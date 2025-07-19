import re, json, html, datetime, pathlib, requests
from bs4 import BeautifulSoup

UA = {"User-Agent":"Mozilla/5.0"}
TODAY = datetime.date.today().isoformat()

# 1️⃣  1차 소스 (갱신 빠른 사이트만)
SOURCES = {
    "Blox Fruits": [
        ("https://www.pcgamesn.com/blox-fruits/codes", r"\*\s+([A-Za-z0-9_!]{4,20})\s+-")
    ],
    "Shindo Life": [
        ("https://www.pockettactics.com/shindo-life/codes", r"\*\s+([A-Za-z0-9_!]{4,20})\s+-")
    ],
    "Bee Swarm Simulator": [
        ("https://beebom.com/roblox-bee-swarm-simulator-codes/", r"\*\s+([A-Za-z0-9_!]{4,20})[:\s-]")
    ],
    "Blade Ball": [
        ("https://beebom.com/roblox-blade-ball-codes/", r"<strong>([^<\s]{4,20})</strong>")
    ],
    "Anime Champions Simulator": [
        ("https://beebom.com/roblox-anime-champions-simulator-codes/", r"<strong>([^<\s]{4,20})</strong>")
    ],
    # …필요 게임 추가
}

# 2️⃣  코드 클린업
def clean(code:str)->str:
    code = re.sub(r"[^\w!]", "", html.unescape(code).strip().upper())
    if not (5 <= len(code) <= 20) or code.isdigit() or not code[0].isalpha():
        return ""
    return code

# 3️⃣  페이지 내부 'Expired' 라인 제거
def filter_expired_in_html(raw_html:str)->str:
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup.find_all(["del","strike"]):
        tag.decompose()
    # 키워드 기반
    text = str(soup)
    text = re.sub(r"(?i)expired[^<]{0,30}</?[^>]+>", "", text)
    return text

# 4️⃣  Roblox 공식 프로모코드 API (글로벌 코드만 해당)
def is_promo_api_alive(code:str)->bool:
    url="https://economy.roblox.com/v1/promocodes/redeem"
    try:
        r=requests.post(url,json={"promocode":code},timeout=12)
        bad=("invalid","expired","already","code has")
        return not any(b in r.text.lower() for b in bad)
    except Exception:
        return True   # 네트워크 오류 → true

# 5️⃣  메인 수집
def main():
    final=[]
    seen=set()

    for game,(entries) in SOURCES.items():
        for url,pattern in entries:
            try:
                html_txt=requests.get(url,headers=UA,timeout=30).text
                html_txt=filter_expired_in_html(html_txt)
            except Exception as e:
                print("⚠️",game,"fetch fail",e);continue

            for raw in re.findall(pattern,html_txt,re.I):
                code=clean(raw)
                if not code or code in seen: continue

                # 글로벌 프로모코드만 API로 이중 체크
                api_ok = is_promo_api_alive(code) if game=="Roblox Promo" else True
                if not api_ok:
                    print("🗑️",code,"API expired");continue

                final.append({
                    "game":game,
                    "code":code,
                    "verified":TODAY
                })
                seen.add(code)

    pathlib.Path("coupons.json").write_text(
        json.dumps(sorted(final,key=lambda x:(x["game"],x["code"])),
                   ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"✅ {len(final)} codes saved across {len({c['game'] for c in final})} games")

if __name__=="__main__":
    main()
