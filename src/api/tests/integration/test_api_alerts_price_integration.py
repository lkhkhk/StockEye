# src/api/tests/integration/test_api_alerts_price_integration.py
"""
API 통합 테스트: 봇 가격 알림 설정 API

이 파일은 `/bot/alert/price` 엔드포인트에 대한 통합 테스트를 포함합니다.
이 API는 텔레그램 봇의 특정 흐름(예: 자연어 처리)을 통해 가격 알림을 생성하거나
업데이트하는 데 사용될 것으로 보입니다. 특히 `repeat_interval` 필드의 처리를 검증합니다.

`TestClient`를 사용하여 API 요청을 보내고, `real_db` fixture를 통해 실제 데이터베이스와의
상호작용을 검증합니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.main import app
from src.common.database.db_connector import get_db
from src.common.models.user import User
from src.common.models.price_alert import PriceAlert


@pytest.fixture(scope="module")
def client():
    """
    모듈 범위의 `TestClient` Fixture.

    - **목적**: 테스트 모듈 전체에서 FastAPI 애플리케이션에 대한 요청을 보낼 수 있는
              하나의 클라이언트 인스턴스를 제공합니다.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def db_session(real_db):
    """
    함수 범위의 데이터베이스 세션 Fixture.

    - **목적**: 각 테스트 함수에 격리된 데이터베이스 세션을 제공합니다.
              `real_db` fixture로부터 세션을 받아 사용합니다.
    """
    # `real_db` fixture가 트랜잭션 관리 및 세션 닫기를 처리하므로,
    # 여기서는 세션을 전달하기만 합니다.
    yield real_db


@pytest.fixture(scope="function", autouse=True)
def override_get_db_dependency(db_session: Session):
    """
    `get_db` 의존성을 오버라이드하는 Fixture.

    - **목적**: API 라우터에서 사용하는 `get_db` 의존성을 테스트용 DB 세션으로 대체하여,
              API 호출이 테스트 데이터베이스를 사용하도록 합니다.
    - **적용**: `autouse=True`로 설정되어 이 모듈의 모든 테스트에 자동으로 적용됩니다.
    """
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    # 테스트 종료 후 오버라이드 해제
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_set_price_alert_for_bot_with_repeat_interval(client: TestClient, db_session: Session):
    """
    - **테스트 대상**: `POST /bot/alert/price`
    - **목적**: 봇을 통해 신규 가격 알림을 설정할 때, `repeat_interval` 필드가 올바르게 저장되는지 확인합니다.
    - **시나리오**:
        1. `repeat_interval`을 포함한 알림 생성 페이로드를 구성합니다.
        2. API를 호출하여 알림을 생성합니다.
        3. 200 OK 응답과 함께 반환된 데이터에 `repeat_interval`이 포함되어 있는지 확인합니다.
        4. 데이터베이스에 저장된 실제 데이터에도 `repeat_interval`이 올바르게 기록되었는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given: 테스트용 데이터 정의
    telegram_user_id = 12345
    symbol = "005930"
    payload = {
        "telegram_user_id": telegram_user_id,
        "telegram_username": "testuser",
        "telegram_first_name": "Test",
        "telegram_last_name": "User",
        "symbol": symbol,
        "target_price": 75000.0,
        "condition": "gte",
        "repeat_interval": "daily"
    }

    # When: API 호출
    response = client.post("/bot/alert/price", json=payload)

    # Then: API 응답 검증
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["repeat_interval"] == "daily"

    # Then: 데이터베이스 상태 검증
    user = db_session.query(User).filter(User.telegram_id == telegram_user_id).first()
    assert user is not None
    alert = db_session.query(PriceAlert).filter(PriceAlert.user_id == user.id, PriceAlert.symbol == symbol).first()
    assert alert is not None
    assert alert.repeat_interval == "daily"


@pytest.mark.asyncio
async def test_update_price_alert_for_bot_with_repeat_interval(client: TestClient, db_session: Session):
    """
    - **테스트 대상**: `POST /bot/alert/price` (업데이트 시나리오)
    - **목적**: 봇을 통해 기존 가격 알림을 업데이트할 때, `repeat_interval` 필드가 올바르게 변경되는지 확인합니다.
    - **시나리오**:
        1. `repeat_interval`이 없는 초기 알림을 생성합니다.
        2. `repeat_interval`을 포함한 페이로드로 동일한 심볼에 대해 다시 API를 호출하여 알림을 업데이트합니다.
        3. 200 OK 응답과 함께 반환된 데이터에 업데이트된 `repeat_interval`이 포함되어 있는지 확인합니다.
        4. 데이터베이스에 저장된 데이터도 올바르게 업데이트되었는지 확인합니다.
    - **Mock 대상**: 없음
    """
    # Given: 초기 알림 데이터 생성
    telegram_user_id = 12346
    symbol = "005930"
    initial_payload = {
        "telegram_user_id": telegram_user_id,
        "telegram_username": "testuser2",
        "telegram_first_name": "Test2",
        "telegram_last_name": "User2",
        "symbol": symbol,
        "target_price": 70000.0,
        "condition": "lte"
    }
    client.post("/bot/alert/price", json=initial_payload)

    # When: repeat_interval을 포함하여 업데이트 요청
    update_payload = {
        "telegram_user_id": telegram_user_id,
        "telegram_username": "testuser2",
        "telegram_first_name": "Test2",
        "telegram_last_name": "User2",
        "symbol": symbol,
        "target_price": 76000.0,
        "condition": "gte",
        "repeat_interval": "weekly"
    }
    response = client.post("/bot/alert/price", json=update_payload)

    # Then: API 응답 검증
    assert response.status_code == 200
    data = response.json()
    assert data["target_price"] == 76000.0
    assert data["repeat_interval"] == "weekly"

    # Then: 데이터베이스 상태 검증
    user = db_session.query(User).filter(User.telegram_id == telegram_user_id).first()
    alert = db_session.query(PriceAlert).filter(PriceAlert.user_id == user.id, PriceAlert.symbol == symbol).first()
    assert alert is not None
    assert alert.repeat_interval == "weekly"