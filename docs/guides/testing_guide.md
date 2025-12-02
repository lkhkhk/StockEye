# 테스트 코드 작성 가이드

이 문서는 StockEye 프로젝트의 테스트 코드를 작성하고 유지보수하기 위한 표준 가이드라인을 제공합니다. 모든 개발자는 새로운 기능 추가 및 코드 변경 시 이 가이드라인을 따라 테스트 코드를 작성해야 합니다.

## 1. 기본 원칙

*   **테스트는 독립적이어야 한다:** 각 테스트 함수는 다른 테스트에 영향을 주지 않고 독립적으로 실행될 수 있어야 합니다.
*   **테스트는 결정적이어야 한다:** 테스트는 실행할 때마다 항상 동일한 결과를 반환해야 합니다. (외부 API 호출, 현재 시간 등 비결정적 요소는 모의(Mock) 처리)
*   **테스트는 명확해야 한다:** 테스트 코드만 읽어도 어떤 시나리오를 검증하는지 명확하게 이해할 수 있어야 합니다. (Given-When-Then 패턴 사용 권장)
*   **커버리지를 높여라:** 새로 추가된 코드는 반드시 테스트 코드로 커버되어야 합니다.

## 2. API 서비스 테스트 (`src/api/tests/`)

`FastAPI`의 `TestClient`와 `pytest`를 사용하여 API 엔드포인트를 테스트합니다.

### 2.1. 테스트 환경 (`conftest.py`)

*   **DB 세션:** 모든 테스트는 `sqlite` 인메모리 DB를 사용합니다. `conftest.py`의 `db` fixture를 사용하여 함수마다 독립적인 트랜잭션을 보장하고, 테스트 종료 후 자동으로 롤백합니다.
*   **TestClient:** `client` fixture를 사용하여 `TestClient` 인스턴스를 생성하고, `get_db` 의존성을 테스트용 DB 세션으로 오버라이드합니다.

### 2.2. 테스트 헬퍼 함수 (`tests/helpers.py` - 신규 생성 권장)

반복적으로 사용되는 로직은 헬퍼 함수로 분리하여 재사용성을 높입니다.

**예시: 인증된 사용자 생성 및 토큰 발급**

```python
# src/api/tests/helpers.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from src.api.models import User
from src.api.services.auth_service import create_access_token

def create_test_user(db: Session, role: str = "user") -> User:
    """테스트용 사용자를 생성하고 DB에 저장합니다."""
    unique_id = uuid4().hex
    user = User(
        username=f"test_{unique_id}",
        email=f"test_{unique_id}@example.com",
        password_hash="hashed_password", # 실제 해싱 로직 사용 권장
        role=role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_auth_headers(user: User) -> dict[str, str]:
    """사용자 객체로부터 인증 헤더를 생성합니다."""
    token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"Authorization": f"Bearer {token}"}
```

### 2.3. 라우터 테스트 작성법

*   **파일 구조:** `test_api_[router_name].py` 형식으로 파일을 생성합니다.
*   **Given-When-Then 패턴:** 테스트의 가독성을 위해 이 구조를 따릅니다.
*   **상세한 검증:** `status_code` 뿐만 아니라, 응답 본문의 구조와 데이터 타입까지 상세하게 검증합니다.
*   **인증/인가 테스트:** `@pytest.mark.parametrize`를 사용하여 다양한 사용자 역할(admin, user, unauthenticated)에 따른 접근 제어를 검증합니다.

**예시: `watchlist` 라우터 테스트**

```python
# src/api/tests/test_api_watchlist.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.tests.helpers import create_test_user, get_auth_headers
from src.api.schemas.watchlist import WatchlistResponse # 응답 검증용 스키마


def test_add_to_watchlist_success(client: TestClient, db: Session):
    # Given: 인증된 사용자 생성
    user = create_test_user(db)
    headers = get_auth_headers(user)
    symbol_to_add = "005930"

    # When: 관심 종목 추가 API 호출
    response = client.post("/watchlist/", json={"symbol": symbol_to_add}, headers=headers)

    # Then: 성공적으로 추가되었는지 검증
    assert response.status_code == 201 # Created
    data = response.json()
    assert data["symbol"] == symbol_to_add
    assert data["user_id"] == user.id

def test_get_watchlist_unauthenticated(client: TestClient):
    # Given: 인증되지 않은 사용자
    # When: 관심 종목 조회 API 호출
    response = client.get("/watchlist/")

    # Then: 401 Unauthorized 응답 확인
    assert response.status_code == 401


def test_get_watchlist_returns_correct_schema(client: TestClient, db: Session):
    # Given: 데이터가 있는 사용자
    user = create_test_user(db)
    headers = get_auth_headers(user)
    client.post("/watchlist/", json={"symbol": "005930"}, headers=headers)
    client.post("/watchlist/", json={"symbol": "035720"}, headers=headers)

    # When: 관심 종목 조회
    response = client.get("/watchlist/", headers=headers)

    # Then: 응답 스키마 검증
    assert response.status_code == 200
    # Pydantic 모델로 응답 데이터 유효성 검사
    watchlist_response = WatchlistResponse.parse_obj(response.json())
    assert len(watchlist_response.watchlist) == 2
    assert isinstance(watchlist_response.watchlist[0].symbol, str)
```

## 3. 봇 핸들러 테스트 (`src/bot/tests/`)

`python-telegram-bot`의 `ApplicationBuilder`와 `pytest.mark.asyncio`를 사용하여 비동기 핸들러를 테스트합니다.

### 3.1. 테스트 구조

*   **비동기 테스트:** 모든 테스트 함수는 `async def`로 선언하고 `@pytest.mark.asyncio` 데코레이터를 붙입니다.
*   **Mock 객체 사용:** `unittest.mock.AsyncMock`을 사용하여 `telegram.Update`, `telegram.ext.ContextTypes` 등 텔레그램 객체와 외부 API 호출(`httpx.AsyncClient`)을 모의합니다.
*   **파일 구조:** `test_[handler_name]_handler.py` 형식으로 파일을 생성합니다.

### 3.2. 핸들러 테스트 작성법

*   **`Update` 객체 모의:** 사용자의 메시지, 커맨드, 콜백 쿼리 등 다양한 입력을 시뮬레이션하기 위해 `Update` 객체를 상세하게 모의합니다.
*   **`Context` 객체 모의:** `context.args`, `context.user_data` 등 핸들러가 사용하는 `Context` 객체의 속성을 설정합니다.
*   **API 호출 모의:** `pytest-mock`의 `mocker` fixture나 `unittest.mock.patch`를 사용하여 `httpx` 호출 결과를 모의합니다.
*   **응답 메시지 검증:** `update.message.reply_text`나 `update.callback_query.edit_message_text`와 같은 응답 함수가 올바른 인자와 함께 호출되었는지 검증합니다.

**예시: `/watchlist` 명령어 핸들러 테스트**

```python
# src/bot/tests/test_watchlist_handler.py
import pytest
from unittest.mock import AsyncMock, patch

from src.bot.handlers.watchlist import show_watchlist, add_to_watchlist_callback

@pytest.mark.asyncio
async def test_show_watchlist_success():
    # Given: API가 성공적으로 응답하는 상황
    update = AsyncMock()
    context = AsyncMock()
    update.effective_user.id = 12345
    update.message.reply_text = AsyncMock()

    mock_api_response = {
        "watchlist": [
            {"symbol": "005930", "name": "삼성전자"},
            {"symbol": "035720", "name": "카카오"}
        ]
    }

    with patch("src.bot.handlers.watchlist.session.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_api_response

        # When: 핸들러 호출
        await show_watchlist(update, context)

        # Then: API 호출 및 응답 메시지 검증
        mock_get.assert_called_once_with(f"http://api:8000/watchlist/{update.effective_user.id}")
        update.message.reply_text.assert_called_once()
        sent_message = update.message.reply_text.call_args[0][0]
        assert "관심 종목 목록" in sent_message
        assert "- 삼성전자 (005930)" in sent_message
        assert "- 카카오 (035720)" in sent_message

@pytest.mark.asyncio
async def test_add_to_watchlist_callback():
    # Given: 사용자가 인라인 버튼을 클릭한 상황
    update = AsyncMock()
    context = AsyncMock()
    update.effective_user.id = 12345
    update.callback_query = AsyncMock()
    update.callback_query.data = "watchlist_add:005930" # 콜백 데이터 모의
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    with patch("src.bot.handlers.watchlist.session.post") as mock_post:
        mock_post.return_value.status_code = 201

        # When: 콜백 핸들러 호출
        await add_to_watchlist_callback(update, context)

        # Then: API 호출 및 응답 메시지 검증
        mock_post.assert_called_once()
        update.callback_query.answer.assert_called_once_with("관심 종목에 추가되었습니다.")
        update.callback_query.edit_message_text.assert_called_once()
```

## 4. Common 모듈 테스트 (`src/common/tests/`)

공통 모듈은 외부 의존성이 적어 전통적인 단위 테스트를 작성하기 용이합니다.

**예시: `http_client` 재시도 로직 테스트**

```python
# src/common/tests/test_http_client.py
import pytest
import httpx
from unittest.mock import patch, MagicMock

from src.common.http_client import requests_retry_session

@patch("httpx.Session.get")
def test_retry_session_success_on_first_try(mock_get):
    # Given: 첫 시도에 성공하는 경우
    mock_get.return_value = MagicMock(status_code=200)
    session = requests_retry_session()

    # When: GET 요청
    response = session.get("http://test.com")

    # Then: 한 번만 호출되고 성공 응답 반환
    mock_get.assert_called_once()
    assert response.status_code == 200

@patch("httpx.Session.get")
def test_retry_session_retries_on_5xx_and_succeeds(mock_get):
    # Given: 503 에러 후 성공하는 경우
    mock_get.side_effect = [
        httpx.Response(503, content=b'Service Unavailable'),
        httpx.Response(200, content=b'OK')
    ]
    session = requests_retry_session(retries=3)

    # When: GET 요청
    response = session.get("http://test.com")

    # Then: 두 번 호출되고 성공 응답 반환
    assert mock_get.call_count == 2
    assert response.status_code == 200
```