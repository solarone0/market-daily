"""Claude API(웹 검색)로 오늘의 경제 칼럼을 써서 data/columns/에 저장한다.

환경변수 ANTHROPIC_API_KEY 필요. 같은 날짜 칼럼이 이미 있으면 건너뛴다(--force로 덮어쓰기).
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent.parent
COLUMNS = ROOT / "data" / "columns"
INDEX = COLUMNS / "index.json"
MARKET = ROOT / "data" / "market.json"
KST = timezone(timedelta(hours=9))

MODEL = "claude-opus-5-5"
MAX_CONTINUATIONS = 5

SYSTEM = """너는 한국어 경제 칼럼니스트다. 네이버 프리미엄 콘텐츠 수준의 뉴스 칼럼(공백 포함 5,000~7,000자)을 쓴다.

원칙
- 해외 외신을 주요 레퍼런스로 삼는다: Financial Times, Nikkei Asia, Yahoo Finance를 우선하고 Bloomberg, Reuters, CNBC, WSJ로 보완한다. 국내는 연합뉴스, 한국경제, 매일경제, Korea Herald, Korea JoongAng Daily 등.
- 웹 검색으로 확인한 사실만 쓴다. 숫자에는 날짜를 붙이고, 확인하지 못한 내용은 쓰지 않는다. 출처끼리 수치가 다르면 더 신뢰할 수 있는 쪽을 쓰거나 범위로 쓴다.
- 함께 주는 시장 데이터(JSON)는 차트에 쓰이는 실제 종가다. 지수·환율·코인 가격은 이 값과 어긋나지 않게 쓴다.
- 문체는 신문 칼럼체(~다)로 쓴다. 숫자는 굵게 강조하되 과하지 않게 한다. 투자 권유는 하지 않는다.

구성(마크다운, 이 순서를 지킨다)
# 제목 (한 줄, 그날의 핵심을 담는다)
*부제: 날짜와 한 줄 요약*

## Ⅰ. 해외
### 소제목들 (금리·중앙은행, 원자재·지정학, 주식·기업, 아시아 등 그날 중요한 것 3~5개)

## Ⅱ. 국내
### 주식
### 부동산
(필요하면 금리·환율 소제목 추가)

## Ⅲ. 가상화폐

## 맺으며: 앞으로 볼 체크리스트
(번호 목록 4~6개)

---
**Sources:**
- [기사 제목](URL) 형식으로 실제로 참고한 기사만

출력은 칼럼 마크다운만 낸다. 앞뒤에 설명이나 인사말을 붙이지 않는다."""


def market_summary():
    if not MARKET.exists():
        return "(시장 데이터 없음)"
    data = json.loads(MARKET.read_text(encoding="utf-8"))
    lines = []
    for s in data["series"]:
        recent = ", ".join(f"{d} {v:g}" for d, v in s["points"][-6:])
        lines.append(f"- {s['group']} | {s['name']}({s['symbol']}): 최근 {recent} / 전일 대비 {s['change']:+.2f}%")
    return "\n".join(lines)


def run(today):
    client = anthropic.Anthropic()
    user = (
        f"오늘은 {today}(KST)다. 직전 24~48시간의 주요 경제 뉴스를 검색해서 오늘자 칼럼을 써 줘.\n\n"
        f"시장 데이터(Yahoo Finance 종가):\n{market_summary()}"
    )
    messages = [{"role": "user", "content": user}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 20}]

    for _ in range(MAX_CONTINUATIONS + 1):
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=64000,
            system=SYSTEM,
            messages=messages,
            tools=tools,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            response = stream.get_final_message()
        if response.stop_reason != "pause_turn":
            break
        # 서버 검색 루프가 한도에 걸리면 같은 대화를 다시 보내 이어서 진행
        messages = [messages[0], {"role": "assistant", "content": response.content}]

    if response.stop_reason == "refusal":
        sys.exit(f"요청 거절: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        sys.exit("max_tokens에 걸려 칼럼이 잘림")

    text = "".join(b.text for b in response.content if b.type == "text")
    start = text.find("# ")
    if start < 0:
        sys.exit("칼럼 형식(# 제목)을 찾지 못함")
    print(f"usage: {response.usage}", file=sys.stderr)
    return text[start:].strip() + "\n"


def main():
    today = datetime.now(KST).strftime("%Y-%m-%d")
    path = COLUMNS / f"{today}.md"
    if path.exists() and "--force" not in sys.argv:
        print(f"{path.name} 이미 있음, 건너뜀")
        return

    column = run(today)
    title = re.match(r"#\s+(.+)", column).group(1).strip()
    COLUMNS.mkdir(parents=True, exist_ok=True)
    path.write_text(column, encoding="utf-8")

    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else []
    index = [c for c in index if c["date"] != today]
    index.insert(0, {"date": today, "title": title})
    index.sort(key=lambda c: c["date"], reverse=True)
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{path.name} 저장: {title}")


if __name__ == "__main__":
    main()
