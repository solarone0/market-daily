"""Yahoo Finance 차트 API에서 주요 지표를 받아 data/market.json으로 저장한다."""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "market.json"

# (그룹, 심볼, 표시 이름, 단위)
SERIES = [
    ("해외", "^GSPC", "S&P 500", ""),
    ("해외", "^IXIC", "나스닥", ""),
    ("해외", "^N225", "닛케이 225", ""),
    ("해외", "^TNX", "美 10년물 금리", "%"),
    ("해외", "BZ=F", "브렌트유", "$"),
    ("해외", "GC=F", "금", "$"),
    ("국내", "^KS11", "코스피", ""),
    ("국내", "^KQ11", "코스닥", ""),
    ("국내", "KRW=X", "원/달러", "원"),
    ("국내", "JPY=X", "엔/달러", "엔"),
    ("가상화폐", "BTC-USD", "비트코인", "$"),
    ("가상화폐", "ETH-USD", "이더리움", "$"),
]

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range=6mo&interval=1d"


def fetch(symbol):
    url = URL.format(urllib.parse.quote(symbol))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        result = json.load(r)["chart"]["result"][0]
    meta = result["meta"]
    offset = meta.get("gmtoffset", 0)

    def day(ts):  # 거래소 현지 날짜
        return datetime.fromtimestamp(ts + offset, timezone.utc).strftime("%Y-%m-%d")

    closes = result["indicators"]["quote"][0]["close"]
    points = [[day(t), round(c, 4)] for t, c in zip(result["timestamp"], closes) if c is not None]
    # 일봉에 오늘 값이 늦게 반영되는 경우가 있어 최신가로 마지막 점을 맞춘다
    last = round(meta.get("regularMarketPrice") or points[-1][1], 4)
    today = day(meta.get("regularMarketTime", result["timestamp"][-1]))
    if points and points[-1][0] == today:
        points[-1][1] = last
    else:
        points.append([today, last])
    if len(points) < 2:
        raise ValueError("데이터 부족")
    return {"last": last, "change": round((last / points[-2][1] - 1) * 100, 2), "points": points}


def main():
    old = {}
    if OUT.exists():
        old = {s["symbol"]: s for s in json.loads(OUT.read_text(encoding="utf-8"))["series"]}
    series, failed = [], []
    for group, symbol, name, unit in SERIES:
        try:
            data = fetch(symbol)
        except Exception as e:  # 한 종목 실패가 전체를 막지 않게 이전 값 유지
            failed.append(f"{symbol}: {e}")
            if symbol not in old:
                continue
            data = {k: old[symbol][k] for k in ("last", "change", "points")}
        series.append({"group": group, "symbol": symbol, "name": name, "unit": unit, **data})
        time.sleep(0.5)
    if not series:
        sys.exit("모든 지표 수집 실패")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {"updated": datetime.now(timezone.utc).isoformat(timespec="minutes"), "series": series},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"{len(series)}개 저장" + (f", 실패: {failed}" if failed else ""))


if __name__ == "__main__":
    main()
