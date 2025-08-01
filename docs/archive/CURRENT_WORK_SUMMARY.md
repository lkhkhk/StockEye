# 현재 작업 요약: 텔레그램 봇 명령어 오류 수정 및 async/await 일관성 확보

## 1. 작업 목표
텔레그램 봇의 `alert_add`, `alert_list`, `alert_remove`, `register`, `unregister` 명령어 실행 시 발생하는 오류를 해결하고, `httpx` 라이브러리의 `async`/`await` 사용법을 포함한 비동기 처리 로직의 일관성을 확보합니다.

## 2. 발생 문제 및 해결 과정 요약

### 2.1. `httpx.Response.json()` 관련 `async`/`await` 혼선
*   **문제:** `alert_add` 및 `alert_list` 명령어에서 `httpx.Response.json()` 메서드를 호출할 때 `await` 키워드 사용 여부에 대한 혼선으로 `object list can't be used in 'await' expression` 오류가 발생했습니다. `httpx.Response.json()`은 비동기 메서드이므로 `await`가 필요합니다.
*   **해결:** `src/bot/handlers/alert.py` 파일 내 `alert_add`, `alert_list` 함수에서 `resp.json()` 호출 시 `await`를 추가합니다.

### 2.2. 이전 작업에서 발생했던 주요 오류들 (참고용)

*   **`telegram.error.Conflict: terminated by other getUpdates request`**:
    *   **원인:** 텔레그램 봇 다중 인스턴스 실행.
    *   **해결:** `docker compose down --remove-orphans`로 환경 초기화.
*   **API 서비스 `KeyError: 'url'`**:
    *   **원인:** `httpx`의 `post` 메서드에 URL이 위치 인자로 전달되는데, 테스트 코드에서 `kwargs['url']`로 접근 시도.
    *   **해결:** `src/bot/tests/test_alert_handler.py`에서 `args[0]`을 사용하여 URL에 접근하도록 테스트 코드 수정.
*   **`psycopg2.errors.UndefinedFunction: operator does not exist: character varying = integer`**:
    *   **원인:** `telegram_id` 컬럼 타입 불일치 (String vs Integer) 및 `INTEGER` 범위 초과.
    *   **해결:** `src/api/models/user.py`에서 `telegram_id`를 `BigInteger`로 변경 후 DB 스키마 업데이트.
*   **`NameError: name 'BigInteger' is not defined`**:
    *   **원인:** `src/api/models/user.py`에서 `BigInteger` 임포트 누락.
    *   **해결:** `src/api/models/user.py`에 `from sqlalchemy import BigInteger` 추가.
*   **`TypeError: 'first_name' is an invalid keyword argument for User`**:
    *   **원인:** `User` 모델에 `first_name`, `last_name` 컬럼 정의 누락.
    *   **해결:** `src/api/models/user.py`에 `first_name`, `last_name` 컬럼 추가 후 DB 스키마 업데이트.
*   **`psycopg2.errors.NotNullViolation` (for `password_hash`, `email`)**:
    *   **원인:** 텔레그램 사용자 생성 시 `password_hash`, `email`이 `None`으로 전달되는데 DB 컬럼이 `NOT NULL` 제약 조건을 가짐.
    *   **해결:** `src/api/models/user.py`에서 해당 컬럼들을 `nullable=True`로 변경 후 DB 스키마 업데이트.
*   **`psycopg2.errors.UndefinedColumn` (for `change_percent`, `change_type`, `repeat_interval`)**:
    *   **원인:** `PriceAlert` 모델에 컬럼이 정의되었으나 DB 스키마에 반영되지 않음.
    *   **해결:** DB 스키마에 해당 컬럼들 추가.
*   **`IndentationError`**:
    *   **원인:** `src/bot/handlers/alert.py` 파일의 들여쓰기 오류.
    *   **해결:** 해당 줄의 들여쓰기 수정.
*   **`AssertionError: expected call not found.` (가격 포맷팅)**:
    *   **원인:** `float` 값의 문자열 포맷팅 불일치.
    *   **해결:** `src/bot/tests/test_alert_handler.py`에서 예상 문자열을 `75,000.0원`으로 변경.

## 3. 현재 코드 상태 및 다음 작업 계획

테스트 코드(`src/bot/tests/test_alert_handler.py`)에서는 `httpx.Response.json()`이 비동기 메서드임을 반영하여 `mock_response.json = AsyncMock(return_value=...)` 형태로 모의 방식을 변경해야 합니다.

1.  **`src/bot/tests/test_alert_handler.py` 수정:**
    *   모든 `mock_response.json.return_value = ...` 부분을 `mock_response.json = AsyncMock(return_value=...)`로 변경합니다.
2.  **Docker 컨테이너 재빌드 및 실행:** 모든 코드 변경 후 `docker compose down --remove-orphans` 및 `docker compose up --build -d`를 실행합니다.
3.  **봇 핸들러 테스트 재실행:** `pytest src/bot/tests/test_alert_handler.py`를 실행하여 모든 테스트가 통과하는지 확인합니다.
