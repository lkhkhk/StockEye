import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.common.db_connector import get_db
from src.api.models.user import User
from src.api.models.price_alert import PriceAlert

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def db_session(real_db):
    db = real_db
    try:
        yield db
    finally:
        # real_db fixture가 세션을 닫으므로 여기서는 닫지 않음
        pass

@pytest.fixture(scope="function", autouse=True)
def override_get_db_dependency(db_session: Session):
    # 각 테스트 함수가 시작될 때마다 get_db 의존성을 오버라이드
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides = {} # 테스트 종료 후 오버라이드 해제

@pytest.mark.asyncio
async def test_set_price_alert_for_bot_with_repeat_interval(client: TestClient, db_session: Session):
    """봇을 통해 가격 알림 설정 시 repeat_interval이 올바르게 저장되는지 테스트"""
    telegram_user_id = 12345
    symbol = "005930"
    target_price = 75000.0
    condition = "gte"
    repeat_interval = "daily"

    payload = {
        "telegram_user_id": telegram_user_id,
        "telegram_username": "testuser",
        "telegram_first_name": "Test",
        "telegram_last_name": "User",
        "symbol": symbol,
        "target_price": target_price,
        "condition": condition,
        "repeat_interval": repeat_interval
    }

    response = client.post("/bot/alert/price", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["target_price"] == target_price
    assert data["condition"] == condition
    assert data["repeat_interval"] == repeat_interval
    assert data["is_active"] == True

    # DB에서 직접 확인
    user = db_session.query(User).filter(User.telegram_id == telegram_user_id).first()
    assert user is not None

    alert = db_session.query(PriceAlert).filter(
        PriceAlert.user_id == user.id,
        PriceAlert.symbol == symbol
    ).first()
    assert alert is not None
    assert alert.target_price == target_price
    assert alert.condition == condition
    assert alert.repeat_interval == repeat_interval
    assert alert.is_active == True

@pytest.mark.asyncio
async def test_update_price_alert_for_bot_with_repeat_interval(client: TestClient, db_session: Session):
    """봇을 통해 기존 가격 알림 업데이트 시 repeat_interval이 올바르게 저장되는지 테스트"""
    telegram_user_id = 12346
    symbol = "005930"
    
    # 기존 알림 생성 (repeat_interval 없음)
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

    # repeat_interval을 포함하여 업데이트
    updated_target_price = 76000.0
    updated_condition = "gte"
    updated_repeat_interval = "weekly"

    update_payload = {
        "telegram_user_id": telegram_user_id,
        "telegram_username": "testuser2",
        "telegram_first_name": "Test2",
        "telegram_last_name": "User2",
        "symbol": symbol,
        "target_price": updated_target_price,
        "condition": updated_condition,
        "repeat_interval": updated_repeat_interval
    }

    response = client.post("/bot/alert/price", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["target_price"] == updated_target_price
    assert data["condition"] == updated_condition
    assert data["repeat_interval"] == updated_repeat_interval
    assert data["is_active"] == True

    # DB에서 직접 확인
    user = db_session.query(User).filter(User.telegram_id == telegram_user_id).first()
    assert user is not None

    alert = db_session.query(PriceAlert).filter(
        PriceAlert.user_id == user.id,
        PriceAlert.symbol == symbol
    ).first()
    assert alert is not None
    assert alert.target_price == updated_target_price
    assert alert.condition == updated_condition
    assert alert.repeat_interval == updated_repeat_interval
    assert alert.is_active == True
