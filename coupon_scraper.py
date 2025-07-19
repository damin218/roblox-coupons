#!/usr/bin/env python3
# coupon_scraper.py ― 구조 변경에 강건한 쿠폰 수집기

import re, json, html, datetime, pathlib, requests
from bs4 import BeautifulSoup

# ── 설정 ─────────────────────────────────────────────
UA    = {"User-Agent":"Mozilla/5.0"}
TODAY = datetime.date.today().isoformat()

# ── 1) 사이트별 URL 목록 ─────────────────────────────────
#    여기에 쿠폰 페이지 URL만 추가해 주세요.
#    (게임명은 결과 정렬용, key 순서대로 반복)
sources_map = {
  "Blox Fruits": [
    "https://www.pcgamesn.com/blox-fruits/codes",
    "https://gamerant.com/blox-fruits-codes/"
  ],
  "Shindo Life": [
    "https://www.pockettactics.com/shindo-life/codes"
  ],
  "Bee Swarm Simulator": [
    "https://beebom.com/roblox-bee-swarm-simulator-codes/"
  ],
  # … 추가하고 싶은 게임 페이지 URL 계속 …
}

# ── HTML 내 만료 표시 제거 ────────────────────────────
def strip_expired(html_txt: str) -> str:
    soup = BeautifulSoup(html_txt, "html.parser")
    for t in soup.find_all(["del","strike"]):
        t.decompose()
    return re.sub(r"(?i)expired","", str(soup))

# ── 텍스트에서 쿠폰 후보 모두 뽑아내기 ───────────────────
COUPON_RE = re.compile(r"\b[A-Z0-9!]{4,20}\b")
def extract_codes_from(html_txt: str) -> list[str]:
    # 1) 만료 태그 제거
    clean_html = strip_expired(html_txt)
    # 2) 모든 텍스트로 변환
    text = BeautifulSoup(clean_html, "html.parser").get_text(separator=" ")
    # 3) 대문자+숫자 패턴으로 후보 추출
    return COUPON_RE.findall(text)

# ── 개별 문자열 정리 & 유효성 검사 ─────────────────────
def clean(raw: str) -> str:
    s    = html.unescape(raw).strip().upper()
    code = re.sub(r"[^\w!]","", s)
    # 4~20자, 첫글자 알파벳 조건
    return code if 4 <= len(code) <= 20 and code[0].isalpha() else ""

# ── 기존 coupons.json 로드 ───────────────────────────
def load_old() -> list[dict]:
    try:
        return json.load(open("coupons.json", encoding="utf-8"))
    except FileNotFoundError:
        return []

# ── 메인 ─────────────────────────────────────────────
def main():
    old   = load_old()
    seen  = {c["code"] for c in old}
    out   = []

    for game, urls in sources_map.items():
        raw_codes = []
        for url in urls:
            try:
                resp = requests.get(url, headers=UA, timeout=15)
                resp.raise_for_status()
                found = extract_codes_from(resp.text)
                print(f"[{game}] {url} → found {len(found)} raw candidates")
                raw_codes += found
            except Exception as e:
                print(f"[{game}] ERROR fetching {url}: {e}")

        # 정리 & 중복 제거
        valid = []
        for r in raw_codes:
            c = clean(r)
            if c and c not in seen:
                valid.append(c)
                seen.add(c)

        # 유효 코드가 있으면 결과에 추가
        if valid:
            for code in sorted(set(valid)):
                out.append({
                    "game":     game,
                    "code":     code,
                    "expires":  None,
                    "verified": TODAY
                })
            print(f"[{game}] → {len(valid)} valid codes, included.")
        else:
            print(f"[{game}] → no valid codes, skipped.")

    # 결과 저장
    out.sort(key=lambda x:(x["game"].upper(), x["code"]))
    pathlib.Path("coupons.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ Finished. {len(out)} codes across {len({r['game'] for r in out})} games.")

if __name__=="__main__":
    main()
