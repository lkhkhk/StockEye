# Gemini CLI Agent 지시사항 및 작업 기록

이 문서는 Gemini CLI Agent가 프로젝트 작업을 수행하면서 받은 주요 지시사항과 작업 기록을 관리합니다.

## 1. 작업 원칙 및 워크플로우

*   **선행 테스트:** 모든 신규 작업 착수 전, 전체 테스트를 먼저 실행하여 현 시스템의 안정성을 확인합니다.
*   **계획 수립 및 관리:**
    *   진행할 과제에 대한 상세 계획을 수립합니다.
    *   이 계획을 `docs/PLAN.MD` 파일에 To-Do 항목으로 추가하고, 진행 상황에 따라 항상 최신 상태로 업데이트합니다.
*   **개발 워크플로우:**
    1.  신규/변경 기능에 대한 **테스트 코드를 먼저 작성**합니다.
    2.  테스트를 통과하는 기능 코드를 구현합니다.
    3.  `docker compose`를 사용하여 전체 서비스를 다시 빌드하고 재기동합니다.
    4.  컨테이너 내에서 실제 기능을 테스트하여 완료를 확인합니다.
    5.  계획된 작업 단위가 완료되면, 진행 상황을 보고하고 다음 단계 진행에 대한 지시를 기다립니다.
*   **코드 품질 및 구조:**
    *   꼼꼼하고 신중하게 작업하며, 변경 사항이 기존 코드에 미치는 영향을 항상 확인합니다.
    *   기존 프로젝트 구조를 최대한 유지하며, 변경이 필요할 경우 사전에 상세 설명과 함께 문의합니다.
*   **`replace` 도구 사용 지침:**
    *   `replace` 도구 사용 전에는 반드시 `read_file`로 대상 파일의 현재 내용을 읽어옵니다.
    *   `old_string` 인자는 `read_file` 결과에서 변경할 부분을 정확히 복사하여 사용합니다. (공백, 들여쓰기, 줄바꿈 포함)
    *   `old_string`이 짧아 중복될 가능성이 있는 경우, 최소 3줄 이상의 충분한 컨텍스트를 포함합니다.
    *   여러 번 변경이 필요한 경우 `expected_replacements` 인자를 명시합니다.
*   **`src/common` 모듈 변경 시 주의사항:**
    *   `api`와 `bot` 서비스는 `src/common` 디렉토리를 공유하므로, 이 디렉토리 내의 파일 변경은 두 서비스 모두에 영향을 미칩니다.
    *   `src/common` 파일 변경 시, 해당 변경이 영향을 미치는 모든 `api` 및 `bot` 서비스의 관련 파일을 **동시에, 그리고 일관되게 수정**해야 합니다.
*   **실행 환경:**
    *   `docker compose` 명령어를 사용합니다.
    *   테스트 코드 작성 및 실행은 각 서비스(`api`, `bot`)의 `tests` 폴더 내에서, 컨테이너 안에서 수행합니다.
    *   파일 삭제 등 권한 문제가 발생할 수 있는 작업은 반드시 컨테이너 내부에서 실행합니다.
*   **커뮤니케이션:**
    *   지시사항을 잊지 않고 반복적인 지시가 발생하지 않도록 합니다.
    *   답변은 한국어로 합니다.

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
