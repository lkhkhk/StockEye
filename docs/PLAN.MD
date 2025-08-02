# StocksEye 개발 계획 및 현황

## 🎯 Phase 1: 코어 인프라 구축 (완료)

-   [x] **프로젝트 초기 설정**
    -   [x] Docker 기반 서비스 환경 구성 (api, bot, db)
    -   [x] FastAPI 및 Telegram Bot 프레임워크 연동
    -   [x] PostgreSQL 연동 및 SQLAlchemy ORM 설정
    -   [x] `settings.env`를 통한 환경 변수 관리
    -   [x] `pytest` 기반 테스트 환경 구축 (in-memory DB 활용)
-   [x] **중앙 로깅 시스템 구축**
    -   [x] `api`, `bot` 서비스 로그를 `/logs` 볼륨에 파일로 기록
    -   [x] 표준 시간, 로그 레벨 등 일관된 포맷 적용
-   [x] **백그라운드 스케줄러(APScheduler) 연동**
    -   [x] `api` 서비스 시작 시 스케줄러 자동 실행
    -   [x] 스케줄러 상태 및 잡 목록 조회 API 구현

## 🚀 Phase 2: 핵심 기능 구현 (완료)

-   [x] **사용자 인증 시스템 (JWT 기반)**
    -   [x] 회원가입, 로그인, 로그아웃 API
    -   [x] 토큰 기반 사용자 인증 및 정보 조회
    -   [x] 사용자 정보 조회/업데이트, 텔레그램 등록, 사용자 통계, 모든 사용자 조회 테스트 커버리지 개선 (`src/api/routers/user.py` 테스트 커버리지 개선)
-   [x] **주식 정보 관리**
    -   [x] **종목 마스터**: DART API 연동을 통한 전체 종목 정보 일괄 갱신 (매일 오전 7시)
    -   [x] **일별 시세**: 전체 종목의 일별 시세 데이터 생성 및 갱신 (매일 오후 6시, 현재는 임시 데이터)
    -   [x] **공시 정보**: DART API 연동을 통한 최신 공시 정보 주기적 확인 (매 4시간, API 호출 최적화)
    -   [x] **종목 마스터 및 현재가 조회 테스트 커버리지 개선**: `src/api/routers/stock_master.py` 테스트 커버리지 개선
-   [x] **텔레그램 봇 기본 기능**
    -   [x] `/start`, `/help` 등 기본 명령어 핸들러
    -   [x] 종목 코드/이름 기반 검색 및 상세 정보 조회
    -   [x] 자연어(일상 대화) 기반 종목 검색 및 예측 요청 처리
-   [x] **관심 종목 (Watchlist)**
    -   [x] 관심 종목 추가, 조회, 삭제 기능 (API 및 봇 명령어)
    -   [x] 관심 종목 추가/조회/삭제 테스트 커버리지 개선 (`src/api/routers/watchlist.py` 테스트 커버리지 개선)
-   [x] **주가 예측**
    -   [x] 이동평균선(SMA) 기반 기본 예측 모델 구현
    -   [x] 사용자별 예측 이력 조회 기능 (API 및 봇 명령어)
-   [x] **모의 거래 (Simulated Trading)**
    -   [x] 매수/매도 기록 및 이력 조회 기능 (API 및 봇 명령어)
    -   [x] 거래 내역 기반 수익률, 승률 등 기본 통계 제공 (`src/api/routers/simulated_trade.py` 테스트 커버리지 개선)

## ✨ Phase 3: 기능 고도화 및 UX 개선 (진행 중)

-   [x] **실시간 공시 알림**
    -   [x] `SystemConfig`를 이용해 마지막 확인 공시 추적
    -   [x] 신규 공시 발생 시 구독자에게 텔레그램 알림 발송
    -   [x] DART API 사용량 초과 등 예외 처리 강화
    -   [x] DART API 호출 횟수 최적화 (전체 공시 갱신 시 단일 API 호출로 변경)
-   [x] **가격 알림 (Price Alert) 기능 고도화**
    -   [x] 알림 조건 다양화: 목표가(이상/이하), 전일 대비 변동률(상승/하락)
    -   [x] 통합 알림 설정: 단일 `PriceAlert` 모델에서 가격, 변동률, 공시 알림 여부 동시 관리
    -   [x] 반복 알림: 알림 발생 후에도 비활성화되지 않고 계속 알림을 받는 옵션 추가 (매일, 매주 등)
    -   [x] 알림 메시지 개선: 현재가, 등락률 등 상세 정보 포함
    -   [x] 텔레그램 봇 `/set_price` 명령어 오류 수정 및 기능 개선
-   [x] **관리자 기능 강화**
    -   [x] 통계 조회, 스케줄러 잡 제어, 데이터 수동 갱신 등 봇 명령어로 제어
    -   [x] 장시간 소요 작업(일괄 갱신 등)에 대한 비동기 처리 및 결과 알림
    -   [x] 관리자 명령어 핸들러에 `@admin_only` 데코레이터를 적용하여 권한 확인 로직 중복 제거
    -   [x] 전체 공시 갱신 로직을 단일 API 호출로 개선하여 효율성 및 안정성 확보
-   [x] **외부 API 연동 안정성 강화**
    -   [x] `requests` 사용 시 `timeout` 및 `retries` 로직 추가 (DART API, 봇 핸들러)
    -   [x] **(TODO)** 실제 주식 시세 API 연동 (현재 임시 데이터 -> 실 데이터)
-   [x] **(TODO) 예측 모델 개선**
    -   [x] 더 다양한 기술적 지표(RSI, MACD 등)를 사용한 예측 로직 고도화
    -   [x] 예측 결과에 대한 신뢰도 또는 확률 점수 제공 (`src/api/routers/predict.py` 테스트 커버리지 개선)

## 🔧 Phase 4: 리팩토링 및 안정화 (향후 계획)

-   [x] **개발/운영 모드 구분 추가**: `APP_ENV` 환경 변수 도입 및 환경별 `.env` 파일, 동적 로깅 설정 적용
-   [x] **코드 리팩토링**
    -   [x] API 라우터 구조 개선 (e.g., `admin` 라우터 통합)
    -   [x] 중복 코드 제거 (e.g., `requests_retry_session` 공통화 -> `http_client.py`로 분리)
    -   [x] API 서비스 로직에 대한 의존성 주입(DI) 패턴 전면 적용
    -   [x] 불필요한 파일 제거 (e.g., `src/bot/services/notify_service.py`)
    -   [x] `telegram_id` 등 DB 스키마 타입 불일치 문제 해결 및 `User` 모델 필드 확장
-   [x] **테스트 커버리지 확대**
    -   [x] `bot` 핸들러에 대한 단위/통합 테스트 코드 보강 (`/set_price` 명령어 테스트 추가)
    -   [x] **테스트 환경 안정화**: `test_toggle_disclosure_alert_existing_alert_on_to_off` 테스트 실패 문제 해결 (서비스 의존성 모의를 통한 테스트 격리 확보)
    -   [x] **봇 서비스 테스트 안정화**: `bot` 핸들러의 비동기 함수 호출 시 `await` 키워드 누락 문제 해결 (`src/bot/tests/test_bot_natural.py` 테스트 통과)
    -   [x] **테스트 파일 구조 개선**: `test_bot_alert_price.py`를 `test_api_alerts_price.py`로 이름 변경, `src/common` 모듈 테스트를 `src/common/tests`로 이동, `test_e2e_scenario.py`를 `src/api/tests/e2e`로 이동 및 `pytest.ini` 업데이트
    -   [x] **API 단위 테스트 폴더 분리**: `src/api/tests` 내의 단위 테스트 파일들을 `src/api/tests/unit`으로 이동 및 `pytest.ini` 업데이트
-   [x] **`GEMINI.md` 지침 업데이트**: `replace` 도구 사용 지침 및 `docker compose exec` 문제 해결 지침 보강
-   [x] **`api` 서비스 `bot_router` 엔드포인트 구현 및 테스트**: `alert/list`, `alert/remove`, `alert/deactivate` 엔드포인트 구현 및 테스트 완료
-   [x] **(TODO)** `api` 서비스의 모든 라우터에 대한 테스트 코드 작성
    -   [x] **(TODO)** `bot` 서비스의 모든 핸들러에 대한 테스트 코드 작성
    -   [x] **`common` 모듈에 대한 단위 테스트 코드 작성**
    -   [x] `src/common/db_connector.py` 테스트 커버리지 개선
    -   [x] `src/common/notify_service.py` 테스트 커버리지 개선
-   [x] **스케줄러 잡 DB 세션 관리 개선**: `src/api/main.py` 내 스케줄러 잡에서 `get_db()` 사용 방식 (`db = next(db_gen)`)을 올바른 세션 관리 방식으로 변경 (`db = get_db()` 및 `db.close()`).
    -   [ ] GitHub Actions 연동
    -   [ ] `main` 브랜치 push 시 자동 테스트 및 Docker 이미지 빌드/배포
-   [ ] **(TODO) 성능 튜닝 및 최적화**
    -   [ ] DB 쿼리 최적화 (인덱스 추가, `selectinload` 등 사용)
    -   [ ] 대량 데이터 처리 로직(일괄 갱신 등) 성능 개선
-   [x] **텔레그램 봇 `/symbols` 명령어 오류 해결**: `/symbols` 명령어 실행 시 "[종목 목록 조회 실패: 알 수 없는 오류가 발생했습니다.]" 응답이 발생하는 문제 해결. (페이지네이션 및 `market` 정보 표시 개선 포함)
-   [ ] **봇 테스트 리팩토링**: 기능별 단위 테스트 및 통합 테스트 분리


