#!/usr/bin/env python3
# coupon_scraper.py ― Roblox 쿠폰 수집기 (Sorts API 사용)

"""
1) Sorts API로 “Popular” token 얻기
2) token으로 인기 TOP_N 게임 리스트 불러오기
3) sources_map 전문 사이트에서 쿠폰 긁기
4) 실패 시 Google Fallback
5) strip_expired → clean → 중복 제거 → coupons.json 저장
"""

import re, json, html, datetime, pathlib, urllib.parse, requests
from bs4 import BeautifulSoup

# ── 설정 ────────────────────────────────────────────
UA      = {"User-Agent":"Mozilla/5.0"}
TODAY   = datetime.date.today().isoformat()
TOP_N   = 50   # 상위 몇 개 게임을 수집할지

# ── 1) Sorts API → “Popular” 토큰 얻기 ───────────────
def fetch_sort_token(context="GamesDefaultSorts", target_name="Popular"):
    url = "https://games.roblox.com/v1/games/sorts"
    params = {"model.gameSortsContext": context}
    try:
        resp = requests.get(url, headers=UA, params=params, timeout=10).json()
        for sort in resp.get("data", resp.get("sorts", [])):
            if sort.get("name", "").lower() == target_name.lower():
                token = sort.get("sortToken")
                print(f"[fetch_sort_token] got token for '{target_name}'")
                return token
        print(f"[fetch_sort_token] '{target_name}' token not found")
    except Exception as e:
        print(f"[fetch_sort_token] ERROR: {e}")
    return None

# ── 2) token으로 인기 게임 리스트 가져오기 ──────────────
def fetch_top_games(token, limit=TOP_N):
    if not token:
        print("[fetch_top_games] No token, returning empty list")
        return []
    url = "https://games.roblox.com/v1/games/list"
    params = {
        "sortToken": token,
        "startRow": 0,
        "maxRows": limit
    }
    try:
        data = requests.get(url, headers=UA, params=params, timeout=10).json()
        games = [g["name"] for g in data.get("data", data.get("games", []))]
        print(f"[fetch_top_games] got {len(games)} games")
        return games
    except Exception as e:
        print(f"[fetch_top_games] ERROR: {e}")
        return []

# ── 3) 전문 사이트 sources_map 예시 ───────────────────
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
    # … 여기에 추가하고 싶은 게임/사이트 매핑 계속 덧붙이세요 …
}

# ── 만료 표시(<del>, strike, ‘Expired’) 제거 ───────────
def strip_expired(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup.find_all(["del","strike"]):
        tag.decompose()
    return re.sub(r"(?i)expired","", str(soup))

# ── 코드 정리 & 유효성 검사 ───────────────────────────
def clean(raw):
    s = html.unescape(raw).strip().upper()
    code = re.sub(r"[^\w!]","", s)
    return code if 5<=len(code)<=20 and code[0].isalpha() else ""

# ── Google Fallback ─────────────────────────────────
def google_codes(game):
    q = urllib.parse.quote_plus(f"{game} codes")
    url = f"https://www.google.com/search?q={q}&num=5&hl=en"
    try:
        txt = requests.get(url, headers=UA, timeout=10).text
    except Exception as e:
        print(f"[{game}] Google fetch ERROR: {e}")
        return []
    links = re.findall(r"/url\?q=(https://[^&]+)", txt)
    found_codes = []
    for link in links[:3]:
        u = urllib.parse.unquote(link)
        try:
            ptxt = requests.get(u, headers=UA, timeout=10).text
            ptxt = html.unescape(ptxt)
            codes = re.findall(r"<code>([^<\s]{5,20})</code>", ptxt, re.I)
            print(f"[{game}][Google] {u} → found {len(codes)} codes")
            found_codes += codes
        except:
            continue
    return found_codes

# ── 이전 쿠폰 로드 ───────────────────────────────────
def load_old():
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

# ── 메인 ─────────────────────────────────────────────
def main():
    # 1) 토큰 → 2) 게임 리스트
    token = fetch_sort_token()
    games = fetch_top_games(token)

    old = load_old()
    seen = {c["code"] for c in old}
    result = []

    # 3~5) 각 게임별 수집
    for game in games:
        raw_list = []
        # 전문 사이트
        for url, pat in sources_map.get(game, []):
            try:
                html_txt = strip_expired(requests.get(url, headers=UA, timeout=10).text)
                found = re.findall(pat, html_txt, re.I)
                print(f"[{game}] {url} → found {len(found)} raw codes")
                raw_list += found
            except Exception as e:
                print(f"[{game}] ERROR fetching {url}: {e}")

        # fallback
        if not raw_list:
            print(f"[{game}] no expert source → Google fallback")
            raw_list = google_codes(game)

        # clean & dedupe
        for raw in raw_list:
            code = clean(raw)
            if code and code not in seen:
                result.append({"game":game,"code":code,"verified":TODAY})
                seen.add(code)

    # 정렬·저장
    result.sort(key=lambda x:(x["game"],x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ Finished. {len(result)} codes across {len({r['game'] for r in result})} games")

if __name__=="__main__":
    main()
