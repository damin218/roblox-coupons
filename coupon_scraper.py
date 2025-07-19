#!/usr/bin/env python3
# coding: utf-8

import os
import re
import json
import datetime
import pathlib
import requests
from bs4 import BeautifulSoup

# ── 기본 설정 ─────────────────────────────────────────
TODAY      = datetime.date.today().isoformat()
REDEEM_URL = "https://billing.roblox.com/v1/promocodes/redeem"
HEADERS    = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ── 1) 영어→한글 게임명 매핑 ───────────────────────────
game_name_map = {
    "BLOX FRUITS":          "블록스 프루츠",
    "SHINDO LIFE":          "신도 라이프",
    "BEE SWARM SIMULATOR":  "비 스웜 시뮬레이터",
    "ADOPT ME!":            "어답트 미!",
    "MURDER MYSTERY 2":     "머더 미스터리 2",
    "TOWER OF HELL":        "타워 오브 헬",
    "ARSENAL":              "아스널",
    "PET SIMULATOR X":      "펫 시뮬레이터 X",
    "MAD CITY":             "매드 시티",
    "DRESS TO IMPRESS":     "드레스 투 임프레스",
    "BROOKHAVEN":           "브룩헤이븐",
    "JAILBREAK":            "제일브레이크",
    "CAPYBARA EVOLUTION":   "카피바라 이볼루션",
    "DUCK ARMY":            "덕 아미",
    "MONKEY TYCOON":        "몽키 타이쿤",
    "WELCOME TO BLOXBURG":  "웰컴 투 블록스버그",
    "ANIME FIGHTERS SIM":   "애니메 파이터즈",
    "KING LEGACY":          "킹 레거시",
    "PET SIMULATOR 99":     "펫 시뮬레이터 99",
    "WEAPON FIGHTING SIM":  "웨폰 파이팅 시뮬레이터",
    "ALL STAR TOWER DEF":   "올 스타 타워 디펜스",
    "BUILD A BOAT FOR TREASURE": "빌드 어 보트 포 트레저",
    "BLUE LOCK RIVALS":     "블루 락 라이벌즈",
    "DRAGON ADVENTURES":    "드래곤 어드벤처",
    "VEHICLE SIMULATOR":    "비히클 시뮬레이터",
    "PHANTOM FORCES":       "팬텀 포스",
    # …추가 가능…
}

# ── 2) 영어→게임 실행 링크 매핑 ───────────────────────
game_links_map = {
    "BLOX FRUITS":          "https://www.roblox.com/games/2753915549/Blox-Fruits",
    "SHINDO LIFE":          "https://www.roblox.com/games/4616652839/Shindo-Life-240",
    "BEE SWARM SIMULATOR":  "https://www.roblox.com/games/1537690962/Bee-Swarm-Simulator",
    "ADOPT ME!":            "https://www.roblox.com/games/920587237/Adopt-Me",
    "MURDER MYSTERY 2":     "https://www.roblox.com/games/142823291/Murder-Mystery-2",
    "TOWER OF HELL":        "https://www.roblox.com/games/1962086868/Tower-of-Hell",
    "ARSENAL":              "https://www.roblox.com/games/286090429/Arsenal",
    "PET SIMULATOR X":      "https://www.roblox.com/games/6284583030/Pet-Simulator-X",
    "MAD CITY":             "https://www.roblox.com/games/1224212277/Mad-City-Chapter-2",
    "DRESS TO IMPRESS":     "https://www.roblox.com/games/15101393044/Dress-To-Impress",
    "BROOKHAVEN":           "https://www.roblox.com/games/4924922222/Brookhaven",
    "JAILBREAK":            "https://www.roblox.com/games/606849621/Jailbreak",
    "CAPYBARA EVOLUTION":   "https://www.roblox.com/games/3275705894/Capybara-Evolution",
    "DUCK ARMY":            "https://www.roblox.com/games/5064521273/Duck-Army",
    "MONKEY TYCOON":        "https://www.roblox.com/games/6364617971/Monkey-Tycoon",
    "WELCOME TO BLOXBURG":  "https://www.roblox.com/games/185655149/Welcome-to-Bloxburg",
    "ANIME FIGHTERS SIM":   "https://www.roblox.com/games/4834945293/Anime-Fighters-Simulator",
    "KING LEGACY":          "https://www.roblox.com/games/2753915549/King-Legacy",  # 예시
    "PET SIMULATOR 99":     "https://www.roblox.com/games/6078818642/Pet-Simulator-99",
    "WEAPON FIGHTING SIM":  "https://www.roblox.com/games/1412608525/Weapon-Fighting-Simulator",
    "ALL STAR TOWER DEF":   "https://www.roblox.com/games/2153271816/All-Star-Tower-Defense",
    "BUILD A BOAT FOR TREASURE": "https://www.roblox.com/games/537413528/Build-A-Boat-For-Treasure",
    "BLUE LOCK RIVALS":     "https://www.roblox.com/games/71289778/Blue-Lock-Rivals",
    "DRAGON ADVENTURES":    "https://www.roblox.com/games/466696001/Dragon-Adventures",
    "VEHICLE SIMULATOR":    "https://www.roblox.com/games/295716640/Vehicle-Simulator",
    "PHANTOM FORCES":       "https://www.roblox.com/games/292439477/Phantom-Forces",
    # …추가 가능…
}

# ── 3) 전문 사이트 쿠폰 소스맵 ─────────────────────────
sources_map = {
    "BLOX FRUITS": [
        ("https://www.pcgamesn.com/blox-fruits/codes",
         r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
        ("https://gamerant.com/blox-fruits-codes/",
         r"<code>([^<\s]{4,40})</code>"),
        ("https://twinfinite.net/2025/07/blox-fruits-roblox-codes/",
         r"<li>\s*<strong>([^<\s]{4,40})</strong>"),
    ],
    "SHINDO LIFE": [
        ("https://www.pockettactics.com/shindo-life/codes",
         r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
        ("https://beebom.com/roblox-shindo-life-codes/",
         r"<code>([^<\s]{4,40})</code>"),
        ("https://www.gamespot.com/articles/shindo-life-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "BEE SWARM SIMULATOR": [
        ("https://beebom.com/roblox-bee-swarm-simulator-codes/",
         r"\*\s+([A-Za-z0-9_!]{4,40})[:\s-]"),
        ("https://gamerant.com/bee-swarm-simulator-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "ADOPT ME!": [
        ("https://progameguides.com/roblox/adopt-me-codes/",
         r"<li>\s*<strong>([^<\s]{4,40})</strong>"),
        ("https://beebom.com/adopt-me-roblox-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "MURDER MYSTERY 2": [
        ("https://www.pocketgamer.com/murder-mystery-2/codes/",
         r"<code>([^<\s]{4,40})</code>"),
        ("https://www.gamersdecide.com/articles/murder-mystery-2-codes",
         r"\*\s+([A-Za-z0-9_!]{4,40})"),
    ],
    "TOWER OF HELL": [
        ("https://bo3.gg/games/articles/tower-of-hell-codes",
         r"<code>([^<\s]{4,40})</code>"),
        ("https://gamerant.com/tower-of-hell-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "ARSENAL": [
        ("https://www.pockettactics.com/arsenal/codes",
         r"<code>([^<\s]{4,40})</code>"),
        ("https://robloxarsenal.fandom.com/wiki/Codes",
         r"<code>([^<\s]{4,40})</code>"),
        ("https://gamerant.com/arsenal-roblox-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "PET SIMULATOR X": [
        ("https://www.pockettactics.com/pet-simulator-x/codes",
         r"<code>([^<\s]{4,40})</code>"),
        ("https://gamerant.com/pet-simulator-x-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "MAD CITY": [
        ("https://www.pocketgamer.com/roblox/mad-city-codes/",
         r"<code>([^<\s]{4,40})</code>"),
        ("https://progameguides.com/roblox/mad-city-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "DRESS TO IMPRESS": [
        ("https://progameguides.com/roblox/dress-to-impress-codes/",
         r"<code>([^<\s]{4,40})</code>"),
        ("https://beebom.com/roblox-dress-to-impress-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "BROOKHAVEN": [
        ("https://progameguides.com/roblox/brookhaven-codes/",
         r"<code>([^<\s]{4,40})</code>"),
        ("https://gamerant.com/brookhaven-roblox-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "JAILBREAK": [
        ("https://progameguides.com/roblox/jailbreak-codes/",
         r"<code>([^<\s]{4,40})</code>"),
        ("https://gamerant.com/jailbreak-roblox-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "CAPYBARA EVOLUTION": [
        ("https://beebom.com/capybara-evolution-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "DUCK ARMY": [
        ("https://beebom.com/duck-army-codes/",
         r"<li>\s*([A-Za-z0-9_!]{4,40})[:\s]"),
    ],
    "MONKEY TYCOON": [
        ("https://beebom.com/roblox-monkey-tycoon-codes/",
         r"<li>\s*([A-Za-z0-9_!]{4,40})[:\s]"),
    ],
    "WELCOME TO BLOXBURG": [
        ("https://www.pockettactics.com/welcome-to-bloxburg-codes",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "ANIME FIGHTERS SIM": [
        ("https://www.pockettactics.com/anime-fighters-simulator/codes",
         r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
        ("https://gamerant.com/anime-fighters-simulator-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "KING LEGACY": [
        ("https://www.pockettactics.com/king-legacy/codes",
         r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
    ],
    "PET SIMULATOR 99": [
        ("https://beebom.com/roblox-pet-simulator-99-codes/",
         r"<strong>([^<\s]{4,40})</strong>"),
    ],
    "WEAPON FIGHTING SIM": [
        ("https://www.pockettactics.com/weapon-fighting-simulator/codes",
         r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
    ],
    "ALL STAR TOWER DEF": [
        ("https://www.pockettactics.com/all-star-tower-defense/codes",
         r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
    ],
    "BUILD A BOAT FOR TREASURE": [
        ("https://progameguides.com/roblox/build-a-boat-for-treasure-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "BLUE LOCK RIVALS": [
        ("https://beebom.com/blue-lock-rivals-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "DRAGON ADVENTURES": [
        ("https://progameguides.com/roblox/dragon-adventures-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "VEHICLE SIMULATOR": [
        ("https://progameguides.com/roblox/vehicle-simulator-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
    "PHANTOM FORCES": [
        ("https://progameguides.com/roblox/phantom-forces-codes/",
         r"<code>([^<\s]{4,40})</code>"),
    ],
}

# ── 4) HTML 만료 표시 제거 ─────────────────────────────
def strip_expired(html_txt: str) -> str:
    soup = BeautifulSoup(html_txt, "html.parser")
    for tag in soup.find_all(["del", "strike"]):
        tag.decompose()
    return re.sub(r"(?i)expired", "", str(soup))

# ── 5) 인게임 코드 스크래핑 ─────────────────────────────
def scrape_game_codes() -> dict:
    results = {}
    for eng, sources in sources_map.items():
        raw = []
        for url, pat in sources:
            try:
                html_txt = strip_expired(requests.get(url, headers=HEADERS, timeout=15).text)
                found = re.findall(pat, html_txt, flags=re.I)
                raw += found
            except Exception as e:
                print(f"[{eng}] ERR fetching {url}: {e}")
        valid = sorted({c.strip().upper() for c in raw if 4 <= len(c.strip()) <= 40})
        if valid:
            results[eng] = valid
    return results

# ── 6) 일반 프로모션 코드 검증 ─────────────────────────
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
        return sess.post(REDEEM_URL, json={"code": code}, timeout=10).json().get("success", False)
    except:
        return False

# ── 7) 메인 ────────────────────────────────────────────
def main():
    output = []

    # A) 인게임 코드
    game_codes = scrape_game_codes()
    for eng, codes in game_codes.items():
        kor = game_name_map.get(eng, eng)
        url = game_links_map.get(eng, "")
        for c in codes:
            output.append({
                "game":     f"{kor} ({eng})",
                "code":     c,
                "type":     "in-game",
                "url":      url,
                "verified": TODAY
            })

    # B) 일반 프로모션 코드 검증 (예시 목록)
    sess = create_redeem_session()
    for code in ["SPIDERCOLA", "TWEETROBLOX", "SUMMERSALE2025"]:
        valid = validate_promo(sess, code)
        print(f"[Promo] {code} → {'VALID' if valid else 'INVALID'}")
        if valid:
            output.append({
                "game":     "로블록스 프로모션",
                "code":     code,
                "type":     "promo",
                "url":      "https://www.roblox.com/promocodes",
                "verified": TODAY
            })

    # C) 결과 저장
    output.sort(key=lambda x: (x["game"], x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ Total: {len(output)} coupons across {len(game_codes)} games + promos")

if __name__ == "__main__":
    main()
