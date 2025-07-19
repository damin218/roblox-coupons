"""
coupon_scraper.py  –  Roblox 인기 TOP 100 게임용 ‘올인원’ 쿠폰 수집
────────────────────────────────────────────────────────
▸ 순서
  1. Roblox Charts API로 실시간 TOP 100 게임 ID·이름 획득
  2. 미리 정의한 sources_map(약 30종) → 정규식으로 코드 추출
  3. 나머지는 구글 검색('<Game> codes') → <code> 태그 긁어오기
  4. 대문자·공백·중복 제거 + JSON 저장
"""

import re, json, time, datetime, pathlib, html, urllib.parse, requests
from bs4 import BeautifulSoup

TODAY = datetime.date.today()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ─────────────────────────────────────────────────────
# 1. Roblox Charts API → 인기 게임 TOP 100
# ─────────────────────────────────────────────────────
def fetch_top_games(limit=100):
    """Roblox 공식 차트(https://games.roblox.com/v1/games/list?sortType=top)"""
    url = f"https://games.roblox.com/v1/games/list?sortType=top&startRows=0&maxRows={limit}"
    try:
        data = requests.get(url, headers=UA, timeout=20).json()
        return [g["name"] for g in data.get("games", [])]
    except Exception as e:
        print("⚠️ Charts API 실패:", e)
        # Fallback: 2025‑07 월간 사용자수 기준 상위 20 게임 하드코드
        return ["Blox Fruits", "Brookhaven", "Adopt Me!", "Pet Simulator X",
                "DOORS", "Murder Mystery 2", "Tower of Hell", "Shindo Life",
                "King Legacy", "Project Slayers", "Bee Swarm Simulator",
                "Blade Ball", "All Star Tower Defense", "Blue Lock Rivals",
                "Weapon Fighting Simulator", "Anime Fighters Simulator",
                "Anime Champions Simulator", "Pet Simulator 99", "Evade",
                "Arsenal"]

TOP_GAMES = fetch_top_games(100)[:100]

# ─────────────────────────────────────────────────────
# 2. 게임별 코드 페이지(소스) & 정규식 매핑 (수동 + 확실)
# ─────────────────────────────────────────────────────
sources_map = {
    "BLOX FRUITS": [
        ("https://www.pcgamesn.com/blox-fruits/codes", r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
        ("https://gamerant.com/blox-fruits-codes/",    r"<code>([^<\s]{4,40})</code>")
    ],
    "SHINDO LIFE": [
        ("https://www.pockettactics.com/shindo-life/codes", r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
        ("https://beebom.com/roblox-shindo-life-codes/",    r"<code>([^<\s]{4,40})</code>")
    ],
    "BEE SWARM SIMULATOR": [
        ("https://beebom.com/roblox-bee-swarm-simulator-codes/", r"\*\s+([A-Za-z0-9_!]{4,40})[:\s-]")
    ],
    "ANIME CHAMPIONS SIMULATOR": [
        ("https://beebom.com/roblox-anime-champions-simulator-codes/", r"<strong>([^<\s]{4,40})</strong>")
    ],
    "BLUE LOCK RIVALS": [
        ("https://beebom.com/blue-lock-rivals-codes/", r"<code>([^<\s]{4,40})</code>")
    ],
    "KING LEGACY": [
        ("https://www.pockettactics.com/king-legacy/codes",      r"\*\s+([A-Za-z0-9_!]{4,40})\s+-")
    ],
    "PROJECT SLAYERS": [
        ("https://www.pockettactics.com/project-slayers/codes",  r"\*\s+([A-Za-z0-9_!]{4,40})\s+-")
    ],
    "ALL STAR TOWER DEFENSE": [
        ("https://www.pockettactics.com/all-star-tower-defense/codes", r"\*\s+([A-Za-z0-9_!]{4,40})\s+-")
    ],
    "BLADE BALL": [
        ("https://beebom.com/roblox-blade-ball-codes/", r"<strong>([^<\s]{4,40})</strong>")
    ],
    "PET SIMULATOR 99": [
        ("https://beebom.com/roblox-pet-simulator-99-codes/", r"<strong>([^<\s]{4,40})</strong>")
    ],
    "WEAPON FIGHTING SIMULATOR": [
        ("https://www.pockettactics.com/weapon-fighting-simulator/codes", r"\*\s+([A-Za-z0-9_!]{4,40})\s+-")
    ],
    "ANIME FIGHTERS SIMULATOR": [
        ("https://www.pockettactics.com/anime-fighters-simulator/codes",  r"\*\s+([A-Za-z0-9_!]{4,40})\s+-")
    ],
}

# ─────────────────────────────────────────────────────
# 3. 유틸 – 문자열 정리
# ─────────────────────────────────────────────────────
def clean(code: str) -> str:
    code = re.sub(r"[^\w!]", "", code.strip().upper())
    return code if len(code) >= 4 else ""

# ─────────────────────────────────────────────────────
# 4. « 동적 파서 » – 구글 검색 + <code> 태그 긁기
# ─────────────────────────────────────────────────────
def google_codes(game: str):
    q = urllib.parse.quote_plus(f"{game} codes")
    url = f"https://www.google.com/search?q={q}&num=5&hl=en"
    try:
        html = requests.get(url, headers=UA, timeout=15).text
    except Exception:
        return []
    links = re.findall(r"/url\?q=(https://[^&]+)", html)
    codes = []
    for link in links[:3]:   # 상위 3 페이지만 시도
        link = urllib.parse.unquote(link)
        try:
            page = requests.get(link, headers=UA, timeout=15).text
            page = html.unescape(page)
            codes += re.findall(r"<code>([^<\s]{4,40})</code>", page, re.I)
        except Exception:
            continue
    return [clean(c) for c in codes]

# ─────────────────────────────────────────────────────
# 5. 기존 JSON 로드
# ─────────────────────────────────────────────────────
def load_old():
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

# ─────────────────────────────────────────────────────
# 6. 메인
# ─────────────────────────────────────────────────────
def main():
    codes = load_old()
    seen = {c["code"] for c in codes}

    for game in TOP_GAMES:
        gkey = game.upper()
        new_codes = []

        # 1) 매핑된 공식/전문 사이트 우선
        if gkey in sources_map:
            for src_url, pattern in sources_map[gkey]:
                try:
                    html_txt = requests.get(src_url, headers=UA, timeout=30).text
                    new_codes += re.findall(pattern, html_txt, flags=re.I)
                except Exception:
                    continue
        # 2) 매핑이 없으면 Google 동적 검색
        else:
            new_codes += google_codes(game)

        for code in map(clean, new_codes):
            if code and code not in seen:
                codes.append({"game": game, "code": code, "expires": None})
                seen.add(code)

    # 정렬·저장
    codes.sort(key=lambda x: (x["game"].upper(), x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(codes, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"✅ Saved {len(codes)} coupons for {len({c['game'] for c in codes})} games")

# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
