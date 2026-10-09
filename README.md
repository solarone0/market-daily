# Market Daily

해외 외신(FT · Nikkei Asia · Yahoo Finance 등)으로 읽는 매일의 경제 칼럼과 주요 지표. GitHub Pages로 서비스한다.

- `scripts/fetch_market.py`: Yahoo Finance 차트 API → `data/market.json` (6개월 일봉)
- `scripts/write_column.py`: Claude API(웹 검색) → `data/columns/YYYY-MM-DD.md`, `index.json`
- `.github/workflows/daily.yml`: 매일 07:00 KST 실행 후 `data/` 커밋. 수동 실행은 Actions 탭의 `daily` → Run workflow.

설정: 저장소 Secret `ANTHROPIC_API_KEY`. 없으면 지표만 갱신된다.

로컬 확인: `python -m http.server 8800` → `127.0.0.1:8800`
