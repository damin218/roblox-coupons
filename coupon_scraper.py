#!/usr/bin/env python3
# coding: utf-8
"""
auto_coupon_scraper.py
────────────────────────────────────────────────────────
• sources_list:  URL + 정규식만 넣으면 끝 (게임 이름 자동 추출)
• HTML → 만료표시(<del>,<strike>,“expired”) 제거 → 코드 추출
• clean(): 4–40자 영문/숫자/! 로 필터 + per‑game 중복 제거
• 실행 링크: 캐시 없으면 Roblox 검색 API(rootPlaceId)로 보충
• 프로모 코드: Billing API 로 실제 성공 여부 확인(쿠키 필요)
• coupons.json + widget.html(Tistory) 자동 생성
"""

import os, re, json, datetime, pathlib, urllib.parse, requests
from collections import defaultdict
from bs4 import BeautifulSoup

TODAY = datetime.date.today().isoformat()
UA    = {"User-Agent":"Mozilla/5.0"}

PROMO_API  = "https://billing.roblox.com/v1/promocodes/redeem"
SEARCH_API = (
    "https://games.roblox.com/v1/games/list"
    "?keyword={kw}&startRows=0&maxRows=1"
)

# ── URL + 패턴만 넣으면 자동 반영 ──────────────────────
sources_list = [
    # PCGamesN – Blox Fruits :contentReference[oaicite:0]{index=0}
    ("https://www.pcgamesn.com/blox-fruits/codes",
     r"[*•]\s*([A-Za-z0-9_!]{4,40})"),
    # Pocket Tactics – Shindo Life :contentReference[oaicite:1]{index=1}
    ("https://www.pockettactics.com/shindo-life/codes",
     r"[*•]\s*([A-Za-z0-9_!]{4,40})"),
    # Beebom – Bee Swarm Simulator :contentReference[oaicite:2]{index=2}
    ("https://beebom.com/roblox-bee-swarm-simulator-codes/",
     r"<code>([^<\s]{4,40})</code>"),
    # ProGameGuides – Adopt Me! :contentReference[oaicite:3]{index=3}
    ("https://progameguides.com/roblox/roblox-adopt-me-codes/",
     r"<strong>([^<\s]{4,40})</strong>"),
    # Pocket Gamer – Murder Mystery 2 :contentReference[oaicite:4]{index=4}
    ("https://www.pocketgamer.com/murder-mystery-2/codes/",
     r"<code>([^<\s]{4,40})</code>"),
    # Bo3.gg – Tower of Hell :contentReference[oaicite:5]{index=5}
    ("https://bo3.gg/games/articles/tower-of-hell-codes",
     r"<code>([^<\s]{4,40})</code>"),
    # Pocket Tactics – Arsenal :contentReference[oaicite:6]{index=6}
    ("https://www.pockettactics.com/arsenal/codes",
     r"<code>([^<\s]{4,40})</code>"),
    # Game Rant – Pet Simulator 99 (예시, 없을 수도 있음) :contentReference[oaicite:7]{index=7}
    ("https://gamerant.com/roblox-pet-simulator-99-codes-prestons-shop-super-secret/",
     r"<code>([^<\s]{4,40})</code>")
    # …URL만 계속 추가하세요…
]

# (선택) 한글 번역 – 없으면 영어 그대로
kr_map = {"BLOX FRUITS":"블록스 프루츠","SHINDO LIFE":"신도 라이프"}

# 실행 링크 캐시
link_cache: dict[str,str] = {}

# ── 유틸 ───────────────────────────────────────────────
def strip_expired(html:str)->str:
    soup=BeautifulSoup(html,"html.parser")
    [t.decompose() for t in soup.find_all(["del","strike"])]
    return re.sub(r"(?i)expired","",str(soup))

def clean(raw:str)->str:
    s=re.sub(r"[^\w!]","",raw).upper()
    return s if 4<=len(s)<=40 else ""

def guess_game_name(html:str,url:str)->str:
    # 1) <title> Foo codes
    title = BeautifulSoup(html,"html.parser").title
    if title and "codes" in title.text.lower():
        return title.text.split("codes")[0].strip().upper()
    # 2) URL slug
    slug = urllib.parse.urlparse(url).path.split("/")[1]
    return slug.replace("-"," ").upper()

def fetch_link(name:str)->str:
    if name in link_cache: return link_cache[name]
    try:
        q=urllib.parse.quote_plus(name)
        data=requests.get(SEARCH_API.format(kw=q:=q),headers=UA,timeout=10).json()
        gid=data.get("games",[{}])[0].get("rootPlaceId")
        if gid:
            url=f"https://www.roblox.com/games/{gid}"
            link_cache[name]=url; return url
    except: pass
    return ""

def promo_session():
    cookie=os.getenv("ROBLOX_SECURITY")
    if not cookie: return None
    s=requests.Session(); s.headers.update(UA); s.cookies[".ROBLOSECURITY"]=cookie
    token=s.post(PROMO_API,json={"code":""}).headers.get("x-csrf-token")
    s.headers["x-csrf-token"]=token; return s

def promo_valid(s,code:str)->bool:
    try: return s.post(PROMO_API,json={"code":code},timeout=10).json().get("success",False)
    except: return False

# ── 메인 ───────────────────────────────────────────────
def main():
    dedup=defaultdict(set); out=[]
    # A) 인‑게임 코드
    for url,pat in sources_list:
        try:
            html=requests.get(url,headers=UA,timeout=15).text
            game=guess_game_name(html,url)
            for raw in re.findall(pat,strip_expired(html),flags=re.I):
                code=clean(raw)
                if code and code not in dedup[game]:
                    dedup[game].add(code)
        except Exception as e:
            print(f"[{url}] ERR {e}")

    for game,codes in dedup.items():
        kor=kr_map.get(game,game)
        link=fetch_link(game)
        for c in sorted(codes):
            out.append({"game":f"{kor} ({game})","code":c,
                        "type":"in‑game","url":link,"verified":TODAY})

    # B) 프로모 코드
    sess=promo_session(); promo=["SPIDERCOLA","TWEETROBLOX","SUMMERSALE2025"]
    if sess:
        for p in promo:
            if promo_valid(sess,p):
                out.append({"game":"로블록스 프로모션","code":p,
                            "type":"promo","url":"https://www.roblox.com/promocodes",
                            "verified":TODAY})

    out.sort(key=lambda x:(x["game"],x["code"]))
    pathlib.Path("coupons.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    build_widget(out)
    print("✅ Saved",len(out),"unique coupons")

# 위젯 HTML (T스토리용)
def build_widget(data):
    rows="\n".join(f"<tr><td>{d['game']}</td><td><code>{d['code']}</code></td>"
                   f"<td><a href='{d['url']}' target='_blank'>실행</a></td></tr>"
                   for d in data)
    html=f"""<!doctype html><html><meta charset=utf-8><title>Roblox 쿠폰</title>
<style>body{{font-family:'Noto Sans KR',sans-serif}}table{{width:100%;border-collapse:collapse}}
th,td{{border:1px solid #ccc;padding:6px}}th{{background:#f4f4f4}}</style>
<h2>🎁 Roblox 무료 쿠폰({TODAY})</h2>
<input onkeyup="f(this.value)" placeholder="게임/코드 검색…" style="width:100%;padding:6px">
<table id=t><thead><tr><th>게임</th><th>쿠폰</th><th>실행</th></tr></thead><tbody>{rows}</tbody></table>
<script>function f(q){{q=q.toLowerCase();for(const r of t.tBodies[0].rows)r.style.display=r.textContent.toLowerCase().includes(q)?'':'none';}}</script></html>"""
    pathlib.Path("widget.html").write_text(html,encoding="utf-8")

if __name__=="__main__": main()
