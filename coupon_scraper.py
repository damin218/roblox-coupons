#!/usr/bin/env python3
# coding: utf-8
"""
auto_coupon_scraper.py
────────────────────────────────────────────────────────
URL+정규식만 sources_list 에 넣으면
  • 게임 이름 추정          (<title> 또는 URL slug)
  • 인‑게임 코드 수집 + 중복 제거
  • 실행 링크 자동 검색     (Roblox 검색 API)
  • 프로모 코드 Billing API 검증(.ROBLOSECURITY 필요)
  • coupons.json & widget.html 생성
"""

import os, re, json, datetime, pathlib, urllib.parse, requests
from collections import defaultdict
from bs4 import BeautifulSoup

# ─────────────────────────────── 상수
TODAY       = datetime.date.today().isoformat()
UA          = {"User-Agent": "Mozilla/5.0"}
PROMO_API   = "https://billing.roblox.com/v1/promocodes/redeem"
SEARCH_API  = ("https://games.roblox.com/v1/games/list"
               "?keyword={kw}&startRows=0&maxRows=1")

# ─────────────────────────────── URL + 패턴
sources_list = [
    ("https://www.pcgamesn.com/blox-fruits/codes",
     r"[*•]\s*([A-Za-z0-9_!]{4,40})"),
    ("https://www.pockettactics.com/shindo-life/codes",
     r"[*•]\s*([A-Za-z0-9_!]{4,40})"),
    ("https://beebom.com/roblox-bee-swarm-simulator-codes/",
     r"<code>([^<\s]{4,40})</code>"),
    # …필요한 만큼 URL 추가…
]

# 한글 번역(선택) ──────────────────────────
kr_map = {
    "BLOX FRUITS": "블록스 프루츠",
    "SHINDO LIFE": "신도 라이프",
}

link_cache: dict[str, str] = {}

# ─────────────────────────────── 유틸
def strip_expired(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(["del", "strike"]):
        t.decompose()
    return re.sub(r"(?i)expired", "", str(soup))

def clean(raw: str) -> str:
    s = re.sub(r"[^\w!]", "", raw).upper()
    return s if 4 <= len(s) <= 40 else ""

def guess_name(html: str, url: str) -> str:
    title = BeautifulSoup(html, "html.parser").title
    if title and "codes" in title.text.lower():
        return title.text.split("codes")[0].strip().upper()
    slug = urllib.parse.urlparse(url).path.split("/")[1]
    return slug.replace("-", " ").upper()

def fetch_link(name: str) -> str:
    """캐시 → 검색 API → 실패 시 빈 문자열"""
    if name in link_cache:
        return link_cache[name]
    try:
        kw = urllib.parse.quote_plus(name)
        data = requests.get(SEARCH_API.format(kw=kw), headers=UA,
                            timeout=10).json()
        gid = data.get("games", [{}])[0].get("rootPlaceId")
        if gid:
            url = f"https://www.roblox.com/games/{gid}"
            link_cache[name] = url
            return url
    except Exception:
        pass
    return ""

def promo_session():
    cookie = os.getenv("ROBLOX_SECURITY")
    if not cookie:
        print("ROBLOX_SECURITY not set → skip promo check")
        return None
    s = requests.Session()
    s.headers.update(UA)
    s.cookies[".ROBLOSECURITY"] = cookie
    token = s.post(PROMO_API, json={"code": ""}).headers.get("x-csrf-token")
    s.headers["x-csrf-token"] = token
    return s

def promo_valid(s: requests.Session, code: str) -> bool:
    try:
        return s.post(PROMO_API, json={"code": code},
                      timeout=10).json().get("success", False)
    except Exception:
        return False

# ─────────────────────────────── 메인
def main():
    per_game = defaultdict(set)
    rows = []

    # A. 인‑게임 코드 수집
    for url, pat in sources_list:
        try:
            html = requests.get(url, headers=UA, timeout=15).text
            game = guess_name(html, url)
            for raw in re.findall(pat, strip_expired(html), flags=re.I):
                code = clean(raw)
                if code and code not in per_game[game]:
                    per_game[game].add(code)
        except Exception as e:
            print(f"[{url}] ERR {e}")

    for game, codes in per_game.items():
        kor  = kr_map.get(game, game)
        link = fetch_link(game)
        for c in sorted(codes):
            rows.append({"game": f"{kor} ({game})",
                         "code": c,
                         "type": "in‑game",
                         "url":  link,
                         "verified": TODAY})

    # B. 일반 프로모 코드
    session = promo_session()
    promo = ["SPIDERCOLA", "TWEETROBLOX", "SUMMERSALE2025"]
    if session:
        for p in promo:
            if promo_valid(session, p):
                rows.append({"game": "로블록스 프로모션",
                             "code": p,
                             "type": "promo",
                             "url":  "https://www.roblox.com/promocodes",
                             "verified": TODAY})

    # C. 저장
    rows.sort(key=lambda x: (x["game"], x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8")

    build_widget(rows)
    print(f"✅ Saved {len(rows)} unique coupons")

# ─────────────────────────────── 위젯 HTML
def build_widget(data: list):
    rows_html = "\n".join(
        f"<tr><td>{d['game']}</td>"
        f"<td><code>{d['code']}</code></td>"
        f"<td>{'<a target=\"_blank\" href=\"'+d['url']+'\">실행</a>' if d['url'] else '-'}</td></tr>"
        for d in data
    )
    html = f"""<!doctype html><html lang=ko><meta charset=utf-8>
<title>Roblox 쿠폰</title>
<style>
body{{font-family:'Noto Sans KR',sans-serif;font-size:14px}}
table{{width:100%;border-collapse:collapse;margin-top:10px}}
th,td{{border:1px solid #ddd;padding:6px}}
th{{background:#f4f4f4}}
input{{width:100%;padding:7px;margin:0}}
code{{background:#eee;padding:2px 4px;border-radius:4px}}
</style>
<h2>🎁 Roblox 쿠폰 ({TODAY})</h2>
<input placeholder="게임/쿠폰 검색" onkeyup="f(this.value)">
<table id=tbl><thead><tr><th>게임</th><th>쿠폰</th><th>실행</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<script>function f(q){{q=q.toLowerCase();
for(const r of tbl.tBodies[0].rows)
  r.style.display=r.textContent.toLowerCase().includes(q)?'':'none';}}</script></html>"""
    pathlib.Path("widget.html").write_text(html, encoding="utf-8")

# ───────────────────────────────
if __name__ == "__main__":
    main()
