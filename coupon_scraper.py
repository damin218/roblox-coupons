#!/usr/bin/env python3
# coupon_scraper.py ― Roblox 인기 게임 쿠폰 수집 + 디버그 & Fallback
"""
1. sources_map 에 정의된 신뢰 사이트에서 쿠폰 수집
2. 수집 결과가 없으면 Google 동적 검색(<code> 태그)으로 보충
3. HTML 내 <del>, <strike>, 'Expired' 제거
4. 코드 클린업(clean): 길이·문자 검증
5. 중복 제거(seen), debug print
6. 결과를 coupons.json 에 저장
"""

import re
import json
import html
import datetime
import pathlib
import urllib.parse
import requests
from bs4 import BeautifulSoup

# ── 설정 ────────────────────────────────────────────────
UA = {"User-Agent": "Mozilla/5.0"}
TODAY = datetime.date.today().isoformat()

# ── 1. 신뢰 사이트 매핑: 게임 이름 → [(URL, 패턴), …]
sources_map = {
    "Blox Fruits": [
        ("https://www.pcgamesn.com/blox-fruits/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-"),
        ("https://gamerant.com/blox-fruits-codes/",
         r"<code>([^<\s]{5,20})</code>"),
        ("https://twinfinite.net/2025/07/blox-fruits-roblox-codes/",
         r"<li>\s*<strong>([^<\s]{5,20})</strong>")
    ],
    "Shindo Life": [
        ("https://www.pockettactics.com/shindo-life/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-"),
        ("https://beebom.com/roblox-shindo-life-codes/",
         r"<code>([^<\s]{5,20})</code>"),
        ("https://www.gamespot.com/articles/shindo-life-codes/",
         r"<code>([^<\s]{5,20})</code>")
    ],
    "Bee Swarm Simulator": [
        ("https://beebom.com/roblox-bee-swarm-simulator-codes/",
         r"\*\s+([A-Za-z0-9_!]{5,20})[:\s-]"),
    ],
    "Blade Ball": [
        ("https://beebom.com/roblox-blade-ball-codes/",
         r"<strong>([^<\s]{5,20})</strong>")
    ],
    "Anime Champions Simulator": [
        ("https://beebom.com/roblox-anime-champions-simulator-codes/",
         r"<strong>([^<\s]{5,20})</strong>"),
        ("https://www.destructoid.com/anime-champions-simulator-codes/",
         r"<strong>([^<\s]{5,20})</strong>")
    ],
    "King Legacy": [
        ("https://www.pockettactics.com/king-legacy/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-")
    ],
    "Project Slayers": [
        ("https://www.pockettactics.com/project-slayers/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-"),
        ("https://gamerant.com/project-slayers-roblox-codes/",
         r"<code>([^<\s]{5,20})</code>")
    ],
    "All Star Tower Defense": [
        ("https://www.pockettactics.com/all-star-tower-defense/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-")
    ],
    "Blue Lock Rivals": [
        ("https://beebom.com/blue-lock-rivals-codes/",
         r"<code>([^<\s]{5,20})</code>")
    ],
    "Pet Simulator 99": [
        ("https://beebom.com/roblox-pet-simulator-99-codes/",
         r"<strong>([^<\s]{5,20})</strong>")
    ],
    "Weapon Fighting Simulator": [
        ("https://www.pockettactics.com/weapon-fighting-simulator/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-")
    ],
    "Anime Fighters Simulator": [
        ("https://www.pockettactics.com/anime-fighters-simulator/codes",
         r"\*\s+([A-Za-z0-9_!]{5,20})\s+-")
    ],
    # 더 추가하고 싶으면 여기 ↓
}

# ── 2. HTML 내 만료 표시 제거 (del, strike, 'Expired') ──
def strip_expired(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup.find_all(["del", "strike"]):
        tag.decompose()
    txt = str(soup)
    return re.sub(r"(?i)expired", "", txt)

# ── 3. 문자열 정리 & 유효성 검사 ────────────────────────
def clean(raw: str) -> str:
    s = html.unescape(raw).strip().upper()
    code = re.sub(r"[^\w!]", "", s)
    # 길이 5~20, 첫글자 영문자
    if 5 <= len(code) <= 20 and code[0].isalpha():
        return code
    return ""

# ── 4. Google Fallback: 게임명 + "codes" 검색 → <code> 태그 파싱 ──
def google_codes(game: str) -> list[str]:
    query = urllib.parse.quote_plus(f"{game} codes")
    url = f"https://www.google.com/search?q={query}&num=5&hl=en"
    try:
        resp = requests.get(url, headers=UA, timeout=15)
        links = re.findall(r"/url\?q=(https://[^&]+)", resp.text)
    except Exception:
        return []
    codes = []
    for link in links[:3]:
        link = urllib.parse.unquote(link)
        try:
            p = requests.get(link, headers=UA, timeout=15).text
            p = html.unescape(p)
            codes += re.findall(r"<code>([^<\s]{5,20})</code>", p, flags=re.I)
        except Exception:
            continue
    return codes

# ── 5. 이전 JSON 로드 ───────────────────────────────────
def load_old() -> list[dict]:
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

# ── 6. 메인 ─────────────────────────────────────────────
def main():
    old = load_old()
    seen = {c["code"] for c in old}
    result = []

    for game, sources in sources_map.items():
        collected = []
        for url, pattern in sources:
            try:
                txt = requests.get(url, headers=UA, timeout=20).text
                txt = strip_expired(txt)
            except Exception as e:
                print(f"[{game}] ❌ fetch fail: {e}")
                continue

            found = re.findall(pattern, txt, flags=re.I)
            print(f"[{game}] {url} → found {len(found)} raw codes")
            collected += found

        # sources_map에 전부 실패했으면 Google Fallback
        if not collected:
            print(f"[{game}] ⚠️ no codes found, trying Google fallback")
            collected = google_codes(game)

        for raw in collected:
            code = clean(raw)
            if not code or code in seen:
                continue
            result.append({"game": game, "code": code, "verified": TODAY})
            seen.add(code)

    # 정렬·저장
    result.sort(key=lambda x: (x["game"], x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Total: {len(result)} codes across {len({r['game'] for r in result})} games")

if __name__ == "__main__":
    main()
