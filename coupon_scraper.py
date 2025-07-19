#!/usr/bin/env python3
# coding: utf-8
"""
자동 쿠폰 스크래퍼
1) sources_map의 모든 URL에서 코드 추출
2) 인‑게임 코드 → 형식 & 중복 필터
3) Roblox 검색 API로 실행 링크 자동 확보
4) 일반 프로모션 코드 → Roblox Billing API(로그인 세션 필요)로 성공 여부 판별
5) coupons.json 저장
"""

import os, re, json, datetime, pathlib, urllib.parse, requests
from bs4 import BeautifulSoup

# ── 기본 상수 ──────────────────────────────────────────
TODAY       = datetime.date.today().isoformat()
UA          = {"User-Agent": "Mozilla/5.0"}
PROMO_API   = "https://billing.roblox.com/v1/promocodes/redeem"
SEARCH_API  = "https://games.roblox.com/v1/games/list?keyword={q}&startRows=0&maxRows=1"

# ── 한글 번역(있으면) ──────────────────────────────────
kr_name = {
    "BLOX FRUITS":          "블록스 프루츠",
    "SHINDO LIFE":          "신도 라이프",
    "BEE SWARM SIMULATOR":  "비 스웜 시뮬레이터",
    "ADOPT ME!":            "어답트 미!",
    "MURDER MYSTERY 2":     "머더 미스터리 2",
    "TOWER OF HELL":        "타워 오브 헬",
    # …필요 시 계속 추가…
}

# ── 링크 캐시(검색 API 호출 최소화) ─────────────────────
link_cache = {
    "BLOX FRUITS": "https://www.roblox.com/games/2753915549/Blox-Fruits",
    "SHINDO LIFE": "https://www.roblox.com/games/4616652839/Shindo-Life-240",
    # …필요 시 계속 추가…
}

# ── 최대한 확장한 전문 사이트 소스맵 ───────────────────
sources_map = {
    "BLOX FRUITS": [
        ("https://www.pcgamesn.com/blox-fruits/codes",       r"[*•]\s*([A-Za-z0-9_!]{4,40})"),
        ("https://gamerant.com/blox-fruits-codes/",          r"<code>([^<\s]{4,40})</code>"),
        ("https://www.techradar.com/how-to/blox-fruits-codes", r"<li>.*?([A-Za-z0-9_!]{4,40})")
    ],
    "SHINDO LIFE": [
        ("https://www.pockettactics.com/shindo-life/codes",  r"[*•]\s*([A-Za-z0-9_!]{4,40})"),
        ("https://beebom.com/roblox-shindo-life-codes/",     r"<code>([^<\s]{4,40})</code>")
    ],
    "BEE SWARM SIMULATOR": [
        ("https://beebom.com/roblox-bee-swarm-simulator-codes/", r"<code>([^<\s]{4,40})</code>"),
        ("https://gamerant.com/bee-swarm-simulator-codes/",      r"<code>([^<\s]{4,40})</code>")
    ],
    "ADOPT ME!": [
        ("https://progameguides.com/roblox/roblox-adopt-me-codes/", r"<strong>([^<\s]{4,40})</strong>")
    ],
    "MURDER MYSTERY 2": [
        ("https://www.pocketgamer.com/murder-mystery-2/codes/", r"<code>([^<\s]{4,40})</code>")
    ],
    "TOWER OF HELL": [
        ("https://bo3.gg/games/articles/tower-of-hell-codes",  r"<code>([^<\s]{4,40})</code>")
    ],
    "ARSENAL": [
        ("https://www.pockettactics.com/arsenal/codes",        r"<code>([^<\s]{4,40})</code>")
    ],
    "PET SIMULATOR X": [
        ("https://gamerant.com/pet-simulator-x-codes/",        r"<code>([^<\s]{4,40})</code>")
    ],
    "MAD CITY": [
        ("https://progameguides.com/roblox/mad-city-codes/",   r"<code>([^<\s]{4,40})</code>")
    ],
    # …여기에 더 많은 {게임: [(url, 패턴)]} 쌍을 자유롭게 추가…
}

# ── 만료표시 <del>/<strike>/expired 제거 ────────────────
def strip_expired(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(["del", "strike"]):
        t.decompose()
    return re.sub(r"(?i)expired", "", str(soup))

# ── 코드 클린 & 검증 ───────────────────────────────────
def clean(raw: str) -> str:
    s = re.sub(r"[^\w!]", "", raw).upper()
    return s if 4 <= len(s) <= 40 else ""

# ── 실행 링크 자동 검색(없으면) ─────────────────────────
def fetch_link(name: str) -> str:
    if name in link_cache:
        return link_cache[name]
    try:
        q   = urllib.parse.quote_plus(name)
        data= requests.get(SEARCH_API.format(q=q), headers=UA, timeout=10).json()
        gid = data.get("games", [{}])[0].get("rootPlaceId")
        if gid:
            url = f"https://www.roblox.com/games/{gid}"
            link_cache[name] = url
            return url
    except Exception:
        pass
    return ""

# ── 프로모션 코드 API 세션 ──────────────────────────────
def promo_session():
    cookie = os.getenv("ROBLOX_SECURITY")
    if not cookie:
        print("ROBLOX_SECURITY not set → promo check skipped")
        return None
    s = requests.Session(); s.headers.update(UA); s.cookies[".ROBLOSECURITY"] = cookie
    token = s.post(PROMO_API, json={"code": ""}).headers.get("x-csrf-token")
    s.headers["x-csrf-token"] = token
    return s

def promo_valid(s: requests.Session, code: str) -> bool:
    try:
        return s.post(PROMO_API, json={"code": code}, timeout=10).json().get("success", False)
    except Exception:
        return False

# ── 메인 로직 ──────────────────────────────────────────
def main():
    output, seen = [], set()

    # A) 인‑게임 코드: 모든 게임 순회
    for eng, srcs in sources_map.items():
        raw = []
        for url, pat in srcs:
            try:
                html = strip_expired(requests.get(url, headers=UA, timeout=15).text)
                raw += re.findall(pat, html, flags=re.I)
            except Exception as e:
                print(f"[{eng}] fetch ERR: {e}")

        valids = [c for c in map(clean, raw) if c and c not in seen]
        if not valids:
            continue
        seen.update(valids)

        kor  = kr_name.get(eng, eng)
        link = fetch_link(eng)
        for code in valids:
            output.append({
                "game":     f"{kor} ({eng})",
                "code":     code,
                "type":     "in-game",
                "url":      link,
                "verified": TODAY
            })

    # B) 일반 프로모 코드(API 검증)
    promo_list = ["SPIDERCOLA", "TWEETROBLOX", "SUMMERSALE2025"]
    sess = promo_session()
    if sess:
        for code in promo_list:
            if code not in seen and promo_valid(sess, code):
                output.append({
                    "game": "로블록스 프로모션",
                    "code": code,
                    "type": "promo",
                    "url":  "https://www.roblox.com/promocodes",
                    "verified": TODAY
                })
                seen.add(code)

    # C) JSON 저장
    output.sort(key=lambda x: (x["game"], x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ Saved {len(output)} unique coupons")

if __name__ == "__main__":
    main()
