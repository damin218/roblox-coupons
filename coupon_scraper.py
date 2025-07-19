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
TODAY      = datetime.date.today().isoformat()
REDEEM_URL = "https://billing.roblox.com/v1/promocodes/redeem"
HEADERS    = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ── 1) 영어→한글 게임명 매핑 ───────────────────────────
game_name_map = {
    "BLOX FRUITS":         "블록스 프루츠",
    "SHINDO LIFE":         "신도 라이프",
    "BEE SWARM SIMULATOR": "비 스웜 시뮬레이터",
    "ADOPT ME!":           "어답트 미!",
    "MURDER MYSTERY 2":    "머더 미스터리 2",
    "TOWER OF HELL":       "타워 오브 헬",
    "ARSENAL":             "아스널",
    "PET SIMULATOR X":     "펫 시뮬레이터 X",
    "MAD CITY":            "매드 시티",
    "DRESS TO IMPRESS":    "드레스 투 임프레스",
    "BROOKHAVEN":          "브룩헤이븐",
    "JAILBREAK":           "제일브레이크",
    "CAPYBARA EVOLUTION":  "카피바라 이볼루션",
    "DUCK ARMY":           "덕 아미",
    "MONKEY TYCOON":       "몽키 타이쿤",
    # …원하는 만큼 추가…
}

# ── 2) 전문 사이트 쿠폰 소스맵 ─────────────────────────
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
        ("https://gamerant.com/shindo-life-codes/",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "BEE SWARM SIMULATOR": [
        ("https://beebom.com/roblox-bee-swarm-simulator-codes/",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "ADOPT ME!": [
        ("https://progameguides.com/roblox/roblox-adopt-me-codes/",
         r"<li>\s*([A-Za-z0-9_!]{4,40})—")
    ],
    "MURDER MYSTERY 2": [
        ("https://www.pocketgamer.com/murder-mystery-2/codes/",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "TOWER OF HELL": [
        ("https://bo3.gg/games/articles/tower-of-hell-codes",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "ARSENAL": [
        ("https://www.pockettactics.com/arsenal/codes",
         r"<code>([^<\s]{4,40})</code>"),
        ("https://robloxarsenal.fandom.com/wiki/Codes",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "PET SIMULATOR X": [
        ("https://www.pockettactics.com/pet-simulator-x/codes",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "MAD CITY": [
        ("https://www.pocketgamer.com/roblox/mad-city-codes/",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "DRESS TO IMPRESS": [
        ("https://progameguides.com/roblox/dress-to-impress-codes/",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "BROOKHAVEN": [
        ("https://progameguides.com/roblox/brookhaven-codes/",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "JAILBREAK": [
        ("https://progameguides.com/roblox/jailbreak-codes/",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "CAPYBARA EVOLUTION": [
        ("https://beebom.com/capybara-evolution-codes/",
         r"<code>([^<\s]{4,40})</code>")
    ],
    "DUCK ARMY": [
        ("https://beebom.com/duck-army-codes/",
         r"<li>\s*([A-Za-z0-9_!]{4,40})[:\s]")
    ],
    "MONKEY TYCOON": [
        ("https://beebom.com/roblox-monkey-tycoon-codes/",
         r"<li>\s*([A-Za-z0-9_!]{4,40})[:\s]")
    ],
    # …더 많은 게임·URL 추가 가능…
}

# ── 3) HTML 내 만료 표시 제거 ─────────────────────────────
def strip_expired(html_txt: str) -> str:
    soup = BeautifulSoup(html_txt, "html.parser")
    for tag in soup.find_all(["del", "strike"]):
        tag.decompose()
    return re.sub(r"(?i)expired", "", str(soup))

# ── 4) 인게임 코드 스크래핑 ─────────────────────────────
def scrape_game_codes() -> dict:
    results = {}
    for eng, sources in sources_map.items():
        raw = []
        for url, pat in sources:
            try:
                txt = strip_expired(requests.get(url, headers=HEADERS, timeout=15).text)
                found = re.findall(pat, txt, flags=re.I)
                print(f"[{eng}] {url} → raw: {len(found)}")
                raw += found
            except Exception as e:
                print(f"[{eng}] ERR fetching {url}: {e}")
        valid = sorted({c.strip().upper() for c in raw if 4 <= len(c.strip()) <= 40})
        if valid:
            results[eng] = valid
            print(f"[{eng}] → valid: {len(valid)}")
    return results

# ── 5) 일반 프로모 코드 검증 ─────────────────────────────
def create_redeem_session() -> requests.Session:
    cookie = os.getenv("ROBLOX_SECURITY")
    if not cookie:
        raise RuntimeError("Environment variable ROBLOX_SECURITY is not set.")
    sess = requests.Session()
    sess.headers.update(HEADERS)
    sess.cookies[".ROBLOSECURITY"] = cookie
    init = sess.post(REDEEM_URL, json={"code": ""}, timeout=10)
    token = init.headers.get("x-csrf-token")
    if not token:
        raise RuntimeError("Failed to obtain X-CSRF-TOKEN.")
    sess.headers.update({"x-csrf-token": token})
    return sess

def validate_promo(sess: requests.Session, code: str) -> bool:
    try:
        data = sess.post(REDEEM_URL, json={"code": code}, timeout=10).json()
        return data.get("success", False)
    except Exception:
        return False

# ── 6) 메인 ─────────────────────────────────────────────
def main():
    output = []

    # A) 스크래핑된 인게임 코드
    game_codes = scrape_game_codes()
    for eng, codes in game_codes.items():
        kor = game_name_map.get(eng, eng)
        for c in codes:
            output.append({
                "game": f"{kor} ({eng})",
                "code": c,
                "type": "in-game",
                "expires": None,
                "verified": TODAY
            })

    # B) 일반 프로모션 코드 검증 (예시)
    sess = create_redeem_session()
    for code in ["SPIDERCOLA", "TWEETROBLOX", "SUMMERSALE2025"]:
        valid = validate_promo(sess, code)
        print(f"[Promo] {code} → {'VALID' if valid else 'INVALID'}")
        if valid:
            output.append({
                "game": "로블록스 프로모션",
                "code": code,
                "type": "promo",
                "expires": TODAY,
                "verified": TODAY
            })

    # C) 저장
    output.sort(key=lambda x: (x["game"], x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ Total: {len(output)} coupons across {len(game_codes)} games + promos")

if __name__ == "__main__":
    main()
