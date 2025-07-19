#!/usr/bin/env python3
# coupon_scraper.py ― Roblox TOPN 인기 게임 쿠폰 자동 수집기 (API fix 적용)
"""
1) Roblox Charts API → 인기 TOP N 게임 리스트 획득 (sortType=Popular)
2) sources_map 에 매핑된 전문 사이트에서 쿠폰 추출
3) 실패 게임은 Google Fallback
4) HTML 내 del/strike/Expired 제거 → clean()으로 유효 코드 필터링
5) 중복 제거(seen) → coupons.json 저장
"""

import re, json, html, datetime, pathlib, urllib.parse, requests
from bs4 import BeautifulSoup

# ── 설정 ────────────────────────────────────────────────
UA      = {"User-Agent":"Mozilla/5.0"}
TODAY   = datetime.date.today().isoformat()
TOP_N   = 50   # 상위 N개 게임

# ── 1) Roblox Charts API → 인기 게임 리스트 가져오기 ──
def fetch_top_games(limit=TOP_N):
    url = (
        "https://games.roblox.com/v1/games/list"
        f"?sortType=Popular&sortOrder=Desc&startRow=0&maxRows={limit}"
    )
    try:
        data = requests.get(url, headers=UA, timeout=15).json()
        games = [g["name"] for g in data.get("games",[])]
        print(f"[fetch_top_games] got {len(games)} games")
        return games
    except Exception as e:
        print(f"[fetch_top_games] ERROR: {e}")
        # 최후 보류: 하드코드 10개
        return [
          "Blox Fruits","Shindo Life","Bee Swarm Simulator","Anime Champions Simulator",
          "Blue Lock Rivals","King Legacy","Project Slayers","All Star Tower Defense",
          "Blade Ball","Pet Simulator 99"
        ][:limit]

TOP_GAMES = fetch_top_games()

# ── 2) 전문 사이트 sources_map (예시 일부) ───────────────
sources_map = {
    "Blox Fruits":[
        ("https://www.pcgamesn.com/blox-fruits/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-"),
        ("https://gamerant.com/blox-fruits-codes/",
         r"<code>([^<\s]{5,20})</code>")
    ],
    "Shindo Life":[
        ("https://www.pockettactics.com/shindo-life/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-")
    ],
    # … 필요한 게임 추가 …
}

# ── HTML 만료 표시 제거 ─────────────────────────────────
def strip_expired(text):
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup.find_all(["del","strike"]):
        tag.decompose()
    return re.sub(r"(?i)expired","", str(soup))

# ── 코드 정리 & 유효성 검사 ───────────────────────────────
def clean(raw):
    s = html.unescape(raw).strip().upper()
    code = re.sub(r"[^\w!]","", s)
    return code if 5<=len(code)<=20 and code[0].isalpha() else ""

# ── Google Fallback ─────────────────────────────────────
def google_codes(game):
    q = urllib.parse.quote_plus(f"{game} codes")
    url = f"https://www.google.com/search?q={q}&num=5&hl=en"
    try:
        html_txt = requests.get(url, headers=UA, timeout=15).text
    except Exception as e:
        print(f"[{game}] Google fetch ERROR: {e}")
        return []
    links = re.findall(r"/url\?q=(https://[^&]+)", html_txt)
    codes = []
    for link in links[:3]:
        try:
            p = requests.get(urllib.parse.unquote(link), headers=UA, timeout=15).text
            p = html.unescape(p)
            found = re.findall(r"<code>([^<\s]{5,20})</code>", p, flags=re.I)
            print(f"[{game}][Google] {link} → found {len(found)} codes")
            codes += found
        except Exception as e:
            print(f"[{game}][Google] ERROR on {link}: {e}")
    return codes

# ── 이전 JSON 로드 ───────────────────────────────────────
def load_old():
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

# ── 메인 ─────────────────────────────────────────────────
def main():
    old = load_old()
    seen = {c["code"] for c in old}
    result = []

    for game in TOP_GAMES:
        raw_list = []
        # 1) 전문 사이트
        for url, pat in sources_map.get(game, []):
            try:
                txt = requests.get(url, headers=UA, timeout=15).text
                txt = strip_expired(txt)
                found = re.findall(pat, txt, flags=re.I)
                print(f"[{game}] {url} → found {len(found)} raw codes")
                raw_list += found
            except Exception as e:
                print(f"[{game}] ERROR fetching {url}: {e}")

        # 2) fallback
        if not raw_list:
            print(f"[{game}] no expert source → Google fallback")
            raw_list = google_codes(game)

        # 3) clean & dedupe
        for raw in raw_list:
            code = clean(raw)
            if code and code not in seen:
                result.append({"game":game,"code":code,"verified":TODAY})
                seen.add(code)

    # 정렬·저장
    result.sort(key=lambda x:(x["game"], x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Finished. {len(result)} codes across {len({r['game'] for r in result})} games")

if __name__ == "__main__":
    main()
