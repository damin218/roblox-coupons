#!/usr/bin/env python3
# coupon_scraper.py ― Roblox 쿠폰 수집 + 로깅 강화판
"""
1) TOP_GAMES 리스트 순환
2) sources_map 우선 시도 → debug print
3) 실패 시 Google Fallback → debug print
4) clean() 후 중복제거 → result 리스트
5) coupons.json 에 저장 + 최종 debug
"""

import re, json, html, datetime, pathlib, urllib.parse, requests
from bs4 import BeautifulSoup

# ── 설정 ────────────────────────────────────────────────
UA = {"User-Agent": "Mozilla/5.0"}
TODAY = datetime.date.today().isoformat()
# 수집할 인기 게임 개수
TOP_N = 50

# ── 1) 인기 게임 리스트 가져오기 ───────────────────────────
def fetch_top_games(n=TOP_N):
    url = f"https://games.roblox.com/v1/games/list?sortType=top&startRows=0&maxRows={n}"
    try:
        data = requests.get(url, headers=UA, timeout=15).json()
        games = [g["name"] for g in data.get("games",[])]
        print(f"[fetch_top_games] got {len(games)} games")
        return games
    except Exception as e:
        print(f"[fetch_top_games] ERROR: {e}")
        # 최소 10개 하드코드로 대체
        return ["Blox Fruits","Shindo Life","Bee Swarm Simulator",
                "Blade Ball","Anime Champions Simulator","Brookhaven",
                "Adopt Me!","Murder Mystery 2","Tower of Hell","Arsenal"]

TOP_GAMES = fetch_top_games()

# ── 2) sources_map (전문 사이트) ───────────────────────────
sources_map = {
    "Blox Fruits":[
        ("https://www.pcgamesn.com/blox-fruits/codes", r"\*\s+([A-Za-z0-9_!]{5,20})\s+-"),
        ("https://gamerant.com/blox-fruits-codes/",       r"<code>([^<\s]{5,20})</code>")
    ],
    "Shindo Life":[
        ("https://www.pockettactics.com/shindo-life/codes", r"\*\s+([A-Za-z0-9_!]{5,20})\s+-")
    ],
    # … 필요하면 여기에 더 추가 …
}

# ── 3) HTML 내 만료 표시 제거 ─────────────────────────────
def strip_expired(text):
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup.find_all(["del","strike"]): tag.decompose()
    return re.sub(r"(?i)expired","", str(soup))

# ── 4) 코드 정리 & 유효성 검사 ─────────────────────────────
def clean(raw):
    s = html.unescape(raw).strip().upper()
    code = re.sub(r"[^\w!]","", s)
    if 5 <= len(code) <= 20 and code[0].isalpha():
        return code
    return ""

# ── 5) Google Fallback ────────────────────────────────────
def google_codes(game):
    query = urllib.parse.quote_plus(f"{game} codes")
    url = f"https://www.google.com/search?q={query}&num=5&hl=en"
    try:
        resp = requests.get(url, headers=UA, timeout=15).text
    except Exception as e:
        print(f"[{game}] Google fetch ERROR: {e}")
        return []
    links = re.findall(r"/url\?q=(https://[^&]+)", resp)
    codes = []
    for link in links[:3]:
        try:
            page = requests.get(link, headers=UA, timeout=15).text
            page = html.unescape(page)
            found = re.findall(r"<code>([^<\s]{5,20})</code>", page, flags=re.I)
            print(f"[{game}][Google] {link} → found {len(found)} codes")
            codes += found
        except Exception as e:
            print(f"[{game}][Google] ERROR on {link}: {e}")
    return codes

# ── 6) 이전 JSON 로드 ─────────────────────────────────────
def load_old():
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

# ── 7) 메인 로직 ─────────────────────────────────────────
def main():
    old = load_old()
    seen = {c["code"] for c in old}
    result = []

    for game in TOP_GAMES:
        raw_codes = []
        # --- 전문 사이트 시도 ---
        for url, pat in sources_map.get(game, []):
            try:
                txt = requests.get(url, headers=UA, timeout=15).text
                txt = strip_expired(txt)
                found = re.findall(pat, txt, flags=re.I)
                print(f"[{game}] {url} → found {len(found)} raw codes")
                raw_codes += found
            except Exception as e:
                print(f"[{game}] ERROR fetching {url}: {e}")

        # --- 전부 실패 시 Google fallback ---
        if not raw_codes:
            print(f"[{game}] no expert source → Google fallback")
            raw_codes = google_codes(game)

        # --- 클린업 & 중복 제거 ---
        for raw in raw_codes:
            code = clean(raw)
            if code and code not in seen:
                seen.add(code)
                result.append({"game":game,"code":code,"verified":TODAY})

    # --- 저장 & 최종 로그 ---
    result.sort(key=lambda x:(x["game"],x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Finished. {len(result)} codes across {len({r['game'] for r in result})} games")

if __name__=="__main__":
    main()
