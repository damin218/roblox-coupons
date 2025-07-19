#!/usr/bin/env python3
# coupon_scraper.py ― Roblox 쿠폰 수집기 (3단계 토큰+API+HTML 풀 폴백)

"""
1) Sorts API로 ‘Popular’ 토큰 시도
2) 실패 시 sortType=Favorite API 풀 폴백
3) 실패 시 웹페이지 HTML 스크래핑 풀 폴백
4) sources_map 전문 사이트 → strip_expired → 정규식 추출
5) Google fallback
6) clean() → 중복 제거 → coupons.json 저장
"""

import re, json, html, datetime, pathlib, urllib.parse, requests
from bs4 import BeautifulSoup

UA      = {"User-Agent":"Mozilla/5.0"}
TODAY   = datetime.date.today().isoformat()
TOP_N   = 50   # 상위 게임 몇 개

# ── 1) Sorts API → “Popular” 토큰 ────────────────────
def fetch_sort_token(name="Popular"):
    url    = "https://games.roblox.com/v1/games/sorts"
    try:
        res  = requests.get(url, headers=UA, timeout=10).json()
        sorts = res.get("data", res.get("sorts", []))
        for s in sorts:
            if s.get("name","").lower() == name.lower():
                print(f"[fetch_sort_token] got token for '{name}'")
                return s.get("sortToken")
    except Exception as e:
        print(f"[fetch_sort_token] ERROR: {e}")
    print(f"[fetch_sort_token] '{name}' token not found")
    return None

# ── 2) Sorts API 풀 폴백 → sortType 파라미터 ─────────
def fetch_top_games_via_api(token, limit=TOP_N):
    if token:
        url    = "https://games.roblox.com/v1/games/list"
        params = {"sortToken":token, "startRow":0, "maxRows":limit}
        try:
            data  = requests.get(url, headers=UA, params=params, timeout=10).json()
            games = [g["name"] for g in data.get("data", data.get("games", []))]
            if games:
                print(f"[fetch_top_games] got {len(games)} via token")
                return games
        except Exception as e:
            print(f"[fetch_top_games] API with token ERROR: {e}")

    # Favorite 풀 폴백
    print("[fetch_top_games] using sortType=Favorite fallback")
    fav_url = (
        "https://games.roblox.com/v1/games/list"
        f"?sortType=Favorite&sortOrder=Desc&startRow=0&maxRows={limit}"
    )
    try:
        fav = requests.get(fav_url, headers=UA, timeout=10).json()
        games = [g["name"] for g in fav.get("games", [])]
        if games:
            print(f"[fetch_top_games] got {len(games)} via Favorite fallback")
            return games
    except Exception as e:
        print(f"[fetch_top_games] Favorite fallback ERROR: {e}")

    return []

# ── 3) HTML 풀 폴백 → 홈페이지 스크래핑 ───────────────
def fetch_top_games_via_html(limit=TOP_N):
    print("[fetch_top_games] using HTML scraping fallback")
    url = "https://www.roblox.com/games?sortFilter=Popular"
    try:
        txt  = requests.get(url, headers=UA, timeout=10).text
        soup = BeautifulSoup(txt, "html.parser")
        # game-card-link 클래스의 title 속성에서 게임명 추출
        els  = soup.select("a.game-card-link")
        games=[]
        for a in els:
            title = a.get("title") or a.text.strip()
            if title:
                games.append(title)
            if len(games)>=limit: break
        print(f"[fetch_top_games] got {len(games)} via HTML")
        return games
    except Exception as e:
        print(f"[fetch_top_games] HTML fallback ERROR: {e}")
        return []

# ── 전문 사이트 매핑 (원하시는 게임/사이트 추가) ─────────
sources_map = {
    "Blox Fruits": [
        ("https://www.pcgamesn.com/blox-fruits/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-"),
        ("https://gamerant.com/blox-fruits-codes/",
         r"<code>([^<\s]{5,20})</code>")
    ],
    "Shindo Life": [
        ("https://www.pockettactics.com/shindo-life/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-")
    ],
    # … 여기에 더 추가 …
}

# ── HTML 내 만료 표시 제거 ─────────────────────────────
def strip_expired(html_txt):
    soup = BeautifulSoup(html_txt, "html.parser")
    for t in soup.find_all(["del","strike"]):
        t.decompose()
    return re.sub(r"(?i)expired","", str(soup))

# ── 코드 정리 & 유효성 검사 ─────────────────────────────
def clean(raw):
    s    = html.unescape(raw).strip().upper()
    code = re.sub(r"[^\w!]","", s)
    return code if 5<=len(code)<=20 and code[0].isalpha() else ""

# ── Google Fallback ───────────────────────────────────
def google_codes(game):
    q    = urllib.parse.quote_plus(f"{game} codes")
    url  = f"https://www.google.com/search?q={q}&num=5&hl=en"
    try:
        txt   = requests.get(url, headers=UA, timeout=10).text
        links = re.findall(r"/url\?q=(https://[^&]+)", txt)
    except Exception as e:
        print(f"[{game}] Google fetch ERROR: {e}")
        return []
    codes=[]
    for link in links[:3]:
        u = urllib.parse.unquote(link)
        try:
            ptxt = requests.get(u, headers=UA, timeout=10).text
            ptxt = html.unescape(ptxt)
            found= re.findall(r"<code>([^<\s]{5,20})</code>", ptxt, re.I)
            print(f"[{game}][Google] {u} → {len(found)} codes")
            codes+=found
        except:
            continue
    return codes

# ── 이전 coupons.json 로드 ───────────────────────────
def load_old():
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

# ── Main ─────────────────────────────────────────────
def main():
    # 1) 토큰 API → 2) API 풀 폴백 → 3) HTML 풀 폴백
    token = fetch_sort_token()
    games = fetch_top_games_via_api(token) or fetch_top_games_via_html()

    old   = load_old()
    seen  = {c["code"] for c in old}
    out   = []

    for game in games:
        raw=[]
        # 전문 사이트
        for url, pat in sources_map.get(game, []):
            try:
                txt = strip_expired(requests.get(url, headers=UA, timeout=10).text)
                hits= re.findall(pat, txt, re.I)
                print(f"[{game}] {url} → {len(hits)} raw codes")
                raw+=hits
            except Exception as e:
                print(f"[{game}] ERROR fetching {url}: {e}")
        # Google fallback
        if not raw:
            print(f"[{game}] no expert source → Google fallback")
            raw = google_codes(game)
        # clean & dedupe
        for r in raw:
            c = clean(r)
            if c and c not in seen:
                out.append({"game":game,"code":c,"verified":TODAY})
                seen.add(c)

    out.sort(key=lambda x:(x["game"], x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ Finished. {len(out)} codes across {len({r['game'] for r in out})} games")

if __name__=="__main__":
    main()
