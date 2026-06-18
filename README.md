# 글로벌 게임·빅테크 주가/시가총액 대시보드

32개 글로벌 게임/빅테크 상장사의 현재가, 등락률, 시가총액을 GitHub Pages에서 보여주는 정적 대시보드입니다.

## 데이터 구조

- `data/companies.csv`: 회사/티커/거래소/통화 매핑
- `data/exchange_rates.csv`: KRW 고정 환율
- `scripts/fetch_market_data.py`: Yahoo Finance chart endpoint + yfinance shares cache 기반 수집
- `scripts/build_dashboard.py`: `docs/index.html` 생성
- `docs/data/market_quotes.json`: 대시보드가 읽는 최신 데이터
- `docs/data/market_history.csv`: 갱신 이력 누적

## 환율

사용자 지정 고정 환율을 적용합니다.

| 통화 | KRW |
|---|---:|
| USD | 1,460 |
| EUR | 1,720 |
| JPY | 9 |
| CNY | 200 |
| HKD | 190 |
| TWD | 45 |
| SEK | 150 |
| THB | 45 |
| KRW | 1 |

## 주의

무료/지연 시세 기반 참고용 데이터입니다. 투자 판단용 실시간 호가가 아닙니다.
