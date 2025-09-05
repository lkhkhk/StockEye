# 6. Troubleshooting

## 텔레그램 봇 `/register`, `/unregister` 명령어 `Internal Server Error` 해결 과정

### 1. 문제 현상
텔레그램 봇에서 `/register` 또는 `/unregister` 명령어를 실행했을 때, 사용자에게 "[알림 동의 실패: Internal Server Error]" 메시지가 반환됨.

### 2. 초기 진단 및 로그 분석
초기 로그 분석 결과, `bot_service`에서 `api_service`로의 `PUT /users/telegram_register` 요청이 `500 Internal Server Error`로 실패하는 것을 확인.

**API 서비스 로그에서 발견된 주요 오류:**
```
api_service  | AttributeError: '_GeneratorContextManager' object has no attribute 'query'
api_service  |   File "/app/src/api/routers/user.py", line 85, in telegram_register
api_service  |     user = db.query(User).filter(User.telegram_id == telegram_id_int).first()
```

### 3. 원인 분석

### 3.1. `AttributeError: '_GeneratorContextManager' object has no attribute 'query'`
이 오류는 `src/api/routers/user.py`의 `telegram_register` 함수에서 `db.query()`를 호출할 때 발생했다. 이는 `db` 객체가 SQLAlchemy `Session` 객체가 아니라 `_GeneratorContextManager` 타입의 객체였기 때문이다.

**근본 원인:** `src/common/db_connector.py` 파일의 `get_db` 함수에 `@contextlib.contextmanager` 데코레이터가 사용되고 있었다. FastAPI의 `Depends`는 `yield`를 사용하는 함수를 직접 지원하지만, `@contextlib.contextmanager`는 함수를 제너레이터 컨텍스트 매니저 객체로 변환하여 FastAPI가 예상하는 `Session` 객체가 직접 주입되지 않았다.

### 3.2. `telegram_id` 타입 불일치 (초기 오진단)
초기에는 `src/api/routers/user.py`에서 `telegram_id`를 `int`로 받는데 `src/bot/handlers/register.py`에서 `str`로 보내는 타입 불일치가 원인일 수 있다고 판단했다.
- `src/api/schemas/user.py`에 `TelegramRegister` 스키마를 추가하고, `src/api/routers/user.py`에서 이를 사용하도록 수정했다.
- `src/api/tests/unit/test_api_user.py`에서 `telegram_id`를 문자열로 전달하도록 테스트 코드를 수정했다.
하지만 이 수정 후에도 `422 Unprocessable Entity` 오류가 발생했으며, 이는 `Body(...)`의 `embed=True` (기본 동작) 때문이었다. `embed=True`를 제거했으나 여전히 422 오류가 발생하여, 최종적으로 Pydantic 모델을 사용하는 방식으로 전환했다.
결과적으로 이 부분은 `AttributeError`의 직접적인 원인은 아니었으나, API 요청/응답의 유효성 검증을 개선하는 데 기여했다.

### 4. 해결 과정

### 4.1. `get_db` 함수 수정
`src/common/db_connector.py` 파일에서 `get_db` 함수에 적용된 `@contextlib.contextmanager` 데코레이터와 `import contextlib` 라인을 제거했다.
이로써 `get_db` 함수는 이제 직접 SQLAlchemy `Session` 객체를 `yield`하게 되어, FastAPI의 `Depends`가 올바른 `Session` 객체를 주입할 수 있게 되었다.

### 4.2. `telegram_id` 처리 로직 개선 (이전 수정 포함)
- `src/api/schemas/user.py`에 `TelegramRegister(BaseModel)` 스키마를 정의하여 `telegram_id: str`과 `is_active: bool`을 명시했다.
- `src/api/routers/user.py`의 `telegram_register` 엔드포인트에서 `register_data: TelegramRegister`를 인자로 받도록 변경하고, `register_data.telegram_id`를 `int()`로 변환하여 데이터베이스 작업에 사용하도록 했다.
- `src/api/tests/unit/test_api_user.py`의 관련 테스트에서 `telegram_id`를 `str()`로 변환하여 `json` 페이로드에 포함하도록 수정했다.

### 5. 영향 분석 및 테스트 환경 설명

### 5.1. `get_db` 변경의 영향
`src/common/db_connector.py`의 `get_db` 함수에서 `@contextlib.contextmanager` 데코레이터를 제거한 것은 `db` 객체의 타입이 `_GeneratorContextManager`에서 실제 SQLAlchemy `Session` 객체로 변경되는 핵심적인 수정이다. 이 변경은 `db` 객체를 SQLAlchemy `Session`으로 가정하고 `query`, `add`, `commit`, `rollback` 등의 메서드를 호출하는 모든 코드(라우터, 서비스, 인증 관련 파일, 테스트 파일 등)에 긍정적인 영향을 미친다. 이전에 발생했던 `AttributeError`는 이 수정으로 인해 해결된다.

### 5.2. 테스트 환경과 실제 DB 연결
- **단위 테스트 (Unit Test):** `src/api/tests/conftest.py`의 `db` 픽스처는 `MagicMock(spec=Session)`을 사용하여 실제 DB 연결 없이 `Session` 객체의 동작을 흉내 낸다. 이는 특정 함수/클래스의 로직을 빠르게 테스트하는 데 사용된다.
- **통합 테스트 (Integration Test):** `src/api/tests/conftest.py`의 `real_db` 픽스처는 `TestingSessionLocal()`을 통해 **별도의 테스트용 PostgreSQL 데이터베이스**에 연결된 실제 `Session` 객체를 생성한다. 각 테스트 시작 전에 데이터를 초기화하여 테스트 간 격리를 보장한다. 이는 여러 구성 요소의 통합을 검증하는 데 사용된다.

### 5.3. `dependency_overrides`를 통한 테스트와 실제 서비스 구분
FastAPI는 `app.dependency_overrides` 기능을 제공하여 테스트 시 의존성 주입을 오버라이드할 수 있다.
`src/api/tests/conftest.py`의 `client` 픽스처는 `app.dependency_overrides[get_db] = override_get_db`를 통해 `get_db` 의존성을 오버라이드한다. `override_get_db`는 `real_db` 픽스처가 제공하는 실제 `Session` 객체를 `yield`한다.
따라서 테스트를 실행할 때는 `src/common/db_connector.py`의 `get_db` 함수가 직접 실행되는 것이 아니라, `conftest.py`에 정의된 테스트용 DB 세션(Mock 또는 실제 테스트 DB)이 주입된다.

### 5.4. 이번 변경이 기존 테스트에 미치는 영향
이번 `get_db` 함수 수정은 실제 `get_db` 함수가 테스트 환경의 `real_db` 픽스처처럼 **직접 SQLAlchemy `Session` 객체를 `yield`하도록 변경한 것**이다. 기존 테스트는 이미 `dependency_overrides` 덕분에 올바른 `Session` 객체를 주입받아 성공하고 있었으므로, 이번 변경은 테스트에 부정적인 영향을 주지 않는다. 오히려 실제 코드의 동작을 테스트 환경의 성공적인 동작 방식과 일치시켜 시스템의 일관성과 안정성을 높인다.

### 6. 결론
`get_db` 함수의 `@contextlib.contextmanager` 데코레이터 제거 및 `telegram_id` 처리 로직 개선을 통해 `/register`, `/unregister` 명령어의 `Internal Server Error`가 해결될 것으로 예상된다. 이 변경은 기존 테스트에 부정적인 영향을 주지 않으며, 시스템의 안정성을 향상시킨다.

---

## `httpx.Response` 객체에서 `AttributeError: 'Response' object has no attribute 'ok'` 발생

-   **발생 시점:** `httpx` 라이브러리를 사용하여 API를 호출하고, 응답 객체(response)의 성공 여부를 `response.ok` 속성으로 확인할 때 발생합니다.
-   **원인:** `httpx` 라이브러리 버전 `0.27.0` 이상부터 `response.ok` 속성이 **비활성화(deprecated)**되고 `response.is_success` 속성으로 대체되었습니다. 프로젝트의 `requirements.txt`에 명시된 `python-telegram-bot` 라이브러리는 `httpx>=0.27,<0.29` 버전을 요구하므로, 최신 버전의 `httpx`가 설치되면서 이 문제가 발생합니다.
-   **해결책:** 코드 내에서 `httpx.Response` 객체의 성공 여부를 확인할 때, `response.ok` 대신 **`response.is_success`**를 사용해야 합니다.

    ```python
    # 기존 코드 (오류 발생)
    if response.ok:
        # ...

    # 수정된 코드 (정상 동작)
    if response.is_success:
        # ...
    ```

-   **재발 방지:**
    -   새로운 API 연동 코드 작성 시, `httpx` 응답을 처리할 때는 항상 `is_success` 속성을 사용합니다.
    -   만약 유사한 `AttributeError`가 다른 라이브러리에서 발생할 경우, 라이브러리 버전과 공식 문서의 변경 이력(Changelog)을 우선적으로 확인하여 속성 또는 메서드의 변경 사항이 있는지 검토합니다.

---

## `ImportError: cannot import name '...'` (순환 참조 오류)

-   **발생 시점:** `docker compose up`으로 서비스를 시작할 때, API 서비스가 기동에 실패하며 `ImportError: cannot import name '...' from partially initialized module '...' (most likely due to a circular import)`와 유사한 오류를 출력합니다.

-   **원인:** 파이썬의 모듈 임포트 과정에서 두 개 이상의 모듈이 서로를 직간접적으로 참조하는 '순환 참조(Circular Import)' 고리가 만들어졌기 때문입니다. 예를 들어, `A.py`가 `B.py`를 임포트하고, `B.py`가 다시 `A.py`를 임포트하는 경우입니다. 이 프로젝트에서는 라우터, 서비스, 인증 핸들러 등 여러 파일이 서로의 기능을 사용하면서 복잡한 의존성 관계가 형성되어 이 문제가 발생했습니다.
    -   `라우터(A) -> 서비스(B) -> 인증 핸들러(C) -> 서비스(B)` 와 같은 구조도 순환 참조를 유발할 수 있습니다.

-   **해결책:** 모듈 최상단(Global Scope)에서의 임포트를 피하고, **함수 또는 메서드 내에서 필요한 시점에 지역적으로 임포트(Local Import)**하여 순환 고리를 끊습니다. 이 방법은 모듈이 로드되는 시점에는 의존성이 발생하지 않도록 하여 문제를 해결합니다.

    ```python
    # src/api/routers/auth.py (수정 전 - 오류 발생 가능)
    from src.common.services.user_service import UserService, get_user_service

    @router.post("/bot/token")
    def get_token_for_bot(user_service: UserService = Depends(get_user_service)):
        # ...
    ```

    ```python
    # src/api/routers/auth.py (수정 후 - 정상 동작)
    # 상단에서 UserService 임포트 제거

    @router.post("/bot/token")
    def get_token_for_bot(db: Session = Depends(get_db)):
        # 함수 내에서 필요할 때 지역적으로 임포트
        from src.common.services.user_service import UserService
        user_service = UserService()
        # ... 이제 user_service 사용 가능
    ```

-   **재발 방지:**
    -   새로운 기능을 추가할 때, 모듈 간의 의존성 관계가 어떻게 형성되는지 신중하게 고려합니다.
    -   순환 참조가 의심될 경우, 의존성 주입(Dependency Injection)을 사용하거나, 위와 같이 지역 임포트를 활용하여 의존성 발생 시점을 늦추는 방법을 적극적으로 검토합니다.

---

## 테스트 실행 시 멈춤(Hang) 또는 원인 불명의 비동기/Mock 오류 해결

-   **발생 시점:** `pytest`로 특정 테스트(주로 `asyncio`와 `unittest.mock.patch`를 함께 사용하는 복잡한 테스트)를 실행할 때, 테스트가 끝나지 않고 멈추거나, 이해하기 어려운 `TypeError` 또는 `AttributeError`를 내며 실패합니다.

-   **원인:**
    -   비동기 코드에 대한 Mocking 설정이 복잡하게 얽혀 교착 상태(Deadlock)를 유발하는 경우.
    -   테스트 대상 코드의 초기화 과정이나 의존성 주입 부분에서 숨겨진 오류가 발생하여 테스트 실행기(pytest)가 본격적인 테스트 시작 전에 멈추는 경우.
    -   테스트 환경의 로그 레벨 설정이 낮아, 원인 파악에 필요한 로그가 출력되지 않는 경우.

-   **해결책: 최소 단위 임시 테스트 (Minimal Temporary Test) 전략**
    -   복잡한 테스트 파일 전체를 디버깅하려 하지 않고, 문제가 되는 기능의 **가장 핵심적인 부분만 검증하는 아주 작은 임시 테스트**를 작성하여 문제의 범위를 획기적으로 좁히는 전략입니다.

-   **진행 단계:**
    1.  **현상 파악:** `timeout <SECONDS> docker compose exec ...` 명령을 사용하여 테스트가 정말로 멈추는지, 아니면 단순히 오래 걸리는지 확인합니다. (예: `timeout 30s ...`)
    2.  **임시 테스트 파일 생성:** 기존 테스트 파일은 그대로 두고, `tests/unit/test_temp_...py` 와 같은 이름으로 새 테스트 파일을 생성합니다.
    3.  **최소 기능 테스트 작성:**
        -   문제가 되는 함수(`A`)를 임포트합니다.
        -   `A` 함수 내부의 **첫 번째 `await` 지점**이나 의심되는 부분만 실행하고, 즉시 테스트가 종료되도록 Mock을 설정합니다.
        -   예를 들어, `notification_listener`가 `while True:` 루프에서 멈추는 것을 방지하기 위해, 루프 내부의 `get_message`가 `asyncio.CancelledError`를 발생시키도록 Mocking하여 즉시 루프를 탈출시킵니다.
    4.  **상세 로그 확인 설정:**
        -   테스트 함수에 `caplog` 픽스처를 추가합니다.
        -   테스트 시작 시 `caplog.set_level(logging.DEBUG, logger="<테스트 대상의 로거 이름>")` 코드를 추가하여, 테스트 중 발생하는 모든 레벨의 로그를 놓치지 않고 확인할 수 있도록 설정합니다.
        -   문제가 되는 함수 자체에도 `logger.info` 또는 `logger.debug`를 추가하여 실행 흐름을 추적합니다.
    5.  **임시 테스트 실행 및 분석:**
        -   새로 만든 임시 테스트를 실행합니다. 이 테스트는 멈추지 않고 빠르게 실패하며 명확한 오류 메시지나 로그를 출력해야 합니다.
        -   출력된 로그와 오류를 분석하여 실제 코드(`main.py` 등)의 버그를 찾아 수정합니다.
    6.  **정리:** 실제 코드의 버그를 수정한 후, 임시 테스트로 최종 검증을 하고, 역할을 다한 임시 테스트 파일은 삭제합니다.
    7.  **원래 테스트 재검증:** 마지막으로, 원래 문제가 있었던 테스트 파일을 다시 실행하여 모든 문제가 해결되었는지 확인합니다.

-   **기대 효과:**
    -   복잡한 의존성과 비동기 로직을 분리하여, 문제의 원인을 명확하게 특정할 수 있습니다.
    -   '멈춤' 현상 뒤에 숨어있는 실제 `AttributeError`, `TypeError` 등의 근본적인 버그를 발견할 수 있습니다.

---

## FastAPI 테스트: `dependency_overrides`와 `patch`의 올바른 사용법

-   **문제 상황:** `unittest.mock.patch`를 사용하여 FastAPI의 의존성(DB 세션, 서비스 클래스 등)을 Mocking할 경우, 원인 불명의 테스트 멈춤(Hang) 현상이 간헐적으로 발생했습니다. 이는 `patch`가 파이썬의 `import` 시스템에 개입하는 방식과 FastAPI의 `TestClient` 및 의존성 주입 시스템의 내부 동작이 충돌하면서 발생하는 것으로 분석됩니다.

-   **핵심 원칙:** FastAPI 테스트의 안정성과 신뢰성을 확보하기 위해, 두 도구의 역할을 명확히 구분하여 사용해야 합니다.

### 1. `app.dependency_overrides`: FastAPI 의존성 주입의 공식적인 방법

-   **언제 사용해야 하는가?**
    -   엔드포인트 함수에서 `Depends(...)`를 통해 주입되는 **모든 의존성**을 테스트에서 가짜(Mock)로 대체할 때 사용합니다.
    -   예: `db: Session = Depends(get_db)`, `stock_service: StockService = Depends(get_stock_service)` 등

-   **왜 더 좋은가?**
    -   **신뢰성:** FastAPI 프레임워크가 공식적으로 제공하는 기능으로, 내부 동작과 충돌하지 않아 매우 안정적입니다. 테스트 멈춤 현상의 근본적인 해결책입니다.
    -   **명확성:** "FastAPI의 의존성을 테스트용으로 대체한다"는 의도가 코드에 명확하게 드러납니다.
    -   **견고성:** 의존성이 어디서 `import` 되는지 신경 쓸 필요 없이, 원본 의존성 함수(`get_db`) 자체를 키(key)로 사용하므로 실수가 적습니다.

-   **비유:** 자동차의 정비 모드를 켜고, 제조사가 제공하는 정식 절차에 따라 부품(의존성)을 안전하게 교체하는 것과 같습니다.

### 2. `unittest.mock.patch`: 범용적인 파이썬 Mocking 도구

-   **언제 사용해야 하는가?**
    -   FastAPI의 `Depends`와 관련 **없는** 대상을 Mocking할 때 사용합니다.
    -   **환경 변수:** `patch.dict(os.environ, ...)`
    -   **외부 라이브러리 호출:** `patch('httpx.AsyncClient')`
    -   **의존성 주입과 관련 없는 일반 함수/클래스:** `patch('src.api.main.seed_test_data')`

-   **왜 여기서는 `patch`를 쓰는가?**
    -   `dependency_overrides`는 `Depends`로 관리되는 대상만 대체할 수 있기 때문입니다. 그 외의 모든 것은 범용 도구인 `patch`를 사용해야 합니다.

-   **비유:** 자동차의 오디오나 내비게이션처럼, 엔진(FastAPI 의존성 주입 시스템)과 직접적인 관련이 없는 부가적인 부품을 교체하는 것과 같습니다.

### 최종 규칙

> **FastAPI 테스트를 작성할 때, `Depends`로 주입되는 대상은 `app.dependency_overrides`를 사용하고, 그 외 모든 것은 `patch`를 사용한다.**

이 원칙을 일관되게 적용하여 `api` 서비스의 단위 테스트를 리팩토링했으며, 이를 통해 모든 테스트 멈춤 현상을 해결하고 안정적인 테스트 스위트를 구축했습니다.

---

## SQLAlchemy/SQLite 단위 테스트 시 `datetime` 파싱 오류 해결

-   **발생 시점:** `pytest`로 SQLAlchemy 모델 및 서비스를 테스트할 때, `ValueError: Invalid isoformat string` 또는 `ValueError: time data ... does not match format ...` 오류가 간헐적으로, 그리고 여러 테스트 파일에 걸쳐 반복적으로 발생했습니다.

-   **원인 분석:** 이 문제는 여러 요인이 복합적으로 작용한 결과입니다.
    1.  **DB와 Python 간의 `datetime` 형식 불일치:** Python의 `datetime.isoformat()`은 날짜와 시간 사이에 `T` 구분자를 사용합니다 (예: `2023-10-27T10:00:00`). 하지만 테스트에 사용된 인메모리 SQLite는 `datetime` 객체를 `T`가 없는 공백 구분자 형태의 문자열로 저장하는 경우가 많습니다 (예: `2023-10-27 10:00:00`).
    2.  **마이크로초(Microseconds) 유무:** `datetime.datetime.now()`는 마이크로초를 포함하는 값을 생성하지만, DB에 저장되었다가 다시 읽어올 때는 이 값이 생략될 수 있습니다. 이로 인해 `strptime` 포맷 문자열(`%f`)과 실제 값의 형식이 일치하지 않는 문제가 발생합니다.
    3.  **불안정한 `TypeDecorator`:** `conftest.py`에 정의된 `SQLiteDateTime` 타입 데코레이터가 이러한 모든 경우의 수를 충분히 유연하게 처리하지 못하여, 특정 형식의 날짜/시간 문자열만 파싱할 수 있었고 다른 형식의 문자열을 만나면 `ValueError`를 발생시켰습니다.

-   **해결 과정 및 최종 방안:**

    1.  **`conftest.py`의 `SQLiteDateTime` 데코레이터 강화 (핵심 해결책):**
        -   `process_result_value` 메서드 내에 여러 `try-except` 블록을 중첩하여, 다양한 날짜/시간 문자열 형식을 순차적으로 파싱하도록 수정했습니다. 이 방법은 `T` 구분자 및 마이크로초의 유무와 관계없이 안정적으로 `datetime` 객체를 복원합니다.

        ```python
        # src/common/tests/unit/conftest.py
        class SQLiteDateTime(types.TypeDecorator):
            # ... (process_bind_param은 동일)
            def process_result_value(self, value, dialect):
                if value is not None:
                    try:
                        # 'T' 구분자 + 마이크로초
                        return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')
                    except ValueError:
                        try:
                            # 'T' 구분자 (마이크로초 없음)
                            return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
                        except ValueError:
                            try:
                                # 공백 구분자 + 마이크로초
                                return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
                            except ValueError:
                                # 공백 구분자 (마이크로초 없음)
                                return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                return value
        ```

    2.  **`Date` 타입 컬럼의 명확한 사용:**
        -   `datetime`이 아닌 `date` 정보만 필요한 `TestDailyPrice` 모델의 경우, 컬럼 타입을 SQLAlchemy의 `Date`로 명시적으로 변경했습니다. 이렇게 하면 시간 정보와 관련된 복잡한 파싱 문제를 근본적으로 피할 수 있습니다.
        -   이에 맞춰 해당 모델을 사용하는 테스트 코드(`test_price_alert_service_notification.py`)에서는 `datetime.date.today()`와 같이 `date` 객체를 직접 사용하여 테스트 데이터를 생성하도록 수정했습니다.

-   **재발 방지 및 향후 가이드라인:**
    -   **규칙 1:** 단위 테스트에서 `DateTime`을 다룰 때는, `conftest.py`에 정의된 **강화된 `SQLiteDateTime` 타입 데코레이터를 항상 사용**합니다. 이 데코레이터는 SQLite와의 호환성 문제를 대부분 해결해 줍니다.
    -   **규칙 2:** 시간 정보가 필요 없는 날짜 데이터는 반드시 SQLAlchemy의 **`Date` 타입을 사용**하고, 테스트 데이터 역시 `datetime.date` 객체로 생성하여 혼동을 방지합니다.
    -   **규칙 3:** 새로운 테스트 모델에 날짜/시간 관련 컬럼 추가 시, 위 두 규칙을 반드시 준수하여 같은 문제가 재발하지 않도록 합니다.

---

## `bot` 서비스 E2E 테스트의 간헐적 OOM 오류

`bot` 서비스의 E2E 테스트(`src/bot/tests/e2e/test_prediction_history_e2e.py`) 실행 시, 간헐적으로 메모리 부족(OOM)으로 인해 테스트가 실패하는 현상이 발생했습니다. 이 문제는 `stockeye-worker` 서비스가 함께 실행될 때 더 자주 발생하는 경향을 보였습니다.

### 원인 분석

`docker stats`를 통해 컨테이너별 메모리 사용량을 모니터링한 결과, `stockeye-bot` 컨테이너의 메모리 사용량이 테스트 중에 급격히 증가하는 것을 확인했습니다.

문제의 원인을 파악하기 위해 `bot` 서비스의 코드, 특히 E2E 테스트에서 호출되는 핸들러들을 분석했습니다. 분석 결과, `src/bot/handlers/natural.py`의 `natural_message_handler` 함수가 동기(synchronous) 방식의 `requests` 라이브러리를 사용하여 여러 차례 API를 호출하는 것을 확인했습니다.

`bot` 서비스는 `asyncio` 기반의 비동기 애플리케이션이므로, 동기 방식의 I/O 작업(예: `requests`를 사용한 HTTP 요청)은 이벤트 루프를 블로킹합니다. 이로 인해 다음과 같은 문제가 발생할 수 있습니다.

1.  **이벤트 루프 블로킹**: 동기 요청이 완료될 때까지 다른 모든 작업을 중단시켜 애플리케이션의 응답성을 저하시킵니다.
2.  **메모리 사용량 증가**: 여러 요청이 동시에 처리되지 못하고 대기 상태에 빠지면서, 각 요청에 할당된 메모리가 해제되지 않고 누적되어 메모리 사용량이 급격히 증가할 수 있습니다.

이러한 이유로 `natural_message_handler`가 호출될 때마다 `bot` 서비스의 메모리 사용량이 크게 증가했고, 이는 간헐적인 OOM 오류의 직접적인 원인이 되었습니다.

### 해결 방안

문제 해결을 위해 `natural.py` 핸들러의 모든 `requests` 호출을 비동기(asynchronous) 방식의 `httpx` 라이브러리를 사용하도록 리팩토링했습니다.

-   **기존 코드 (requests 사용):**
    ```python
    import requests
    
    response = requests.get(f"{API_URL}/symbols/search", params={"query": text})
    ```

-   **개선된 코드 (httpx 사용):**
    ```python
    import httpx
    from src.common.utils.http_client import get_retry_client

    async with get_retry_client() as client:
        response = await client.get(f"/api/v1/symbols/search", params={"query": text})
    ```

`get_retry_client` 팩토리 함수를 통해 `httpx.AsyncClient` 인스턴스를 생성하고, `async with`와 `await`를 사용하여 비동기적으로 API를 호출하도록 수정했습니다.

### 결과

리팩토링 후, `stockeye-worker` 서비스를 포함한 모든 서비스를 가동한 상태에서 `bot` 서비스의 E2E 테스트를 반복적으로 실행한 결과, 더 이상 메모리 부족으로 인한 오류가 발생하지 않았습니다. `docker stats`를 통해서도 `bot` 컨테이너의 메모리 사용량이 안정적으로 유지되는 것을 확인했습니다.

이를 통해 동기 라이브러리 사용으로 인한 이벤트 루프 블로킹이 성능 저하 및 메모리 문제의 근본적인 원인이었음을 최종적으로 확인하고, 비동기 라이브러리로 교체하여 문제를 해결했습니다.