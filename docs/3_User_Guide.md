# 사용자 가이드

이 문서는 StockEye 텔레그램 봇의 사용 방법을 안내합니다.

## 1. 시작하기

텔레그램에서 StockEye 봇을 찾아 대화를 시작하고 `/start` 명령어를 입력하면 봇 사용을 시작할 수 있습니다.

## 2. 주요 명령어

| 명령어 | 기능 | 사용 예시 |
| :--- | :--- | :--- |
| `/start` | 봇 시작 및 환영 메시지, 명령어 안내 표시 | `/start` |
| `/help` | 모든 명령어 목록과 사용법 안내 | `/help` |
| `/register` | StockEye 서비스에 사용자를 등록합니다. | `/register` |
| `/unregister` | StockEye 서비스에서 사용자를 탈퇴합니다. | `/unregister` |
| `/symbols` | 등록된 전체 주식 종목 목록을 조회합니다. | `/symbols` |
| `/symbols_search` | 키워드로 주식 종목을 검색합니다. | `/symbols_search 삼성` |
| `/symbol_info` | 특정 종목의 상세 정보를 조회합니다. | `/symbol_info 005930` |
| `/predict` | 특정 종목의 주가 등락을 예측합니다. | `/predict 005930` |
| `/watchlist_add` | 관심 종목을 추가합니다. | `/watchlist_add 005930` |
| `/watchlist_remove` | 관심 종목을 삭제합니다. | `/watchlist_remove 005930` |
| `/watchlist_get` | 나의 관심 종목 목록을 확인합니다. | `/watchlist_get` |
| `/set_price` | 특정 종목에 대한 가격 알림을 설정합니다. | `/set_price 005930 80000 gte` (8만원 이상 시 알림) |
| `/trade_simulate` | 모의 거래를 기록합니다. | `/trade_simulate buy 005930 10 75000` (10주를 75000원에 매수) |
| `/trade_history` | 나의 모의 거래 내역을 확인합니다. | `/trade_history` |

## 3. 자연어 사용법

딱딱한 명령어가 아니더라도, 일상적인 대화로 봇의 기능을 사용할 수 있습니다.

- **현재가 조회:** "삼성전자 얼마야?", "005930 현재가 알려줘"
- **예측 요청:** "카카오 주가 예측해줘", "035720 오를까?"
