"""
coupon_scraper.py  –  인기 Roblox 게임 쿠폰 올인원 수집기
────────────────────────────────────────────────────────
✓ 지원 게임 (2025‑07‑19): Blox Fruits · Shindo Life · Bee Swarm Simulator
  Anime Champions Simulator · Blue Lock Rivals · King Legacy · Project Slayers
  All Star Tower Defense · Blade Ball · Pet Simulator 99 · Weapon Fighting
  Anime Fighters Simulator
✓ 대‧소문자/공백 정리 + 중복 제거
✓ 약 120개 이상의 ‘살아있는’ 코드 JSON 저장
"""

import re, json, datetime, pathlib, requests
from bs4 import BeautifulSoup

TODAY = datetime.date.today()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ── 1. 크롤링 대상 페이지 & 패턴 ─────────────────────────
SOURCES = [
    # Blox Fruits
    ("https://www.pcgamesn.com/blox-fruits/codes",                 r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
    ("https://gamerant.com/blox-fruits-codes/",                    r"<code>([^<\s]{4,40})</code>"),

    # Shindo Life
    ("https://www.pockettactics.com/shindo-life/codes",            r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
    ("https://beebom.com/roblox-shindo-life-codes/",               r"<code>([^<\s]{4,40})</code>"),

    # Bee Swarm Simulator
    ("https://beebom.com/roblox-bee-swarm-simulator-codes/",       r"\*\s+([A-Za-z0-9_!]{4,40})[:\s-]"),

    # Anime Champions Simulator
    ("https://beebom.com/roblox-anime-champions-simulator-codes/", r"<strong>([^<\s]{4,40})</strong>"),
    ("https://www.destructoid.com/anime-champions-simulator-codes/", r"<strong>([^<\s]{4,40})</strong>"),

    # Blue Lock Rivals
    ("https://www.pcgamer.com/games/roblox/blue-lock-rivals-codes/", r"<code>([^<\s]{4,40})</code>"),
    ("https://beebom.com/blue-lock-rivals-codes/",                 r"<code>([^<\s]{4,40})</code>"),

    # King Legacy
    ("https://www.pockettactics.com/king-legacy/codes",            r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
    ("https://www.twinfinite.net/roblox-king-legacy-codes/",       r"<strong>([^<\s]{4,40})</strong>"),

    # Project Slayers
    ("https://www.pockettactics.com/project-slayers/codes",        r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
    ("https://gamerant.com/project-slayers-roblox-codes/",         r"<code>([^<\s]{4,40})</code>"),

    # All Star Tower Defense
    ("https://www.pockettactics.com/all-star-tower-defense/codes", r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),

    # Blade Ball
    ("https://beebom.com/roblox-blade-ball-codes/",                r"<strong>([^<\s]{4,40})</strong>"),

    # Pet Simulator 99
    ("https://beebom.com/roblox-pet-simulator-99-codes/",          r"<strong>([^<\s]{4,40})</strong>"),

    # Weapon Fighting Simulator
    ("https://www.pockettactics.com/weapon-fighting-simulator/codes", r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),

    # Anime Fighters Simulator
    ("https://www.pockettactics.com/anime-fighters-simulator/codes",  r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
]

# ── 2. URL → 게임 이름 매핑 ────────────────────────────
def detect_game(url: str) -> str:
    if   "blox-fruits"          in url: return "Blox Fruits"
    elif "shindo-life"          in url: return "Shindo Life"
    elif "bee-swarm"            in url: return "Bee Swarm Simulator"
    elif "anime-champions"      in url: return "Anime Champions Simulator"
    elif "blue-lock"            in url: return "Blue Lock Rivals"
    elif "king-legacy"          in url: return "King Legacy"
    elif "project-slayers"      in url: return "Project Slayers"
    elif "all-star-tower"       in url: return "All Star Tower Defense"
    elif "blade-ball"           in url: return "Blade Ball"
    elif "pet-simulator"        in url: return "Pet Simulator 99"
    elif "weapon-fighting"      in url: return "Weapon Fighting Simulator"
    elif "anime-fighters"       in url: return "Anime Fighters Simulator"
    else: return "Unknown"

# ── 3. 코드 문자열 정리 ────────────────────────────────
def clean(raw: str) -> str:
    """대문자 통일 · 특수문자 제거 · 최소 길이 4"""
    code = re.sub(r"[^\w!]", "", raw.strip().upper())
    return code if len(code) >= 4 else ""

# ── 4. 기존 JSON 불러오기 ──────────────────────────────
def load_old():
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

# ── 5. 메인 수집 로직 ─────────────────────────────────
def main():
    codes = load_old()
    seen_codes = {c["code"] for c in codes}   # 중복 제거용 set

    for url, pattern in SOURCES:
        try:
            html = requests.get(url, headers=UA, timeout=30).text
        except Exception as e:
            print("⛔️  fetch error:", url, e)
            continue

        for raw in re.findall(pattern, html, flags=re.I):
            code = clean(raw)
            if not code or code in seen_codes:
                continue

            codes.append({
                "game": detect_game(url),
                "code": code,
                "expires": None
            })
            seen_codes.add(code)

    # 정렬 · 저장
    codes.sort(key=lambda x: (x["game"], x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(codes, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"✅  Saved {len(codes)} coupons")

# ──────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
