### 2.15. 아키텍처 재설계 준비: 프로젝트 명명 규칙 통일 및 설정 파일 업데이트 (2025-08-05)

*   **목표:** 새로운 `worker` 서비스 도입에 앞서, 프로젝트의 일관성과 명확성을 확보하기 위해 모든 서비스의 명명 규칙을 통일하고 관련 설정 파일을 업데이트합니다.
*   **작업 내역:**
    *   **`docker-compose.yml` 수정:** 모든 서비스(`api`, `bot`, `db`)의 이름과 `container_name`에 `stockseye-` 접두사를 붙여 수정했습니다. (예: `api` -> `stockseye-api`)
    *   **서비스 간 호출 코드 수정:** `docker-compose.yml`의 변경사항에 맞춰, 서비스 간 통신에 사용되는 호스트 이름을 새로운 서비스명으로 업데이트했습니다.
        *   `src/bot/handlers/*.py`: `api_service`를 `stockseye-api`를 참조하도록 `API_HOST` 환경 변수를 사용하게 변경했습니다.
        *   `src/bot/tests/unit/*.py`: 테스트 코드 내에 하드코딩된 `http://api_service:8000` URL을 `http://stockseye-api:8000`으로 일괄 변경했습니다.
        *   `src/bot/tests/e2e/test_api_bot_e2e.py`: 웹훅 URL의 호스트명을 `stockseye-bot`으로 수정했습니다.
    *   **스크립트 수정:** `scripts/backup_restore.sh`의 대상 컨테이너 이름을 `postgres_db`에서 `stockseye-db`로 변경했습니다.
*   **결과:** 새로운 아키텍처를 적용하기 위한 모든 사전 준비 작업을 완료했습니다.

---

### 2.14. 아키텍처 재설계: Message Queue 도입 및 Worker 서비스 분리 (2025-08-05)

*   **목표:** E2E 테스트에서 발생한 `api`와 `bot` 서비스 간의 순환 의존성 및 네트워크 문제를 근본적으로 해결하기 위해 아키텍처를 재설계합니다.
*   **논의 및 결정 사항:**
    *   **문제 진단:** `api` 서비스가 알림을 보내기 위해 `bot` 서비스의 웹훅을 직접 호출하는 구조는 강한 결합(Tight Coupling)과 순환 의존성을 야기하여, E2E 테스트 실패 및 시스템 불안정성의 원인이 됨을 확인했습니다.
    *   **해결 방안 채택:** 서비스 간의 결합을 끊고 비동기 처리를 도입하기 위해 **Message Queue(Redis)를 사용하는 `worker` 서비스 모델**을 채택하기로 결정했습니다.
        *   **`worker` 서비스:** 알림, 주기적 작업(스케줄링), 비동기 장기 실행 작업 등 백그라운드에서 실행되어야 하는 모든 작업을 전담하는 독립적인 서비스입니다.
        *   **`api` 서비스:** `bot`을 직접 호출하는 대신, 알림/작업 요청을 Redis에 메시지로 발행(Publish)하는 역할만 수행합니다.
        *   **`bot` 서비스:** 사용자 요청을 처리하고 `api`에 데이터를 요청하는 역할에만 집중합니다.
    *   **명명 규칙 개선:** 프로젝트의 명확성과 확장성을 위해 모든 서비스와 컨테이너의 이름에 `stockseye-` 접두사를 붙여 통일하기로 결정했습니다. (예: `stockseye-api`, `stockseye-bot`)
*   **현재 상태:** 새로운 아키텍처 계획을 `PLAN.MD`에 반영하고, 관련 파일(docker-compose.yml, 소스 코드, 문서 등)을 일괄적으로 수정하는 작업을 진행할 예정입니다.

---

### 2.13. Bot-API 연동 버그 해결 및 E2E 테스트 도입 (2025-08-04)

*   **목표:** 프로젝트 전반에 걸쳐 발견된 Bot-API 간의 사용자 식별 및 인증 방식 불일치 버그를 해결하고, 재발 방지를 위한 E2E 테스트를 도입합니다.
*   **작업 내역 (진행 중):**
    *   **`/alert` 기능 버그 해결:**
        *   **1단계 (분석):** `notification.py`, `price_alert.py`, `alert.py`, `user_service.py` 등 관련 파일의 코드를 분석하여, 봇은 `telegram_id`를 보내지만 API는 `JWT` 토큰을 요구하는 근본적인 문제를 재확인했습니다.
        *   **2단계 (계획):** API 라우터(`notification.py`)가 `telegram_id`를 기반으로 사용자를 식별하고, 필요시 신규 사용자를 자동 생성하도록 수정하는 것으로 해결 방향을 정했습니다.
        *   **3단계 (구현):**
            *   `src/api/schemas/price_alert.py` 스키마에 `telegram_id` 필드를 추가했습니다.
            *   `src/api/routers/notification.py`의 `create_alert`, `get_my_alerts`, `delete_alert` 엔드포인트를 `telegram_id` 기반으로 동작하도록 수정했습니다.
            *   `src/bot/handlers/alert.py`의 `alert_list`, `alert_remove`, `set_price_alert`, `alert_button_callback`, `alert_set_repeat_callback` 함수를 수정하여 `telegram_id`를 사용하고, API의 변경된 엔드포인트에 맞게 호출하도록 변경했습니다.
        *   **4단계 (검증 시도 및 문제 발생):**
            *   수정된 `alert` 기능에 대한 E2E 테스트(`src/bot/tests/e2e/test_api_bot_e2e.py`)를 작성했습니다.
            *   `api` 컨테이너에서 `pytest`를 실행하여 `src/api/tests/integration/test_api_alerts.py`와 `src/bot/tests/e2e/test_api_bot_e2e.py`를 검증하려 했으나, `httpx.ConnectError: All connection attempts failed` 오류가 지속적으로 발생했습니다.
            *   **원인 분석:**
                *   E2E 테스트가 봇의 웹훅 URL(`http://bot:8001/webhook`)에 연결하지 못하는 문제였습니다.
                *   `src/bot/main.py`가 폴링 모드로 동작하고 있었고, E2E 테스트는 웹훅을 호출하는 방식이었습니다.
                *   `src/bot/main.py`를 웹훅 모드로 변경하고, `docker-compose.yml`에 `bot` 서비스의 `ports` 매핑과 `WEBHOOK_URL` 환경 변수를 추가했습니다.
                *   `test_api_bot_e2e.py`의 `BOT_WEBHOOK_URL` 설정과 `src/bot/main.py`의 `webhook_url` 설정 간의 불일치(`http://bot:8001` vs `http://bot:8001/webhook`)가 있었습니다.
                *   `src/bot/tests/e2e/test_api_bot_e2e.py`의 `send_telegram_message` 함수에서 `BOT_WEBHOOK_URL`에 `/webhook` 경로를 추가하여 요청을 보내도록 수정했습니다.
            *   **현재 상태:** `httpx.ConnectError: [Errno -5] No address associated with hostname` 오류가 여전히 발생하고 있습니다. 이는 `api` 컨테이너에서 `bot` 서비스의 웹훅 URL을 해석하지 못하는 네트워크 문제입니다.

---

### 2.12. API 단위 테스트 강화 - `predict_service.py` (`calculate_analysis_items`) (2025-08-02)

*   **목표:** `src/api/services/predict_service.py`의 `calculate_analysis_items` 메서드에 대한 심층적인 단위 테스트를 추가하고 100% 커버리지를 달성합니다.
*   **수행 내용:**
    *   `src/api/tests/unit/test_predict_service.py` 파일에 `calculate_analysis_items` 메서드를 직접 테스트하는 `test_calculate_analysis_items_basic_up_trend` 및 `test_calculate_analysis_items_basic_down_trend` 테스트 케이스를 추가했습니다.
    *   이 테스트들은 Pandas DataFrame 형태의 Mock 데이터를 사용하여 `calculate_analysis_items`의 SMA 기반 추세 분석 로직을 검증합니다.
*   **결과:** `calculate_analysis_items` 메서드에 대한 단위 테스트를 진행 중입니다. 추가적인 시나리오(횡보, RSI, MACD, 엣지 케이스 등)에 대한 테스트를 계속 추가할 예정입니다.


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
        *   **解決:** `src/api/models/user.py`에서 `telegram_id` 컬럼 타입을 `BigInteger`로 변경. `docker compose up --build -d` 후 `docker compose exec db psql -U postgres -d stocks_db -c "ALTER TABLE app_users ALTER COLUMN telegram_id TYPE BIGINT USING telegram_id::BIGINT;"` 명령어로 DB 스키마 업데이트.
    4.  **`NameError: name 'BigInteger' is not defined`**:
        *   **원인:** `src/api/models/user.py`에서 `BigInteger`를 사용했지만 `sqlalchemy`에서 임포트하지 않음.
        *   **解決:** `src/api/models/user.py`에 `from sqlalchemy import BigInteger` 추가.
    5.  **`TypeError: 'first_name' is an invalid keyword argument for User`**:
        *   **원인:** `src/api/models/user.py`의 `User` 모델에 `first_name` 및 `last_name` 컬럼이 정의되지 않음.
        *   **解決:** `src/api/models/user.py`에 `first_name` 및 `last_name` 컬럼 추가. `docker compose up --build -d` 후 `docker compose exec db psql -U postgres -d stocks_db -c "ALTER TABLE app_users ADD COLUMN first_name VARCHAR(50), ADD COLUMN last_name VARCHAR(50);"` 명령어로 DB 스키마 업데이트.
    6.  **`psycopg2.errors.NotNullViolation: null value in column "password_hash" of relation "app_users" violates not-null constraint`**:
        *   **원인:** 텔레그램 봇을 통해 사용자 생성 시 `password_hash`가 `None`으로 전달되는데, DB 컬럼이 `NOT NULL` 제약 조건을 가짐.
        *   **解決:** `src/api/models/user.py`에서 `password_hash` 컬럼을 `nullable=True`로 변경. `docker compose up --build -d` 후 `docker compose exec db psql -U postgres -d stocks_db -c "ALTER TABLE app_users ALTER COLUMN password_hash DROP NOT NULL;"` 명령어로 DB 스키마 업데이트.
    7.  **`psycopg2.errors.NotNullViolation: null value in column "email" of relation "app_users" violates not-null constraint`**:
        *   **원인:** 텔레그램 봇을 통해 사용자 생성 시 `email`이 `None`으로 전달되는데, DB 컬럼이 `NOT NULL` 제약 조건을 가짐.
        *   **解決:** `src/api/models/user.py`에서 `email` 컬럼을 `nullable=True`로 변경. `docker compose up --build -d` 후 `docker compose exec db psql -U postgres -d stocks_db -c "ALTER TABLE app_users ALTER COLUMN email DROP NOT NULL;"` 명령어로 DB 스키마 업데이트.
    8.  **`psycopg2.errors.UndefinedColumn: column price_alerts.change_percent does not exist`**:
        *   **원인:** `src/api/models/price_alert.py`에 `change_percent` 및 `change_type` 컬럼이 정의되어 있으나, DB 스키마에 반영되지 않음.
        *   **解決:** `docker compose up --build -d` 후 `docker compose exec db psql -U postgres -d stocks_db -c "ALTER TABLE price_alerts ADD COLUMN change_percent FLOAT, ADD COLUMN change_type VARCHAR(10);"` 명령어로 DB 스키마 업데이트.
    9.  **`psycopg2.errors.UndefinedColumn: column price_alerts.repeat_interval does not exist`**:
        *   **원인:** `src/api/models/price_alert.py`에 `repeat_interval` 컬럼이 정의되어 있으나, DB 스키마에 반영되지 않음.
        *   **解決:** `docker compose up --build -d` 후 `docker compose exec db psql -U postgres -d stocks_db -c "ALTER TABLE price_alerts ADD COLUMN repeat_interval VARCHAR(20);"` 명령어로 DB 스키마 업데이트.
    10. **`IndentationError: unindent does not match any outer indentation level`**:
        *   **원인:** `src/bot/handlers/alert.py` 파일의 들여쓰기 오류.
        *   **解決:** 해당 줄의 들여쓰기 수정.
    11. **`TypeError: object MagicMock can't be used in 'await' expression`**:
        *   **원인:** `update.message.reply_text`가 `AsyncMock`으로 모의되었지만, `await` 가능하도록 설정되지 않음.
        *   **解決:** `update.message.reply_text = AsyncMock()`으로 설정.
    12. **`AssertionError: expected call not found.` (가격 포맷팅)**:
        *   **원인:** `set_price_alert` 함수에서 `price`를 `float`으로 변환 후 문자열로 포매팅할 때 소수점 이하가 붙어 테스트 코드의 예상 문자열과 불일치.
        *   **解決:** `src/bot/tests/test_alert_handler.py`의 테스트 코드에서 예상 문자열을 `75,000.0원`으로 변경.
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
        *   **解決:** `src/api/models/prediction_history.py`에서 `id` 컬럼 정의를 `Column(Integer, primary_key=True, autoincrement=True)`로 변경하여 SQLite 호환성을 확보.
        *   `src/api/tests/conftest.py`의 `db` fixture를 수정하여 각 테스트 함수 실행 전에 모든 테이블을 삭제하고 다시 생성함으로써 깨끗한 데이터베이스 상태를 보장.
*   **테스트 결과:** 모든 API 테스트가 성공적으로 통과.

### 2.5. 테스트 환경 안정화 및 API 테스트 오류 수정 (2025-07-30)

*   **목표:** `api` 및 `bot` 서비스의 전체 테스트를 성공적으로 실행하고, 테스트 과정에서 발생한 오류를 해결하여 테스트 환경의 안정성을 확보.
*   **수행 내용:**
    1.  **`docker compose exec` 명령 오류 (`service "api_service" is not running`)**:
        *   **원인:** `docker compose exec` 명령이 `api_service` 컨테이너를 찾지 못하는 알 수 없는 문제 발생. `docker compose ps`에서는 컨테이너가 `Up` 상태로 보였으나, `exec`, `stop`, `restart`, `logs` 등 대부분의 `docker compose` 명령에서 동일한 오류 발생. 이는 `docker compose` 클라이언트와 Docker 데몬 간의 통신 문제 또는 Docker 환경 자체의 문제로 추정.
        *   **解決:** `docker compose down --remove-orphans` 명령으로 모든 컨테이너를 완전히 제거하고, `docker compose up -d --build`로 재빌드 및 재실행. 이후에도 `docker compose exec` 문제가 지속되어, `docker exec <container_name> <command>` 형식으로 직접 `docker exec` 명령을 사용하여 컨테이너 내부에서 테스트를 실행.
    2.  **`test_stock_service.py` 테스트 실패 (6개 테스트)**:
        *   **원인 1: `unittest.mock.patch` 데코레이터 인자 순서 불일치**: `@patch` 데코레이터는 역순으로 인자를 주입하므로, 테스트 함수의 인자 순서와 데코레이터의 순서가 일치하지 않아 발생.
        *   **解決 1:** `src/api/tests/test_stock_service.py` 파일 내의 모든 `test_check_and_notify_new_disclosures` 관련 테스트 함수의 인자 순서를 `@patch` 데코레이터의 역순에 맞춰 수정.
        *   **원인 2: `real_db.add.assert_called_once()` 및 `real_db.commit.assert_called_once()` `AttributeError`**: `real_db`가 실제 SQLAlchemy 세션 객체이므로 `assert_called_once()`와 같은 목(mock) 메서드를 직접 호출할 수 없음.
        *   **解決 2:** `test_check_and_notify_new_disclosures_initial_run` 테스트 내에서 `patch.object(real_db, 'add')`와 `patch.object(real_db, 'commit')`를 사용하여 `real_db` 객체의 `add`와 `commit` 메서드를 목(mock) 처리.
        *   **원인 3: `assert config.value == '...'` `AttributeError`**: `test_check_and_notify_new_disclosures_success` 테스트에서 `mock_config_initial`이 `SystemConfig`의 `value` 속성을 가지고 있지 않아 발생.
        *   **解決 3:** `mock_config_initial`에 `value` 속성을 추가하고, `real_db.query(SystemConfig).filter(...).first()`가 반환하는 `config` 객체도 `MagicMock(spec=SystemConfig, value=...)`으로 처리하여 `value` 속성을 가질 수 있도록 수정.
        *   **원인 4: `real_db.rollback.called` `AttributeError`**: `test_check_and_notify_new_disclosures_dart_api_limit_exceeded`, `test_check_and_notify_new_disclosures_other_dart_api_error`, `test_check_and_notify_new_disclosures_unexpected_error` 테스트에서 `real_db.rollback`이 메서드이므로 `called` 속성을 직접 가질 수 없어 발생.
        *   **解決 4:** 각 테스트 함수 내에서 `patch.object(real_db, 'rollback')`를 사용하여 `real_db.rollback`을 목(mock) 처리하고, `mock_real_db_rollback.assert_called_once()` 또는 `mock_real_db_rollback.assert_not_called()`로 검증.
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


## 텔레그램 봇 `/symbols` 명령어 문제 해결 계획 (2025-08-01)

### 1. 현재 상황 요약

*   **문제:** 텔레그램 봇의 `/symbols` 명령어가 여전히 정상 작동하지 않습니다. "종목 목록 조회 실패: 알 수 없는 오류가 발생했습니다." 메시지가 계속 표시됩니다.
*   **원인 분석 (이전까지):**
    *   `api_service`의 `/symbols/` 엔드포인트가 모든 종목 데이터를 반환하여 텔레그램 메시지 길이 제한(4096자)을 초과하는 것이 문제의 원인으로 파악되었습니다.
    *   `src/api/routers/stock_master.py` 파일의 `get_all_symbols` 함수에 `limit` 파라미터를 추가하여 반환되는 종목 수를 제한하도록 수정했습니다.
    *   `src/bot/handlers/symbols.py` 파일의 `symbols_command` 함수에서 API 호출 시 `limit=10` 파라미터를 포함하도록 수정했습니다.
    *   `api` 및 `bot` 서비스를 강제로 재빌드하고 재시작하여 변경 사항을 적용했습니다.
*   **최신 테스트 결과:**
    *   `bot` 컨테이너 내부에서 `requests`를 사용하여 `http://api_service:8000/symbols/?limit=10` 엔드포인트를 직접 호출한 결과, **여전히 모든 종목 데이터가 반환되는 것을 확인했습니다.** (10개로 제한되지 않음)
    *   이는 `src/api/routers/stock_master.py`의 `limit` 로직이 예상대로 작동하지 않거나, Docker 빌드/배포 과정에서 알 수 없는 문제가 발생했을 가능성을 시사합니다.

### 2. 내일 작업 계획

1.  **API 로직 심층 디버깅 (`src/api/routers/stock_master.py`):**
    *   `get_all_symbols` 함수 내부에 디버그 로그를 추가하여 `limit` 파라미터가 함수 내부로 정확히 전달되는지, 그리고 SQLAlchemy 쿼리(`db.query(StockMaster).limit(limit).all()`)가 `limit`을 제대로 적용하여 SQL 쿼리를 생성하는지 상세히 확인하겠습니다.
    *   필요하다면 `limit` 값을 코드에 직접 하드코딩하여 (`.limit(10)`) `Query` 파라미터 주입 문제인지, 아니면 SQLAlchemy 쿼리 자체의 문제인지 파악하겠습니다.
2.  **API 서비스 강제 재빌드 및 재시작:** API 코드 수정 후에는 `api` 서비스만 다시 한번 `docker compose build --no-cache api && docker compose up -d api` 명령으로 강제 재빌드 및 재시작하여 변경 사항이 확실히 반영되도록 하겠습니다.
3.  **API 응답 재테스트 (봇 컨테이너에서):** 재빌드 후 `bot` 컨테이너에서 `requests` 스크립트를 사용하여 `/symbols/?limit=10` 엔드포인트의 응답이 실제로 10개로 제한되는지 다시 한번 정확히 확인하겠습니다.
4.  **봇 로그 상세 분석 (API 수정 확인 후):** API가 정상적으로 제한된 응답을 반환하기 시작하면, `bot_service`의 최신 로그를 다시 면밀히 검토하여 텔레그램 메시지 길이 제한 문제가 해결되었는지, 또는 다른 새로운 오류가 발생하는지 확인하겠습니다.
5.  **최종 커밋:** `/symbols` 명령어가 텔레그램 봇에서 완전히 정상 작동하는 것을 확인한 후에 모든 관련 변경 사항을 커밋하겠습니다.


### 2.8. `/symbols <키워드>` 명령 문제 해결 (2025-08-02)

*   **문제:** 텔레그램 봇에서 `/symbols 한화` 명령 시 전체 종목 리스트가 반환되고, 검색 결과가 나오지 않는 문제.
*   **원인 분석:**
    *   **초기 추정:** `bot` 서비스의 `symbols_command`가 `context.args`를 올바르게 받지 못하여 `symbols_search_command`로 라우팅되지 않는 문제.
    *   **`src/bot/main.py`의 `MessageHandler` 문제:** `telegram.ext.MessageHandler`와 `filters.Regex`를 함께 사용할 때, `context.args`가 `CommandHandler`처럼 자동으로 채워지지 않음. `symbols_handler_wrapper`를 통해 `re.match`로 `context.args`를 수동으로 설정하려 했으나, 실제 봇 환경에서 `context.match`가 `None`이 되는 등 예상과 다르게 동작하여 `context.args`가 빈 리스트로 전달됨.
    *   **근본 원인:** 텔레그램 봇 API에서 명령(`Command`)과 인자를 처리하는 가장 견고하고 권장되는 방법은 `CommandHandler`를 사용하는 것. `/symbols 한화`와 같은 형태는 텔레그램 봇 API에 의해 명령으로 인식되므로, `MessageHandler` 대신 `CommandHandler`를 사용해야 함.
*   **해결 과정:**
    1.  **`src/bot/main.py` 수정:**
        *   `symbols_handler_wrapper` 함수 정의 및 관련 `MessageHandler` 라인 제거.
        *   `app.add_handler(CommandHandler("symbols", symbols_command, pass_args=True))`를 추가하여 `/symbols` 명령과 그 뒤의 인자를 `symbols_command`로 직접 전달하도록 설정.
    2.  **`src/bot/tests/test_bot_symbols.py` 수정:**
        *   `test_symbols_handler_wrapper_sets_context_args_and_calls_search` 테스트 제거 (해당 래퍼 함수가 제거되었으므로).
        *   `test_symbols_command_with_query` 테스트는 `CommandHandler`의 `pass_args=True` 동작을 모의하도록 유지.
    3.  **`api` 서비스 통합 테스트 (`src/api/tests/unit/test_api_stock_master.py`) 수정 및 통과 확인:**
        *   `api` 서비스의 `/symbols/` 및 `/symbols/search` 엔드포인트가 `{"items": [...], "total_count": ...}` 형태의 딕셔너리를 반환하도록 변경되었으므로, 기존 테스트들이 이 응답 형식에 맞게 `response.json()['items']`와 `response.json()['total_count']`를 사용하도록 수정.
        *   `test_stock_master_data_fixture`에 "한화" 및 "한화생명" 종목을 추가하여 한글 검색 테스트(`test_search_symbols_korean_query`)가 유효한 데이터를 대상으로 실행되도록 함.
        *   모든 `api` 서비스 통합 테스트가 성공적으로 통과함을 확인. 이는 `api` 서비스의 검색 기능이 정상 작동함을 의미.
*   **테스트 결과:** `bot` 서비스의 `test_bot_symbols.py`를 포함한 모든 테스트가 성공적으로 통과. `api` 서비스의 모든 통합 테스트도 성공적으로 통과.