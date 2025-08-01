# 개발자 가이드

이 문서는 StocksEye 프로젝트의 개발 및 테스트에 필요한 기술적인 가이드라인을 제공합니다.

## 1. 개발 철학

- **MSA 기반 설계:** `api`와 `bot` 서비스는 독립적으로 개발, 배포, 확장이 가능해야 합니다.
- **테스트 주도 개발(TDD):** 새로운 기능을 추가하거나 코드를 수정할 때는 반드시 테스트 코드를 먼저 작성하거나, 기존 테스트를 통과해야 합니다. 이를 통해 코드의 안정성과 유지보수성을 높입니다.
- **코드 컨벤션:** 프로젝트 전반의 코드 스타일과 구조적 일관성을 유지합니다.

## 2. API 서비스 (`src/api`)

### 2.1. 테스트 환경 (`conftest.py`)

- 모든 API 테스트는 `sqlite` 인메모리 데이터베이스를 사용합니다. `conftest.py`의 `db` fixture는 각 테스트 함수마다 독립적인 DB 트랜잭션을 보장하고, 테스트 종료 후 자동으로 롤백하여 테스트 간 격리를 유지합니다.
- `client` fixture는 `TestClient` 인스턴스를 생성하며, `get_db` 의존성을 테스트용 DB 세션으로 오버라이드하여 실제 DB에 영향을 주지 않습니다.

### 2.2. 테스트 작성 가이드

- **파일 구조:** 라우터 단위로 `test_api_[router_name].py` 형식의 테스트 파일을 생성합니다.
- **Given-When-Then 패턴:** 테스트의 가독성을 위해 준비(Given), 실행(When), 검증(Then) 구조를 따릅니다.
- **상세한 검증:** `status_code` 뿐만 아니라, Pydantic 스키마를 활용하여 응답 본문의 전체 구조와 각 필드의 데이터 타입까지 상세하게 검증해야 합니다.
- **인증/인가 테스트:** `@pytest.mark.parametrize`를 사용하여 "관리자", "일반 사용자", "미인증 사용자" 등 다양한 역할에 따른 접근 제어(성공, 401 Unauthorized, 403 Forbidden)를 반드시 검증합니다.
- **헬퍼 함수 활용:** 사용자 생성, 인증 토큰 발급 등 반복되는 로직은 `src/api/tests/helpers.py`의 헬퍼 함수를 사용하여 중복을 최소화합니다.

## 3. Bot 서비스 (`src/bot`)

### 3.1. 테스트 구조

- **비동기 테스트:** 모든 핸들러 테스트 함수는 `async def`로 선언하고 `@pytest.mark.asyncio` 데코레이터를 사용합니다.
- **Mock 객체 사용:** `unittest.mock.AsyncMock`을 사용하여 `telegram.Update`, `telegram.ext.ContextTypes` 등 텔레그램 객체와 외부 API 호출(`httpx.AsyncClient`)을 모의(Mock)합니다.
- **파일 구조:** 핸들러 단위로 `test_[handler_name].py` 형식의 파일을 생성합니다.

### 3.2. 핸들러 테스트 작성법

- **`Update` 객체 모의:** 사용자의 메시지, 커맨드(`context.args`), 콜백 쿼리(`update.callback_query`) 등 다양한 입력을 시뮬레이션하기 위해 `Update` 객체를 상세하게 모의해야 합니다.
- **API 호출 모의:** `unittest.mock.patch`를 사용하여 `httpx` 세션의 `get`, `post` 등의 메서드를 모의 처리하여 `api` 서비스의 응답을 시뮬레이션합니다. 이를 통해 `bot` 서비스 로직을 독립적으로 테스트할 수 있습니다.
- **응답 메시지 검증:** `update.message.reply_text`나 `update.callback_query.edit_message_text`와 같은 응답 함수가 올바른 인자(`chat_id`, `text`, `parse_mode` 등)와 함께 호출되었는지 `assert_called_once_with` 등으로 검증합니다.

## 4. Common 모듈 (`src/common`)

- 공통 모듈은 외부 의존성이 적으므로 전통적인 단위 테스트를 작성하기 용이합니다.
- 특히 `http_client.py`의 재시도 로직이나 `dart_utils.py`의 데이터 파싱 로직 등은 다양한 성공/실패 시나리오에 대해 독립적인 테스트를 통해 안정성을 검증해야 합니다.
