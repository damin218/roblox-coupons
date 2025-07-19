import json, re, requests, datetime, pathlib
from bs4 import BeautifulSoup

# --------- ① 스크랩할 페이지 목록 ------------
SOURCES = [
    ("https://www.pockettactics.com/blox-fruits/codes",     r"<code>([^<]+)</code>"),
    ("https://www.beebom.com/shindo-life-codes/",           r"<strong>([^<\s]{4,30})</strong>")
]
TODAY = datetime.date.today()

def fetch(url, pattern):
    html = requests.get(url, timeout=20).text
    return re.findall(pattern, html, re.I)

def load_old():
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

def main():
    codes = load_old()
    for url, pat in SOURCES:
        for code in fetch(url, pat):
            game = "Blox Fruits" if "blox" in url else "Shindo Life"
            if not any(c["code"] == code for c in codes):
                codes.append({"game": game, "code": code, "expires": None})
    # ─── ③ 만료 필터 (예: "2025-07-18") ───
    codes = [c for c in codes if not c["expires"] or c["expires"] >= str(TODAY)]
    # ④ 저장
    pathlib.Path("coupons.json").write_text(
        json.dumps(sorted(codes, key=lambda x: (x["game"], x["code"])), ensure_ascii=False, indent=2),
        encoding="utf-8")
if __name__ == "__main__":
    main()
