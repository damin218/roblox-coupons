#!/usr/bin/env python3
# coupon_scraper.py ― Roblox 인기 게임 쿠폰 수집기 (토큰+Fallback 복합 방식)

"""
1) Sorts API로 ‘Popular’ 토큰 시도
2) 실패하면 sortType=Favorite Fallback
3) sources_map 전문 사이트 → strip_expired → 정규식 추출
4) Google fallback
5) clean() → 중복 제거 → coupons.json 저장
"""

import re, json, html, datetime, pathlib, urllib.parse, requests
from bs4 import BeautifulSoup

# ── 설정 ─────────────────────────────────────────────
UA      = {"User-Agent":"Mozilla/5.0"}
TODAY   = datetime.date.today().isoformat()
TOP_N   = 50     # 상위 몇 개 게임을 수집할지

# ── 1) Sorts API → “Popular” 토큰 얻기 ─────────────
def fetch_sort_token(context="GamesDefaultSorts", name="Popular"):
    url = "https://games.roblox.com/v1/games/sorts"
    params = {"model.gameSortsContext": context}
    try:
        res = requests.get(url, headers=UA, params=params, timeout=10).json()
        sorts = res.get("data", res.get("sorts", []))
        for s in sorts:
            if s.get("name","").lower() == name.lower():
                print(f"[fetch_sort_token] got token for '{name}'")
                return s.get("sortToken")
        print(f"[fetch_sort_token] '{name}' token not found")
    except Exception as e:
        print(f"[fetch_sort_token] ERROR: {e}")
    return None

# ── 2) token 으로 인기 TOP_N 게임 불러오기 ──────────
def fetch_top_games(token, limit=TOP_N):
    if token:
        url  = "https://games.roblox.com/v1/games/list"
        params = {"sortToken":token,"startRow":0,"maxRows":limit}
        try:
            data = requests.get(url, headers=UA, params=params, timeout=10).json()
            games = [g["name"] for g in data.get("data",data.get("games",[]))]
            print(f"[fetch_top_games] got {len(games)} games via token")
            return games
        except Exception as e:
            print(f"[fetch_top_games] ERROR with token: {e}")

    # ── Fallback: sortType=Favorite ────────────────────
    print("[fetch_top_games] no token → using sortType=Favorite fallback")
    fb_url = (
        f"https://games.roblox.com/v1/games/list"
        f"?sortType=Favorite&sortOrder=Desc&startRow=0&maxRows={limit}"
    )
    try:
        fb = requests.get(fb_url, headers=UA, timeout=10).json()
        games = [g["name"] for g in fb.get("games",[])]
        print(f"[fetch_top_games][fallback] got {len(games)} games")
        return games
    except Exception as e:
        print(f"[fetch_top_games][fallback] ERROR: {e}")
        return []

# ── 3) 사이트별 전문 쿠폰 매핑 (필요시 추가) ───────
sources_map = {
    "Blox Fruits": [
        ("https://www.pcgamesn.com/blox-fruits/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-"),
        ("https://gamerant.com/blox-fruits-codes/",
         r"<code>([^<\s]{5,20})</code>")
    ],
    "Shindo Life": [
        ("https://www.pockettactics.com/shindo-life/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-"),
    ],
    # … 여기에 다른 인기 게임/전문 코드 페이지 매핑을 계속 추가하세요 …
}

# ── HTML 내 <del>, <strike>, “Expired” 제거 ───────────
def strip_expired(html_txt):
    soup = BeautifulSoup(html_txt, "html.parser")
    for t in soup.find_all(["del","strike"]):
        t.decompose()
    return re.sub(r"(?i)expired","", str(soup))

# ── 코드 클린업 & 유효성 검사 ─────────────────────────
def clean(raw):
    s = html.unescape(raw).strip().upper()
    code = re.sub(r"[^\w!]","", s)
    return code if 5 <= len(code) <= 20 and code[0].isalpha() else ""

# ── Google Fallback (상위 3개 링크만) ───────────────
def google_codes(game):
    q   = urllib.parse.quote_plus(f"{game} codes")
    url = f"https://www.google.com/search?q={q}&num=5&hl=en"
    try:
        txt   = requests.get(url, headers=UA, timeout=10).text
        links = re.findall(r"/url\?q=(https://[^&]+)", txt)
    except Exception as e:
        print(f"[{game}] Google fetch ERROR: {e}")
        return []
    found = []
    for link in links[:3]:
        u = urllib.parse.unquote(link)
        try:
            ptxt = requests.get(u, headers=UA, timeout=10).text
            ptxt = html.unescape(ptxt)
            codes = re.findall(r"<code>([^<\s]{5,20})</code>", ptxt, re.I)
            print(f"[{game}][Google] {u} → found {len(codes)} codes")
            found += codes
        except:
            continue
    return found

# ── 기존 coupons.json 로드 ───────────────────────────
def load_old():
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

# ── Main ─────────────────────────────────────────────
def main():
    token = fetch_sort_token()
    games = fetch_top_games(token)

    old   = load_old()
    seen  = {c["code"] for c in old}
    out   = []

    for game in games:
        raws = []
        for url, pat in sources_map.get(game, []):
            try:
                html_txt = strip_expired(requests.get(url, headers=UA, timeout=10).text)
                hits     = re.findall(pat, html_txt, re.I)
                print(f"[{game}] {url} → found {len(hits)} raw codes")
                raws += hits
            except Exception as e:
                print(f"[{game}] ERROR fetching {url}: {e}")

        if not raws:
            print(f"[{game}] no expert source → Google fallback")
            raws = google_codes(game)

        for r in raws:
            c = clean(r)
            if c and c not in seen:
                out.append({"game":game,"code":c,"verified":TODAY})
                seen.add(c)

    out.sort(key=lambda x:(x["game"],x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ Finished. {len(out)} codes across {len({o['game'] for o in out})} games")

if __name__=="__main__":
    main()
