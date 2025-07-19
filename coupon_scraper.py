#!/usr/bin/env python3
# coupon_scraper.py ― Roblox TOP100 인기 게임 쿠폰 자동 수집기
"""
1) Roblox Charts API → 인기 TOP N 게임 이름 리스트 획득
2) sources_map 에 매핑된 전문 사이트에서 쿠폰 추출
3) 나머지 게임은 Google 검색 → <code> 태그 파싱(Fallback)
4) HTML 내 del/strike/Expired 제거 → clean()으로 유효 코드만 필터
5) 중복 제거 → coupons.json 저장
"""

import re, json, html, datetime, pathlib, urllib.parse, requests
from bs4 import BeautifulSoup

# ── 설정 ───────────────────────────────────────────────
UA      = {"User-Agent":"Mozilla/5.0"}
TODAY   = datetime.date.today().isoformat()
TOP_N   = 200   # 상위 N 게임 (필요시 50, 200 등으로 변경)

# ── 1) Roblox Charts API 에서 인기 게임 리스트 가져오기 ──
def fetch_top_games(limit=TOP_N):
    url = f"https://games.roblox.com/v1/games/list?sortType=top&startRows=0&maxRows={limit}"
    try:
        return [g["name"] for g in requests.get(url, headers=UA, timeout=15).json().get("games",[])]
    except Exception:
        # API 실패 시 최소한 20개 하드코드
        return ["Blox Fruits","Shindo Life","Bee Swarm Simulator","Anime Champions Simulator",
                "Blue Lock Rivals","King Legacy","Project Slayers","All Star Tower Defense",
                "Blade Ball","Pet Simulator 99","Weapon Fighting Simulator","Anime Fighters Simulator",
                "Adopt Me!","Murder Mystery 2","Tower of Hell","Arsenal","Brookhaven","Adopt Me!",
                "MM2","Arsenal","Tower of Hell"][:limit]

TOP_GAMES = fetch_top_games()

# ── 2) 전문 사이트 sources_map (약 20개 게임) ──
sources_map = {
    "Blox Fruits": [
        ("https://www.pcgamesn.com/blox-fruits/codes",      r"\*\s+([A-Za-z0-9_!]{5,20})\s+-"),
        ("https://gamerant.com/blox-fruits-codes/",         r"<code>([^<\s]{5,20})</code>"),
    ],
    "Shindo Life":[
        ("https://www.pockettactics.com/shindo-life/codes",r"\*\s+([A-Za-z0-9_!]{5,20})\s+-"),
    ],
    "Bee Swarm Simulator":[
        ("https://beebom.com/roblox-bee-swarm-simulator-codes/",r"\*\s+([A-Za-z0-9_!]{5,20})[:\s-]"),
    ],
    # … 위와 비슷한 형식으로 20개 게임 매핑 유지 …
}

# ── 3) 페이지 HTML에서 만료 표시 제거 ─────────────────
def strip_expired(html_txt:str)->str:
    s=BeautifulSoup(html_txt,"html.parser")
    for t in s.find_all(["del","strike"]): t.decompose()
    return re.sub(r"(?i)expired","",str(s))

# ── 4) 코드 정리 & 유효성 검사 ────────────────────────
def clean(raw:str)->str:
    c=re.sub(r"[^\w!]","",html.unescape(raw).strip().upper())
    return c if 5<=len(c)<=20 and c[0].isalpha() else ""

# ── 5) Google Fallback ────────────────────────────────
def google_codes(game:str)->list[str]:
    q=urllib.parse.quote_plus(f"{game} codes")
    try:
        html_txt=requests.get(f"https://www.google.com/search?q={q}&num=5",headers=UA,timeout=10).text
        links=re.findall(r"/url\?q=(https://[^&]+)",html_txt)
    except:
        return []
    codes=[]
    for link in links[:3]:
        try:
            p=requests.get(urllib.parse.unquote(link),headers=UA,timeout=10).text
            p=html.unescape(p)
            codes+=re.findall(r"<code>([^<\s]{5,20})</code>",p)
        except:
            continue
    return codes

# ── 6) 이전 JSON 불러오기 ───────────────────────────────
def load_old()->list[dict]:
    try: return json.load(open("coupons.json",encoding="utf-8"))
    except: return []

# ── 7) 메인 ───────────────────────────────────────────
def main():
    old = load_old()
    seen = {c["code"] for c in old}
    result=[]

    for game in TOP_GAMES:
        raw_list=[]
        # ① 전문 사이트 우선
        for url,pattern in sources_map.get(game,[]):
            try:
                txt=requests.get(url,headers=UA,timeout=15).text
                txt=strip_expired(txt)
                found=re.findall(pattern,txt,flags=re.I)
                print(f"[{game}] {url} → found {len(found)}")
                raw_list+=found
            except Exception as e:
                print(f"[{game}] fetch fail {e}")

        # ② fallback
        if not raw_list:
            print(f"[{game}] no codes found → Google fallback")
            raw_list=google_codes(game)

        # ③ clean & dedupe
        for raw in raw_list:
            c=clean(raw)
            if c and c not in seen:
                result.append({"game":game,"code":c,"verified":TODAY})
                seen.add(c)

    # ④ save
    result.sort(key=lambda x:(x["game"],x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"✅ Saved {len(result)} codes across {len({r['game'] for r in result})} games")

if __name__=="__main__":
    main()
