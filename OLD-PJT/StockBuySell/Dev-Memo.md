
stock_prediction_spec.md 파일을 기반으로 주식 예측 봇 개발을 진행했습니다.

현재까지 구현된 주요 내용은 다음과 같습니다.

1.  **FastAPI 기반 예측 서비스 API (`main.py`)**:
    *   종목 예측 (`/predict`) 엔드포인트 (간단한 기술적 분석 룰셋 사용)
    *   관심 종목 추가/조회/제거 (`/watchlist/add`, `/watchlist/get/{user_id}`, `/watchlist/remove`) 엔드포인트
    *   모의 매수/매도 기록 (`/trade/simulate`) 엔드포인트
    *   모의 거래 기록 조회 (`/trade/history/{user_id}`) 엔드포인트
    *   SQLite 데이터베이스를 사용하여 관심 종목 및 모의 거래 데이터 저장

2.  **데이터 수집 모듈 (`data_collector.py`)**:
    *   SQLite 데이터베이스에 일별 주가 데이터를 저장하는 기본 구조 구현
    *   네이버 금융 크롤링 함수 스켈레톤 (현재는 플레이스홀더 데이터 반환)
    *   데이터 수집 실행 함수 (`collect_all_stock_data`)

3.  **예측 로직 모듈 (`prediction_logic.py`)**:
    *   데이터베이스에서 최근 주가 데이터를 가져오는 함수
    *   간단한 기술적 분석 룰셋 (최근 3일 종가 추세) 기반 예측 함수 구현

4.  **텔레그램 챗봇 인터페이스 (`telegram_bot.py`)**:
    *   봇 시작, 도움말 명령어 핸들러 (`/start`, `/help`)
    *   종목 예측 명령어 핸들러 (`/predict`) 및 일반 메시지 처리
    *   관심 종목 관리 명령어 핸들러 (`/watchlist_add`, `/watchlist_remove`, `/watchlist_get`)
    *   모의 거래 기록 및 조회 명령어 핸들러 (`/trade_simulate`, `/trade_history`)
    *   FastAPI 백엔드와 연동하여 데이터 요청 및 결과 응답

**향후 개발 필요 사항 (TODO)**:

*   `data_collector.py`에 실제 네이버 금융 데이터 크롤링 로직 구현 및 크론 스케줄러 연동
*   `prediction_logic.py`에 더 정교한 기술적 지표 및 뉴스 분석 기반 예측 로직 추가
*   종목 추천 기능 구현
*   모의 매매 수익률 계산 로직 구현
*   예측 정확도 추적 및 모델 개선 루프 적용

현재까지 개발된 코드는 명세서의 MVP 요구사항과 사용자 기능 대부분을 포함하고 있습니다.

프로젝트 실행을 위해 다음 단계를 수행할 수 있습니다:
1.  필요한 Python 패키지 설치: `pip install fastapi uvicorn python-telegram-bot requests beautifulsoup4 pandas`
# 2.  FastAPI 서버 실행: `uvicorn vibe-coding.StockBuySell.main:app --reload`
2.  FastAPI 서버 실행: `uvicorn main:app --reload`
# 3.  데이터 수집기 실행 (최초 1회 또는 주기적으로): `python vibe-coding/StockBuySell/data_collector.py` (실제 크롤링 로직 구현 후)
3.  데이터 수집기 실행 (최초 1회 또는 주기적으로): `python3 data_collector.py` (실제 크롤링 로직 구현 후)
# 4.  텔레그램 봇 실행: `python vibe-coding/StockBuySell/telegram_bot.py` (텔레그램 봇 토큰 설정 후)
4.  텔레그램 봇 실행: `python3 telegram_bot.py` (텔레그램 봇 토큰 설정 후)

텔레그램 봇 토큰은 `telegram_bot.py` 파일 내 `TELEGRAM_BOT_TOKEN` 변수에 설정해야 합니다.