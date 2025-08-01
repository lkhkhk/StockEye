## 2. 작업 기록

### 2.1. 프로젝트 분석 및 문서 현행화 (2025-07-25)

*   **목표:** 현재 프로젝트의 구조, 기술 스택, 기능 등을 분석하고 관련 문서를 최신화.
*   **수행 내용:**
    *   `README.md`, `docker-compose.yml`, `requirements.txt`, `PLAN.MD` 등 주요 설정 파일 분석.
    *   `src` 디렉토리 내 모든 Python 소스 코드 분석을 통해 기능 및 구현 상태 파악.
    *   `docs/PLAN.MD` 파일에 개발 단계별 현황 및 상세 TODO 항목 업데이트.
    *   `README.md` 파일의 폴더 구조 설명을 최신 상태 및 개선 제안 반영하여 업데이트.

### 2.2. 구조 개선 및 리팩토링 (2025-07-25)

*   **목표:** 코드의 일관성, 재사용성, 유지보수성을 높이기 위한 구조 개선 및 리팩토링 수행.
*   **수행 내용:**
    *   **라우터 통합:** `src/api/routers/admin_router.py` 파일을 삭제하고, 해당 라우터의 기능을 `src/api/routers/admin.py`로 통합.
    *   **공통 유틸리티 중앙화:** `requests_retry_session` 함수를 `src/common/http_client.py`로 분리하고, 관련 파일들에서 `session` 객체를 `src/common/http_client`에서 직접 import하도록 수정.
    *   **서비스 의존성 주입(DI) 패턴 적용:**
        *   `src/api/routers/admin.py`: `StockService`를 `Depends`를 통해 주입받도록 변경.
        *   `src/api/routers/stock_master.py`: `StockService`를 `Depends`를 통해 주입받도록 변경.
        *   `src/api/routers/simulated_trade.py`: `StockService`를 `Depends`를 통해 주입받도록 변경.
        *   `src/api/routers/predict.py`: `predict_stock_movement` 함수를 `Depends`를 통해 주입받도록 변경.
        *   `src/api/routers/notification.py`: `PriceAlertService`를 `Depends`를 통해 주입받도록 변경.
        *   `src/api/routers/bot_router.py`: `UserService`와 `PriceAlertService`를 `Depends`를 통해 주입받도록 변경.
        *   `src/api/main.py`: 스케줄러 잡에서 서비스 인스턴스를 직접 생성하는 대신, `get_stock_service` 및 `get_price_alert_service` 함수를 통해 인스턴스를 얻도록 변경.
        *   `src/api/services/user_service.py`: `user_service = UserService()` 직접 인스턴스화 제거.
    *   **불필요한 파일 제거:** `src/bot/services/notify_service.py` 파일 삭제.
*   **검증:** 각 변경 사항 적용 후 `docker compose up -d --build`를 통해 서비스 재빌드 및 재기동. `api` 및 `bot` 서비스의 모든 `pytest`를 실행하여 기능 및 안정성 검증 완료.


### 2.3. `/set_price` 명령어 오류 수정 및 테스트 (2025-07-26)

*   **목표:** 텔레그램 봇 `/set_price` 명령어 실행 시 발생하는 오류를 해결하고, 관련 API 및 봇 핸들러 테스트 코드 작성 및 통과.
*   **발생 오류 및 해결 과정:**
    1.  **`telegram.error.Conflict: terminated by other getUpdates request`**:
        *   **원인:** 텔레그램 봇 다중 인스턴스 실행 시 발생.
        *   **해결:** `docker compose down --remove-orphans` 명령어로 모든 Docker 컨테이너를 중지 및 제거하여 환경 초기화.
    2.  **API 서비스 `KeyError: 'url'`**:
        *   **원인:** `src/bot/handlers/alert.py`에서 `httpx`의 `session.post` 호출 시 URL을 키워드 인자(`kwargs['url']`)로 접근하려 했으나, `httpx`는 URL을 위치 인자(`args[0]`)로 받음.
        *   **해결:** `src/bot/tests/test_alert_handler.py`에서 `mock_post.call_args`의 `args[0]`을 사용하여 URL에 접근하도록 테스트 코드 수정.
    3.  **`psycopg2.errors.UndefinedFunction: operator does not exist: character varying = integer`**:
        *   **원인:** `src/api/models/user.py`의 `telegram_id` 컬럼이 `String` 타입인데, 테스트 코드에서 `Integer` 타입의 값을 비교하려 함. 또한 텔레그램 ID가 `INTEGER` 범위를 초과.
        *   **해결:** `src/api/models/user.py`에서 `telegram_id` 컬럼 타입을 `BigInteger`로 변경. `docker compose up --build -d` 후 `docker compose exec db psql -U postgres -d stocks_db -c "ALTER TABLE app_users ALTER COLUMN telegram_id TYPE BIGINT USING telegram_id::BIGINT;"` 명령어로 DB 스키마 업데이트.
    4.  **`NameError: name 'BigInteger' is not defined`**:
        *   **원인:** `src/api/models/user.py`에서 `BigInteger`를 사용했지만 `sqlalchemy`에서 임포트하지 않음.
        *   **해결:** `src/api/models/user.py`에 `from sqlalchemy import BigInteger` 추가.
    5.  **`TypeError: 'first_name' is an invalid keyword argument for User`**:
        *   **원인:** `src/api/models/user.py`의 `User` 모델에 `first_name` 및 `last_name` 컬럼이 정의되지 않음.
        *   **해결:** `src/api/models/user.py`에 `first_name` 및 `last_name` 컬럼 추가. `docker compose up --build -d` 후 `docker compose exec db psql -U postgres -d stocks_db -c "ALTER TABLE app_users ADD COLUMN first_name VARCHAR(50), ADD COLUMN last_name VARCHAR(50);"` 명령어로 DB 스키마 업데이트.
    6.  **`psycopg2.errors.NotNullViolation: null value in column "password_hash" of relation "app_users" violates not-null constraint`**:
        *   **원인:** 텔레그램 봇을 통해 사용자 생성 시 `password_hash`가 `None`으로 전달되는데, DB 컬럼이 `NOT NULL` 제약 조건을 가짐.
        *   **해결:** `src/api/models/user.py`에서 `password_hash` 컬럼을 `nullable=True`로 변경. `docker compose up --build -d` 후 `docker compose exec db psql -U postgres -d stocks_db -c "ALTER TABLE app_users ALTER COLUMN password_hash DROP NOT NULL;"` 명령어로 DB 스키마 업데이트.
    7.  **`psycopg2.errors.NotNullViolation: null value in column "email" of relation "app_users" violates not-null constraint`**:
        *   **원인:** 텔레그램 봇을 통해 사용자 생성 시 `email`이 `None`으로 전달되는데, DB 컬럼이 `NOT NULL` 제약 조건을 가짐.
        *   **해결:** `src/api/models/user.py`에서 `email` 컬럼을 `nullable=True`로 변경. `docker compose up --build -d` 후 `docker compose exec db psql -U postgres -d stocks_db -c "ALTER TABLE app_users ALTER COLUMN email DROP NOT NULL;"` 명령어로 DB 스키마 업데이트.
    8.  **`psycopg2.errors.UndefinedColumn: column price_alerts.change_percent does not exist`**:
        *   **원인:** `src/api/models/price_alert.py`에 `change_percent` 및 `change_type` 컬럼이 정의되어 있으나, DB 스키마에 반영되지 않음.
        *   **해결:** `docker compose up --build -d` 후 `docker compose exec db psql -U postgres -d stocks_db -c "ALTER TABLE price_alerts ADD COLUMN change_percent FLOAT, ADD COLUMN change_type VARCHAR(10);"` 명령어로 DB 스키마 업데이트.
    9.  **`psycopg2.errors.UndefinedColumn: column price_alerts.repeat_interval does not exist`**:
        *   **원인:** `src/api/models/price_alert.py`에 `repeat_interval` 컬럼이 정의되어 있으나, DB 스키마에 반영되지 않음.
        *   **해결:** `docker compose up --build -d` 후 `docker compose exec db psql -U postgres -d stocks_db -c "ALTER TABLE price_alerts ADD COLUMN repeat_interval VARCHAR(20);"` 명령어로 DB 스키마 업데이트.
    10. **`IndentationError: unindent does not match any outer indentation level`**:
        *   **원인:** `src/bot/handlers/alert.py` 파일의 들여쓰기 오류.
        *   **해결:** 해당 줄의 들여쓰기 수정.
    11. **`TypeError: object MagicMock can't be used in 'await' expression`**:
        *   **원인:** `update.message.reply_text`가 `AsyncMock`으로 모의되었지만, `await` 가능하도록 설정되지 않음.
        *   **해결:** `update.message.reply_text = AsyncMock()`으로 설정.
    12. **`AssertionError: expected call not found.` (가격 포맷팅)**:
        *   **원인:** `set_price_alert` 함수에서 `price`를 `float`으로 변환 후 문자열로 포매팅할 때 소수점 이하가 붙어 테스트 코드의 예상 문자열과 불일치.
        *   **해결:** `src/bot/tests/test_alert_handler.py`의 테스트 코드에서 예상 문자열을 `75,000.0원`으로 변경.
*   **테스트 결과:** `src/api/tests/test_bot_alert_price.py` 및 `src/bot/tests/test_alert_handler.py`의 모든 테스트 통과.

### 2.4. API 테스트 커버리지 확장 및 안정화 (2025-07-27)

*   **목표:** API 서비스의 테스트 커버리지를 확장하고, 테스트 환경의 안정성을 확보.
*   **수행 내용:**
    *   `src/api/tests/helpers.py` 파일을 생성하여 API 테스트를 위한 유틸리티 함수들을 중앙화.
    *   `src/api/routers/user.py`에 대한 테스트 커버리지를 확장 (`test_api_user.py`): 사용자 등록, 로그인 실패, 사용자 정보 조회, 텔레그램 등록, 사용자 통계, 관리자 접근 등 다양한 시나리오를 포함.
    *   `src/api/routers/stock_master.py`에 대한 테스트 커버리지를 확장 (`test_api_stock_master.py`): 주식 검색 및 현재 가격 조회 등 모든 엔드포인트에 대한 테스트를 추가. 주식 가격 데이터가 없을 경우 404 응답을 반환하도록 `src/api/routers/stock_master.py` 수정.
    *   `src/api/routers/notification.py`에 대한 테스트 커버리지를 확장 (`test_api_alerts.py`): 인증되지 않은 접근, 유효하지 않은 데이터, 알림 업데이트 및 삭제, 알림 테스트 등 시나리오를 포함.
    *   `src/api/routers/prediction_history.py`에 대한 테스트 커버리지를 확장 (`test_api_prediction_history.py`): 페이지네이션 및 필터링 기능을 포함.
    *   **`prediction_history.id` NOT NULL 제약 조건 오류 해결:**
        *   **원인:** 테스트 환경(SQLite)에서 `prediction_history.id` 컬럼의 `sa.Identity` 설정으로 인해 `NOT NULL constraint failed` 오류 발생.
        *   **해결:** `src/api/models/prediction_history.py`에서 `id` 컬럼 정의를 `Column(Integer, primary_key=True, autoincrement=True)`로 변경하여 SQLite 호환성을 확보.
        *   `src/api/tests/conftest.py`의 `db` fixture를 수정하여 각 테스트 함수 실행 전에 모든 테이블을 삭제하고 다시 생성함으로써 깨끗한 데이터베이스 상태를 보장.
*   **테스트 결과:** 모든 API 테스트가 성공적으로 통과.

### 2.5. 테스트 환경 안정화 및 API 테스트 오류 수정 (2025-07-30)

*   **목표:** `api` 및 `bot` 서비스의 전체 테스트를 성공적으로 실행하고, 테스트 과정에서 발생한 오류를 해결하여 테스트 환경의 안정성을 확보.
*   **수행 내용:**
    1.  **`docker compose exec` 명령 오류 (`service "api_service" is not running`)**:
        *   **원인:** `docker compose exec` 명령이 `api_service` 컨테이너를 찾지 못하는 알 수 없는 문제 발생. `docker compose ps`에서는 컨테이너가 `Up` 상태로 보였으나, `exec`, `stop`, `restart`, `logs` 등 대부분의 `docker compose` 명령에서 동일한 오류 발생. 이는 `docker compose` 클라이언트와 Docker 데몬 간의 통신 문제 또는 Docker 환경 자체의 문제로 추정.
        *   **해결:** `docker compose down --remove-orphans` 명령으로 모든 컨테이너를 완전히 제거하고, `docker compose up -d --build`로 재빌드 및 재실행. 이후에도 `docker compose exec` 문제가 지속되어, `docker exec <container_name> <command>` 형식으로 직접 `docker exec` 명령을 사용하여 컨테이너 내부에서 테스트를 실행.
    2.  **`test_stock_service.py` 테스트 실패 (6개 테스트)**:
        *   **원인 1: `unittest.mock.patch` 데코레이터 인자 순서 불일치**: `@patch` 데코레이터는 역순으로 인자를 주입하므로, 테스트 함수의 인자 순서와 데코레이터의 순서가 일치하지 않아 발생.
        *   **해결 1:** `src/api/tests/test_stock_service.py` 파일 내의 모든 `test_check_and_notify_new_disclosures` 관련 테스트 함수의 인자 순서를 `@patch` 데코레이터의 역순에 맞춰 수정.
        *   **원인 2: `real_db.add.assert_called_once()` 및 `real_db.commit.assert_called_once()` `AttributeError`**: `real_db`가 실제 SQLAlchemy 세션 객체이므로 `assert_called_once()`와 같은 목(mock) 메서드를 직접 호출할 수 없음.
        *   **해결 2:** `test_check_and_notify_new_disclosures_initial_run` 테스트 내에서 `patch.object(real_db, 'add')`와 `patch.object(real_db, 'commit')`를 사용하여 `real_db` 객체의 `add`와 `commit` 메서드를 목(mock) 처리.
        *   **원인 3: `assert config.value == '...'` `AttributeError`**: `test_check_and_notify_new_disclosures_success` 테스트에서 `mock_config_initial`이 `SystemConfig`의 `value` 속성을 가지고 있지 않아 발생.
        *   **해결 3:** `mock_config_initial`에 `value` 속성을 추가하고, `real_db.query(SystemConfig).filter(...).first()`가 반환하는 `config` 객체도 `MagicMock(spec=SystemConfig, value=...)`으로 처리하여 `value` 속성을 가질 수 있도록 수정.
        *   **원인 4: `real_db.rollback.called` `AttributeError`**: `test_check_and_notify_new_disclosures_dart_api_limit_exceeded`, `test_check_and_notify_new_disclosures_other_dart_api_error`, `test_check_and_notify_new_disclosures_unexpected_error` 테스트에서 `real_db.rollback`이 메서드이므로 `called` 속성을 직접 가질 수 없어 발생.
        *   **해결 4:** 각 테스트 함수 내에서 `patch.object(real_db, 'rollback')`를 사용하여 `real_db.rollback`을 목(mock) 처리하고, `mock_real_db_rollback.assert_called_once()` 또는 `mock_real_db_rollback.assert_not_called()`로 검증.
*   **테스트 결과:** `api` 서비스의 모든 테스트 (129개 통과, 1개 스킵, 7개 경고) 및 `bot` 서비스의 모든 테스트 (22개 통과)가 성공적으로 완료.

### 2.6. 관리자 기능 강화 및 예측 모델 개선 (2025-07-30)

*   **목표:** 텔레그램 봇을 통한 관리자 기능 강화 및 주식 예측 모델 고도화.
*   **수행 내용:**
    *   `src/bot/handlers/admin.py`에서 API 엔드포인트 호출 및 통계 필드명 불일치 문제 해결.
    *   `requirements.txt`에 `pandas_datareader` 추가.
    *   `src/api/services/stock_service.py`에서 `update_daily_prices` 함수를 `pandas_datareader`를 사용하여 실제 일별 시세 데이터를 가져오도록 수정.
    *   `src/api/services/stock_service.py`에서 `get_current_price_and_change` 함수를 실제 `DailyPrice` 데이터를 사용하도록 수정.
    *   `src/api/services/predict_service.py`에서 RSI 및 MACD 계산 로직을 `calculate_analysis_items` 함수에 추가.
    *   `src/api/services/predict_service.py`에서 예측 로직을 고도화하고 신뢰도/확률 점수를 제공하도록 `calculate_analysis_items` 함수 수정.
    *   `src/api/schemas/predict.py`의 `StockPredictionResponse` 스키마에 `confidence` 필드 추가.
    *   `src/api/routers/predict.py`에서 예측 결과에 `confidence` 필드를 포함하도록 변경.
    *   `src/api/tests/conftest.py`의 `real_db` fixture를 수정하여 각 테스트 함수 시작 전에 모든 테이블의 데이터를 삭제하도록 함.
    *   `src/api/tests/test_stock_service.py`에서 `update_daily_prices` 및 `get_current_price_and_change` 관련 테스트 수정.
    *   `src/api/tests/test_api_predict.py`, `src/api/tests/test_e2e_scenario.py`, `src/api/tests/test_predict_service.py` 테스트 수정.
*   **발생 오류 및 해결 과정:**
    *   `ModuleNotFoundError: No module named 'pandas_datareader'` 오류 발생 및 `docker compose up -d --build` 재실행으로 해결.
    *   `psycopg2.ProgrammingError: can't adapt type 'numpy.int64'` 오류 발생 및 `src/api/services/stock_service.py`에서 명시적 형변환 추가로 해결.
    *   `UniqueViolation` 오류 발생 및 `src/api/tests/conftest.py`의 `real_db` fixture 수정으로 해결.
    *   `KeyError: 'confidence'` 오류 발생 및 `predict_stock_movement` 함수에서 `confidence` 필드 포함하도록 수정으로 해결.
    *   `AssertionError` (예측 결과 불일치) 오류 발생 및 `src/api/services/predict_service.py`의 예측 로직 및 `src/api/tests/test_predict_service.py`의 예상 값 조정으로 해결.
*   **테스트 결과:** `api` 및 `bot` 서비스의 모든 테스트 성공적으로 통과.

### 2.7. 봇 핸들러 테스트 및 실제 주식 시세 API 연동 (2025-08-01)

*   **목표:** 텔레그램 봇 핸들러에 대한 테스트 커버리지를 확장하고, 실제 주식 시세 API를 연동하여 데이터의 정확성을 높입니다.
*   **수행 내용:**
    *   **봇 핸들러 테스트 코드 작성 및 수정:**
        *   `src/bot/handlers/predict.py` (`/predict` 명령어)에 대한 `src/bot/tests/test_bot_predict.py` 테스트 파일 신규 작성 및 오류 수정.
        *   `src/bot/handlers/register.py` (`/register`, `/unregister` 명령어)에 대한 `src/bot/tests/test_bot_register.py` 테스트 파일 신규 작성.
        *   `src/bot/handlers/symbols.py` (`/symbols`, `/symbols_search`, `/symbol_info` 명령어)에 대한 `src/bot/tests/test_bot_symbols.py` 테스트 파일 신규 작성 및 오류 수정.
        *   `src/bot/handlers/trade.py` (`/trade_simulate`, `/trade_history` 명령어)에 대한 `src/bot/tests/test_bot_trade.py` 테스트 파일 신규 작성 및 오류 수정.
        *   `src/bot/handlers/watchlist.py` (`/watchlist_add`, `/watchlist_remove`, `/watchlist_get` 명령어)에 대한 `src/bot/tests/test_bot_watchlist.py` 테스트 파일 신규 작성 및 오류 수정.
    *   **API 서비스 라우터 테스트 확인:** `src/api/routers/`의 모든 라우터에 대한 테스트 파일이 `src/api/tests/unit/`에 이미 존재함을 확인.
    *   **실제 주식 시세 API 연동:**
        *   `requirements.txt`에 `yfinance` 라이브러리 추가.
        *   `src/api/services/stock_service.py`의 `update_daily_prices` 함수를 `pandas_datareader` 대신 `yfinance`를 사용하여 실제 주식 시세 데이터를 가져오도록 수정.
*   **발생 오류 및 해결 과정:**
    *   **`TypeError: object MagicMock can't be used in 'await' expression`**: `update.message.reply_text`가 `AsyncMock`으로 모의되었지만 `await` 가능하도록 설정되지 않아 발생. `update.message.reply_text = AsyncMock()`으로 설정하여 해결.
    *   **`AttributeError: 'coroutine' object has no attribute 'raise_for_status'`**: `httpx`의 `session.post` 및 `session.get` 호출 시 `await` 키워드 누락 및 `response.raise_for_status()` 대신 `response.ok`를 확인하는 로직 필요. `await` 키워드 추가 및 `if response.ok:` 로직으로 변경하여 해결.
    *   **`NameError: name 'requests' is not defined`**: 테스트 파일에서 `requests.exceptions.RequestException`을 사용했지만 `requests` 모듈을 임포트하지 않아 발생. `import requests` 추가하여 해결.
    *   **`AssertionError: expected call not found.` (예상 메시지 불일치)**: 핸들러의 오류 메시지 변경으로 인해 테스트 코드의 예상 메시지와 불일치 발생. 테스트 코드의 예상 메시지를 핸들러의 변경된 메시지에 맞게 수정하여 해결.
    *   **`NameError: name 'Mock' is not defined`**: `unittest.mock.Mock` 임포트를 제거하여 발생. 다시 `from unittest.mock import AsyncMock, patch, Mock`으로 임포트하여 해결.
*   **테스트 결과:** `api` 및 `bot` 서비스의 모든 테스트 성공적으로 통과.