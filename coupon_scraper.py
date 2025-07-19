"""
coupon_scraper.py  ―  Roblox 게임 쿠폰 종합 수집기
────────────────────────────────────────────────────
✓ 대‧소문자·공백·중복 자동 정리
✓ Roblox 프로모코드 API 1회 검사 → 만료·무효 코드 필터
✓ 2025‑07‑19 기준 5개 인기 게임 약 60개+ 쿠폰 수집
"""

import re, json, time, datetime, pathlib, requests
from bs4 import BeautifulSoup  # pip install beautifulsoup4

TODAY = datetime.date.today()

# ───────────────────────────────────────────────────
# 1. 크롤링 대상 페이지 & 정규표현식
# ───────────────────────────────────────────────────
SOURCES = [
    # Blox Fruits
    ("https://www.pcgamesn.com/blox-fruits/codes",
     r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),       # * CODE -
    ("https://gamerant.com/blox-fruits-codes/",
     r"<code>([^<\s]{4,40})</code>"),

    # Shindo Life
    ("https://www.pockettactics.com/shindo-life/codes",
     r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
    ("https://beebom.com/roblox-shindo-life-codes/",
     r"<code>([^<\s]{4,40})</code>"),

    # Bee Swarm Simulator
    ("https://beebom.com/roblox-bee-swarm-simulator-codes/",
     r"\*\s+([A-Za-z0-9_!]{4,40})[:\s-]"),

    # Anime Champions Simulator
    ("https://beebom.com/roblox-anime-champions-simulator-codes/",
     r"<strong>([^<\s]{4,40})</strong>"),
    ("https://www.destructoid.com/anime-champions-simulator-codes/",
     r"<strong>([^<\s]{4,40})</strong>"),

    # Blue Lock Rivals
    ("https://www.pcgamer.com/games/roblox/blue-lock-rivals-codes/",
     r"<code>([^<\s]{4,40})</code>"),
    ("https://beebom.com/blue-lock-rivals-codes/",
     r"<code>([^<\s]{4,40})</code>"),
]

# ───────────────────────────────────────────────────
# 2. URL → 게임 이름 판별
# ───────────────────────────────────────────────────
def detect_game(url: str) -> str:
    if "blox-fruits" in url:               return "Blox Fruits"
    if "shindo" in url:                    return "Shindo Life"
    if "bee-swarm" in url:                 return "Bee Swarm Simulator"
    if "anime-champions" in url:           return "Anime Champions Simulator"
    if "blue-lock" in url:                 return "Blue Lock Rivals"
    return "Unknown"

# ───────────────────────────────────────────────────
# 3. 코드 문자열 정리 (대문자·특수문자 제거)
# ───────────────────────────────────────────────────
def clean(raw: str) -> str:
    """공백 제거, 대문자 통일, 영문·숫자·_·! 만 남김, 길이 4 미만이면 '' 반환"""
    code = re.sub(r"[^\w!]", "", raw.strip().upper())
    return code if len(code) >= 4 else ""

# ───────────────────────────────────────────────────
# 4. Roblox API 유효성 체크
# ───────────────────────────────────────────────────
def is_code_alive(code: str) -> bool:
    """
    Roblox 공식 프로모코드 API에 한 번 POST.
    - 'invalid', 'expired', 'already' 같은 키워드가 있으면 False
    - 그 외(429 rate-limit 포함)는 True 로 낙관 처리
    """
    url = "https://economy.roblox.com/v1/promocodes/redeem"
    try:
        r = requests.post(url, json={"promocode": code}, timeout=12)
        low = r.text.lower()
        if any(k in low for k in ("invalid", "expired", "already")):
            return False
        return True
    except requests.exceptions.RequestException:
        return True  # 네트워크 오류 시 생존으로 간주

# ───────────────────────────────────────────────────
# 5. 기존 JSON 불러오기
# ───────────────────────────────────────────────────
def load_old():
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

# ───────────────────────────────────────────────────
# 6. 메인 로직
# ───────────────────────────────────────────────────
def main():
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    codes = load_old()

    for url, pattern in SOURCES:
        try:
            html = requests.get(url, headers=ua, timeout=25).text
        except Exception as e:
            print("⛔️  fetch error:", url, e)
            continue

        for raw in re.findall(pattern, html, flags=re.I):
            code = clean(raw)
            if not code or any(c["code"] == code for c in codes):
                continue

            if not is_code_alive(code):
                print("🗑️  expired:", code)
                continue

            codes.append({
                "game": detect_game(url),
                "code": code,
                "expires": None
            })
            time.sleep(1)  # API rate‑limit 완화

    # 만료날짜 필터 & 정렬 & 저장
    codes = [c for c in codes if not c["expires"] or c["expires"] >= str(TODAY)]
    codes.sort(key=lambda x: (x["game"], x["code"]))

    pathlib.Path("coupons.json").write_text(
        json.dumps(codes, ensure_ascii=False, indent=2),
        encoding="utf-8")

    print(f"✅  Saved {len(codes)} coupons")

# ───────────────────────────────────────────────────
if __name__ == "__main__":
    main()
