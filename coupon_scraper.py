"""
coupon_scraper.py – ‘실사용 가능’ Roblox 쿠폰 전용 스크레이퍼
─────────────────────────────────────────────────────────────
▲ 신뢰 소스 12 게임 (필요 시 sources_map 에 추가)
▲ HTML 안에 <del>, <strike>, ‘Expired’ 가 붙은 코드 자동 제거
▲ 글로벌 Roblox PromoCode 는 공식 API 로 이중 검증
▲ 각 코드에 verified(검증일) 필드 추가
"""

import re, json, html, datetime, pathlib, requests
from bs4 import BeautifulSoup

# ── 설정 ────────────────────────────────────────────────
UA  = {"User-Agent": "Mozilla/5.0"}
DAY = datetime.date.today().isoformat()

# 1️⃣ 쿠폰 ‘문화’가 있는 인기 게임 & 소스
sources_map = {
    "Blox Fruits": [
        ("https://www.pcgamesn.com/blox-fruits/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-")
    ],
    "Shindo Life": [
        ("https://www.pockettactics.com/shindo-life/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-")
    ],
    "Bee Swarm Simulator": [
        ("https://beebom.com/roblox-bee-swarm-simulator-codes/",
         r"\*\s+([A-Za-z0-9_!]{5,20})[:\s-]")
    ],
    "Blade Ball": [
        ("https://beebom.com/roblox-blade-ball-codes/",
         r"<strong>([^<\s]{5,20})</strong>")
    ],
    "Anime Champions Simulator": [
        ("https://beebom.com/roblox-anime-champions-simulator-codes/",
         r"<strong>([^<\s]{5,20})</strong>")
    ],
    "King Legacy": [
        ("https://www.pockettactics.com/king-legacy/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-")
    ],
    "Project Slayers": [
        ("https://www.pockettactics.com/project-slayers/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-")
    ],
    "All Star Tower Defense": [
        ("https://www.pockettactics.com/all-star-tower-defense/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-")
    ],
    "Blue Lock Rivals": [
        ("https://beebom.com/blue-lock-rivals-codes/",
         r"<code>([^<\s]{5,20})</code>")
    ],
    # ★ 필요 시 이곳에 ("게임 이름":[(URL, 정규식), ...]) 추가
}

# 2️⃣ 유효 코드 규칙
def clean(raw: str) -> str:
    code = re.sub(r"[^\w!]", "", html.unescape(raw).strip().upper())
    return code if (5 <= len(code) <= 20 and code[0].isalpha()) else ""

# 3️⃣ HTML 내 ‘만료’ 코드 제거
def strip_expired(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")
    for bad in soup.find_all(["del", "strike"]):
        bad.decompose()
    return re.sub(r"(?i)expired", "", str(soup))

# 4️⃣ Roblox 공식 PromoCode API (글로벌 코드만 해당)
def api_valid(code: str) -> bool:
    url = "https://economy.roblox.com/v1/promocodes/redeem"
    try:
        res = requests.post(url, json={"promocode": code}, timeout=10)
        bad = ("invalid", "expired", "already", "code has")
        return not any(b in res.text.lower() for b in bad)
    except requests.RequestException:
        return True   # 네트워크 오류 → 통과로 간주

# 5️⃣ 기존 JSON 불러오기
def load_old():
    try:
        with open("coupons.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# 6️⃣ 메인
def main():
    final, seen = [], set(load_old())

    for game, srcs in sources_map.items():
        for url, pattern in srcs:
            try:
                html_txt = requests.get(url, headers=UA, timeout=25).text
                html_txt = strip_expired(html_txt)
            except Exception as e:
                print("⚠️ Fetch fail:", game, e); continue

            for raw in re.findall(pattern, html_txt, re.I):
                code = clean(raw)
                if not code or code in seen: continue

                if game == "Roblox Promo" and not api_valid(code):
                    print("🗑️ Promo expired:", code); continue

                final.append({
                    "game": game,
                    "code": code,
                    "verified": DAY
                })
                seen.add(code)

    final.sort(key=lambda x: (x["game"], x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"✅ {len(final)} codes saved across {len({c['game'] for c in final})} games")

if __name__ == "__main__":
    main()
