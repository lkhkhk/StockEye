# 개발자 가이드

이 문서는 StockEye 프로젝트의 개발 및 테스트에 필요한 기술적인 가이드라인을 제공합니다.

## 1. 개발 철학

- **MSA 기반 설계:** `api`와 `bot` 서비스는 독립적으로 개발, 배포, 확장이 가능해야 합니다.
- **테스트 주도 개발(TDD):** 새로운 기능을 추가하거나 코드를 수정할 때는 반드시 테스트 코드를 먼저 작성하거나, 기존 테스트를 통과해야 합니다. 이를 통해 코드의 안정성과 유지보수성을 높입니다.
- **코드 컨벤션:** 프로젝트 전반의 코드 스타일과 구조적 일관성을 유지합니다.

## 2. Git 브랜치 구조 및 워크플로우

StockEye 프로젝트는 다음과 같은 Git 브랜치 구조를 따릅니다.

*   **`main` 브랜치**: 프로덕션 배포 가능한 안정적인 코드를 관리합니다. `develop` 브랜치에서 충분히 테스트되고 검증된 기능들만 `main`으로 병합(merge)됩니다.
*   **`develop` 브랜치**: 모든 새로운 기능 개발 및 버그 수정이 이루어지는 주 개발 브랜치입니다. 개발자들은 이 브랜치에서 피처 브랜치를 생성하여 작업합니다.
*   **`stockeyeold` 브랜치**: 이전 `main` 브랜치의 이력을 보존하기 위한 브랜치입니다. 이 브랜치에는 더 이상 직접적인 개발 작업이 이루어지지 않습니다.

**개발 워크플로우:**
1.  새로운 기능 개발 또는 버그 수정 시, 항상 `develop` 브랜치에서 새로운 피처 브랜치를 생성합니다.
2.  피처 브랜치에서 작업을 완료한 후, `develop` 브랜치로 Pull Request를 생성하여 코드 리뷰 및 테스트를 거칩니다.
3.  `develop` 브랜치에 충분한 기능이 모이고 안정화되면, `main` 브랜치로 병합하여 릴리즈를 준비합니다.
4.  모든 개발 작업은 `develop` 브랜치에서 시작되어야 합니다.

## 3. API 서비스 (`src/api`)

### 3.1. 테스트 환경 (`conftest.py`)

- 모든 API 테스트는 `sqlite` 인메모리 데이터베이스를 사용합니다. `conftest.py`의 `db` fixture는 각 테스트 함수마다 독립적인 DB 트랜잭션을 보장하고, 테스트 종료 후 자동으로 롤백하여 테스트 간 격리를 유지합니다.
- `client` fixture는 `TestClient` 인스턴스를 생성하며, `get_db` 의존성을 테스트용 DB 세션으로 오버라이드하여 실제 DB에 영향을 주지 않습니다.

### 3.2. 테스트 작성 가이드

- **파일 구조:** 라우터 단위로 `test_api_[router_name].py` 형식의 테스트 파일을 생성합니다.
- **Given-When-Then 패턴:** 테스트의 가독성을 위해 준비(Given), 실행(When), 검증(Then) 구조를 따릅니다.
- **상세한 검증:** `status_code` 뿐만 아니라, Pydantic 스키마를 활용하여 응답 본문의 전체 구조와 각 필드의 데이터 타입까지 상세하게 검증해야 합니다.
- **인증/인가 테스트:** `@pytest.mark.parametrize`를 사용하여 "관리자", "일반 사용자", "미인증 사용자" 등 다양한 역할에 따른 접근 제어(성공, 401 Unauthorized, 403 Forbidden)를 반드시 검증합니다.
- **헬퍼 함수 활용:** 사용자 생성, 인증 토큰 발급 등 반복되는 로직은 `src/api/tests/helpers.py`의 헬퍼 함수를 사용하여 중복을 최소화합니다.

## 4. Bot 서비스 (`src/bot`)

### 4.1. 테스트 구조

- **비동기 테스트:** 모든 핸들러 테스트 함수는 `async def`로 선언하고 `@pytest.mark.asyncio` 데코레이터를 사용합니다.
- **Mock 객체 사용:** `unittest.mock.AsyncMock`을 사용하여 `telegram.Update`, `telegram.ext.ContextTypes` 등 텔레그램 객체와 외부 API 호출(`httpx.AsyncClient`)을 모의(Mock)합니다.
- **파일 구조:** 핸들러 단위로 `test_[handler_name].py` 형식의 파일을 생성합니다.

### 4.2. 핸들러 테스트 작성법

- **`Update` 객체 모의:** 사용자의 메시지, 커맨드(`context.args`), 콜백 쿼리(`update.callback_query`) 등 다양한 입력을 시뮬레이션하기 위해 `Update` 객체를 상세하게 모의해야 합니다.
- **API 호출 모의:** `unittest.mock.patch`를 사용하여 `httpx` 세션의 `get`, `post` 등의 메서드를 모의 처리하여 `api` 서비스의 응답을 시뮬레이션합니다. 이를 통해 `bot` 서비스 로직을 독립적으로 테스트할 수 있습니다.
- **응답 메시지 검증:** `update.message.reply_text`나 `update.callback_query.edit_message_text`와 같은 응답 함수가 올바른 인자(`chat_id`, `text`, `parse_mode` 등)와 함께 호출되었는지 `assert_called_once_with` 등으로 검증합니다.

## 5. Common 모듈 (`src/common`)

- 공통 모듈은 외부 의존성이 적으므로 전통적인 단위 테스트를 작성하기 용이합니다.
- 특히 `http_client.py`의 재시도 로직이나 `dart_utils.py`의 데이터 파싱 로직 등은 다양한 성공/실패 시나리오에 대해 독립적인 테스트를 통해 안정성을 검증해야 합니다.

## 6. 안정적인 테스트 환경 구축 가이드

통합 테스트, 특히 데이터베이스와 연동되는 테스트는 잘못된 설정으로 인해 많은 시간을 낭비하게 할 수 있습니다. 다음은 테스트 환경의 안정성을 확보하기 위한 핵심 가이드라인입니다.

### 6.1. 테스트 데이터베이스 Fixture 설계 (`conftest.py`)

테스트 DB Fixture는 타이밍 문제와 상태 오염을 막기 위해 신중하게 설계해야 합니다.

- **Engine과 Session의 생명주기를 분리하세요:**
    - **`db_engine` (Session Scope):** `pytest` 세션 당 한 번만 실행되는 `session` 스코프의 fixture에서 데이터베이스 자체의 생성(`CREATE DATABASE`)과 삭제(`DROP DATABASE`)를 책임집니다. **SQLAlchemy `engine` 객체는 반드시 DB 생성이 확인된 후에 이 fixture 내부에서 생성하고 `yield` 해야 합니다.** 모듈 레벨에서 `engine`을 생성하면, DB가 준비되기 전의 불안정한 연결 상태를 캐싱하여 세션 내내 문제를 일으킬 수 있습니다.
    - **`real_db` (Function Scope):** 각 테스트 함수마다 실행되는 `function` 스코프의 fixture에서 테이블 스키마(`metadata.create_all`)와 데이터의 상태를 책임집니다. 매 테스트 직전에 테이블을 모두 `DROP`하고 `CREATE`하는 방식은 테스트 간의 완벽한 독립성을 보장하는 가장 확실한 방법입니다.

- **`TestClient`를 사용하세요:** 외부 API를 호출하는 `httpx`와 같은 라이브러리 대신, FastAPI의 `TestClient`를 사용하세요. `TestClient`는 `pytest`의 fixture와 함께 동작하여, 위에서 설계한 DB 세션 의존성을 올바르게 주입받고 트랜잭션을 관리할 수 있게 해줍니다.

### 6.2. Docker 호스트 볼륨 문제

- `docker-compose.yml`에서 `volumes: - ./db/db_data:/var/lib/postgresql/data`와 같이 호스트 경로에 DB 데이터를 직접 바인딩하는 경우, `docker compose down --volumes` 명령으로도 데이터가 삭제되지 않습니다.
- 테스트 중 DB 파일 손상(`InternalError_` 등)이 의심될 경우, 다음 순서로 완전히 초기화해야 합니다.
    1. `docker compose down`으로 모든 컨테이너를 중지합니다.
    2. `sudo rm -rf ./db/db_data` 명령으로 호스트의 DB 디렉토리 자체를 완전히 삭제합니다.
    3. `docker compose up -d --build`로 서비스를 재시작합니다.

### 6.3. 테스트 실패 시나리오 분석

- **`404 Not Found`:** API 라우터가 제대로 등록되지 않았거나, 요청 경로의 `prefix`가 잘못되었을 가능성이 가장 높습니다. `main.py`의 `app.include_router` 부분을 확인하세요.
- **`400 Bad Request` / `422 Unprocessable Entity`:** 요청 데이터의 형식이나 값이 Pydantic 스키마의 유효성 검증을 통과하지 못한 경우입니다. 요청 본문을 확인하세요.
- **`401 Unauthorized` / `403 Forbidden`:** 인증(로그인) 또는 인가(권한) 관련 문제입니다. 테스트에서 사용한 인증 토큰이 유효한지, 해당 유저가 필요한 권한을 가지고 있는지 확인하세요.
- **`pydantic.ValidationError` (서버 내부):** API가 반환하는 데이터가 `response_model`로 지정된 Pydantic 스키마와 일치하지 않는 경우입니다. `async` 함수에 `await`가 누락되어 코루틴 객체가 반환되는 경우가 흔한 원인입니다.