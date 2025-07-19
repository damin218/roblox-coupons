#!/usr/bin/env python3
# coupon_scraper.py ― 유효 쿠폰이 있는 게임만 리스트업

import re, json, html, datetime, pathlib, requests
from bs4 import BeautifulSoup

UA    = {"User-Agent":"Mozilla/5.0"}
TODAY = datetime.date.today().isoformat()

# ── 1) 게임별 전문 사이트 & 정규식 맵 ───────────────────
#    필요하면 여기에 추가하세요.
sources_map = {
  "Blox Fruits": [
    ("https://www.pcgamesn.com/blox-fruits/codes",
     r"\*\s+([A-Za-z0-9_!]{5,20})\s+-"),
    ("https://gamerant.com/blox-fruits-codes/",
     r"<code>([^<\s]{5,20})</code>"),
  ],
  "Shindo Life": [
    ("https://www.pockettactics.com/shindo-life/codes",
     r"\*\s+([A-Za-z0-9_!]{5,20})\s+-"),
  ],
  "Bee Swarm Simulator": [
    ("https://beebom.com/roblox-bee-swarm-simulator-codes/",
     r"\*\s+([A-Za-z0-9_!]{4,30})[:\s-]"),
  ],
  # … 여기에 인기 게임별 코드 페이지를 계속 추가 …
}

# ── HTML 내 <del>, strike, “Expired” 제거 ───────────────
def strip_expired(html_txt: str) -> str:
    soup = BeautifulSoup(html_txt, "html.parser")
    # 지워버릴 태그
    for t in soup.find_all(["del","strike"]):
        t.decompose()
    # “expired” 단어 제거
    return re.sub(r"(?i)expired","", str(soup))

# ── 코드 클린업 & 유효성 검사 ─────────────────────────────
def clean(raw: str) -> str:
    txt  = html.unescape(raw).strip().upper()
    code = re.sub(r"[^\w!]","", txt)
    # 코드 길이 및 첫글자 알파벳 조건
    return code if 5 <= len(code) <= 20 and code[0].isalpha() else ""

# ── 기존 coupons.json 로드 ───────────────────────────
def load_old() -> list:
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

# ── 메인 루프 ─────────────────────────────────────────
def main():
    old     = load_old()
    seen    = {c["code"] for c in old}
    results = []

    for game, sources in sources_map.items():
        raw_codes = []
        for url, pattern in sources:
            try:
                resp = requests.get(url, headers=UA, timeout=15)
                txt  = strip_expired(resp.text)
                found = re.findall(pattern, txt, flags=re.I)
                print(f"[{game}] {url} → found {len(found)} raw")
                raw_codes += found
            except Exception as e:
                print(f"[{game}] ERROR fetching {url}: {e}")

        # clean & dedupe
        valid = []
        for r in raw_codes:
            c = clean(r)
            if c and c not in seen:
                valid.append(c)
                seen.add(c)

        # 유효 코드가 한 개라도 있을 때만 결과에 포함
        if valid:
            for code in sorted(valid):
                results.append({
                    "game":      game,
                    "code":      code,
                    "expires":   None,      # 필요 시 여기에 만료일 문자열 입력
                    "verified":  TODAY
                })
            print(f"[{game}] → {len(valid)} valid codes, included.")
        else:
            print(f"[{game}] → no valid codes, skipped.")

    # 정렬·저장
    results.sort(key=lambda x: (x["game"].upper(), x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ Finished. {len(results)} codes across {len({r['game'] for r in results})} games.")

if __name__ == "__main__":
    main()
