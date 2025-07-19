import re, json, pathlib, datetime, requests
from bs4 import BeautifulSoup

TODAY = datetime.date.today()

# ── ① 새 소스 URL + 정규식 ────────────────────────────────
SOURCES = [
    # Blox Fruits
    ("https://www.pcgamesn.com/blox-fruits/codes",
     r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),   # * CODE -
    ("https://gamerant.com/blox-fruits-codes/",
     r"<code>([^<\s]{4,40})</code>"),

    # Shindo Life
    ("https://www.pockettactics.com/shindo-life/codes",
     r"\*\s+([A-Za-z0-9_!]{4,40})\s+-"),
    ("https://beebom.com/roblox-shindo-life-codes/",
     r"<code>([^<\s]{4,40})</code>"),

    # Bee Swarm Simulator
    ("https://beebom.com/roblox-bee-swarm-simulator-codes/",
     r"\*\s+([A-Za-z0-9_!]{4,40})[:\s-]"),

    # Anime Champions Simulator
    ("https://beebom.com/roblox-anime-champions-simulator-codes/",
     r"<strong>([^<\s]{4,40})</strong>"),
    ("https://www.destructoid.com/anime-champions-simulator-codes/",
     r"<strong>([^<\s]{4,40})</strong>"),

    # Blue Lock Rivals
    ("https://www.pcgamer.com/games/roblox/blue-lock-rivals-codes/",
     r"<code>([^<\s]{4,40})</code>"),
    ("https://beebom.com/blue-lock-rivals-codes/",
     r"<code>([^<\s]{4,40})</code>"),
]

# ── ② 간단한 게임명 매핑 ────────────────────────────────
def detect_game(url: str) -> str:
    if "blox-fruits" in url: return "Blox Fruits"
    if "shindo" in url: return "Shindo Life"
    if "bee-swarm" in url: return "Bee Swarm Simulator"
    if "anime-champions" in url: return "Anime Champions Simulator"
    if "blue-lock" in url: return "Blue Lock Rivals"
    return "Unknown"

# ── ③ 기존 JSON 로드 ───────────────────────────────────
def load_old():
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

# ── ④ 각 페이지에서 코드 수집 ───────────────────────────
def fetch_all():
    codes = load_old()
    for url, pattern in SOURCES:
        try:
            html = requests.get(url, timeout=25).text
        except Exception as e:
            print("⛔", url, e); continue
        found = re.findall(pattern, html, flags=re.I)
        game = detect_game(url)
        for code in found:
            code = code.strip().upper()
            if len(code) < 4: continue
            if not any(c["code"] == code for c in codes):
                codes.append({
                    "game": game,
                    "code": code,
                    "expires": None          # 만료미정
                })
    return codes

# ── ⑤ 만료 필터 + 정렬 + 저장 ──────────────────────────
def main():
    codes = [c for c in fetch_all()
             if not c["expires"] or c["expires"] >= str(TODAY)]
    codes.sort(key=lambda x: (x["game"], x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(codes, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"✅ Saved {len(codes)} coupons")

if __name__ == "__main__":
    main()
