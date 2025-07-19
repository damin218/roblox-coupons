#!/usr/bin/env python3
# coding: utf-8

import os
import re
import json
import datetime
import pathlib
import requests
from bs4 import BeautifulSoup

# ── 설정 ─────────────────────────────────────────────
TODAY       = datetime.date.today().isoformat()
REDEEM_URL  = "https://billing.roblox.com/v1/promocodes/redeem"
HEADERS     = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ── 1) 문자열 정리 함수 ───────────────────────────────
def clean(raw: str) -> str:
    code = re.sub(r"[^\w!]", "", raw.strip().upper())
    return code if len(code) >= 4 else ""

# ── 2) Roblox 일반 프로모션 코드용 세션 생성 ──────────
def create_redeem_session() -> requests.Session:
    cookie = os.getenv("ROBLOX_SECURITY")
    if not cookie:
        raise RuntimeError("Environment variable ROBLOX_SECURITY is not set.")
    sess = requests.Session()
    sess.headers.update(HEADERS)
    sess.cookies[".ROBLOSECURITY"] = cookie

    # 첫 호출로 CSRF 토큰 획득 (의도적 403)
    init = sess.post(REDEEM_URL, json={"code": ""})
    token = init.headers.get("x-csrf-token")
    if not token:
        raise RuntimeError("Failed to obtain X-CSRF-TOKEN. Check your .ROBLOSECURITY value.")
    sess.headers.update({"x-csrf-token": token})
    return sess

def validate_promo_code(sess: requests.Session, code: str) -> bool:
    """
    실제로 redeem API를 호출해봅니다.
    성공(success=true)이면 True, 아니면 False를 반환.
    *주의* 이 호출은 실제로 계정에 리워드를 지급합니다.
    """
    try:
        resp = sess.post(REDEEM_URL, json={"code": code}, timeout=10)
        data = resp.json()
        return data.get("success", False)
    except Exception:
        return False

# ── 3) 인게임 쿠폰 스크래핑용 소스맵 ───────────────────
sources_map = {
    "BLOX FRUITS": [
        ("https://www.pcgamesn.com/blox-fruits/codes",
         r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
        ("https://gamerant.com/blox-fruits-codes/",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "SHINDO LIFE": [
        ("https://www.pockettactics.com/shindo-life/codes",
         r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
        ("https://beebom.com/roblox-shindo-life-codes/",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "BEE SWARM SIMULATOR": [
        ("https://beebom.com/roblox-bee-swarm-simulator-codes/",
         r"\*\s+([A-Za-z0-9_!]{4,40})[:\s-]")
    ],
    # 필요하면 여기에 추가 게임·URL·정규식 계속 덧붙이세요
}

# ── 4) HTML 내 만료 표시(<del>, <strike>, “Expired”) 제거 ──
def strip_expired(html_txt: str) -> str:
    soup = BeautifulSoup(html_txt, "html.parser")
    for tag in soup.find_all(["del", "strike"]):
        tag.decompose()
    return re.sub(r"(?i)expired", "", str(soup))

# ── 5) 인게임 코드 스크래핑 ─────────────────────────────
def scrape_game_codes() -> dict[str, list[str]]:
    all_codes = {}
    for game, sources in sources_map.items():
        raw = []
        for url, pat in sources:
            try:
                html_txt = strip_expired(requests.get(url, headers=HEADERS, timeout=15).text)
                found = re.findall(pat, html_txt, flags=re.I)
                print(f"[{game}] {url} → raw candidates: {len(found)}")
                raw += found
            except Exception as e:
                print(f"[{game}] ERROR fetching {url}: {e}")
        # clean & dedupe
        valid = sorted({clean(r) for r in raw if clean(r)})
        if valid:
            print(f"[{game}] → valid codes: {len(valid)}")
            all_codes[game] = valid
        else:
            print(f"[{game}] → no valid codes found")
    return all_codes

# ── 6) 메인 로직 ───────────────────────────────────────
def main():
    # A) 인게임 코드 먼저 스크래핑
    game_codes = scrape_game_codes()

    # B) 일반 프로모션 코드 검증
    session     = create_redeem_session()
    promo_list  = ["SPIDERCOLA", "TWEETROBLOX", "SUMMERSALE2025"]
    promo_valid = []
    for code in promo_list:
        ok = validate_promo_code(session, code)
        print(f"[Promo] {code} → {'VALID' if ok else 'INVALID'}")
        if ok:
            promo_valid.append(code)

    # C) 결과 합치기 & 저장
    output = []
    for game, codes in game_codes.items():
        for c in codes:
            output.append({
                "game":     game,
                "code":     c,
                "type":     "in-game",
                "expires":  None,
                "verified": TODAY
            })
    for c in promo_valid:
        output.append({
            "game":     "General Promo",
            "code":     c,
            "type":     "promo",
            "expires":  TODAY,
            "verified": TODAY
        })

    # 정렬·파일 쓰기
    output.sort(key=lambda x: (x["game"], x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ Saved {len(output)} total coupons "
          f"({len(game_codes)} games + {len(promo_valid)} promos)")

if __name__ == "__main__":
    main()
