from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.common.models.user import User
from src.common.models.price_alert import PriceAlert
from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
from src.api.services.user_service import UserService
from src.common.services.price_alert_service import PriceAlertService
from src.common.db_connector import get_db # get_db 임포트 추가
from src.api.routers.bot_router import get_user_service, get_price_alert_service # 의존성 주입 함수 임포트
import pytest
from unittest.mock import patch
from datetime import datetime

client = TestClient(app)

@pytest.fixture(name="test_price_alert")
@pytest.mark.asyncio
async def test_price_alert_fixture(real_db: Session, test_user: User):
    price_alert_service = PriceAlertService()
    alert_data = PriceAlertCreate(
        symbol="AAPL",
        target_price=150.0,
        condition="above",
        notify_on_disclosure=False
    )
    alert = await price_alert_service.create_alert(real_db, user_id=test_user.id, alert=alert_data)
    yield alert

@pytest.fixture(scope="function", autouse=True)
def override_bot_router_dependencies(real_db: Session):
    pass


@pytest.mark.asyncio
async def test_toggle_disclosure_alert_new_user_and_alert(real_db: Session, test_user: User):
    telegram_id = test_user.telegram_id
    symbol = "GOOG"
    response = client.post(
        "/bot/alert/disclosure-toggle",
        json={"telegram_user_id": telegram_id, "telegram_username": test_user.username, "symbol": symbol}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["notify_on_disclosure"] is True
    assert data["target_price"] is None
    assert data["condition"] is None

def test_toggle_disclosure_alert_existing_user_new_alert(real_db: Session, test_user: User):
    symbol = "MSFT"
    response = client.post(
        "/bot/alert/disclosure-toggle",
        json={"telegram_user_id": test_user.telegram_id, "symbol": symbol}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["notify_on_disclosure"] is True

@pytest.mark.asyncio
async def test_toggle_disclosure_alert_existing_alert_on_to_off(real_db: Session, test_user: User):
    # Create an initial alert with notify_on_disclosure=True using the service
    price_alert_service = PriceAlertService()
    initial_alert = await price_alert_service.create_alert(
        real_db,
        user_id=test_user.id,
        alert=PriceAlertCreate(
            symbol="AMZN",
            notify_on_disclosure=True,
            is_active=True
        )
    )
    assert initial_alert.notify_on_disclosure is True

    response = client.post(
        "/bot/alert/disclosure-toggle",
        json={"telegram_user_id": test_user.telegram_id, "symbol": initial_alert.symbol}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == initial_alert.symbol
    assert data["notify_on_disclosure"] is False

    # Verify alert is updated in DB
    updated_alert_in_db = real_db.query(PriceAlert).filter(PriceAlert.id == initial_alert.id).first()
    assert updated_alert_in_db.notify_on_disclosure is False

@pytest.mark.asyncio
async def test_toggle_disclosure_alert_existing_alert_off_to_on(real_db: Session, test_user: User):
    # Create an initial alert with notify_on_disclosure=False using the service
    price_alert_service = PriceAlertService()
    initial_alert = await price_alert_service.create_alert(
        real_db,
        user_id=test_user.id,
        alert=PriceAlertCreate(
            symbol="NFLX",
            target_price=10.0,
            condition="above",
            notify_on_disclosure=False,
            is_active=True
        )
    )
    # db.add(initial_alert)
    # db.flush()
    # db.refresh(initial_alert)
    assert initial_alert.notify_on_disclosure is False

    response = client.post(
        "/bot/alert/disclosure-toggle",
        json={"telegram_user_id": test_user.telegram_id, "symbol": initial_alert.symbol}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == initial_alert.symbol
    assert data["notify_on_disclosure"] is True
    assert data["is_active"] is True

@pytest.mark.asyncio
async def test_set_price_alert_existing_user_new_alert(real_db: Session, test_user: User):
    symbol = "NVDA"
    target_price = 1000.0
    condition = "below"
    response = client.post(
        "/bot/alert/price",
        json={
            "telegram_user_id": test_user.telegram_id,
            "telegram_username": test_user.username,
            "symbol": symbol,
            "target_price": target_price,
            "condition": condition
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["target_price"] == target_price
    assert data["condition"] == condition
    assert data["is_active"] is True

@pytest.mark.asyncio
async def test_set_price_alert_existing_alert_update(real_db: Session, test_user: User):
    # Create an initial price alert using the service
    price_alert_service = PriceAlertService()
    initial_alert = await price_alert_service.create_alert(
        real_db,
        user_id=test_user.id,
        alert=PriceAlertCreate(
            symbol="GOOGL",
            target_price=100.0,
            condition="above",
            is_active=False
        )
    )
    # db.add(initial_alert)
    # db.flush()
    # db.refresh(initial_alert)
    assert initial_alert.target_price == 100.0
    assert initial_alert.condition == "above"
    assert initial_alert.is_active is False

    # Update the alert
    new_target_price = 110.0
    new_condition = "below"
    new_repeat_interval = "weekly"
    response = client.post(
        "/bot/alert/price",
        json={
            "telegram_user_id": test_user.telegram_id,
            "symbol": "GOOGL",
            "target_price": new_target_price,
            "condition": new_condition,
            "repeat_interval": new_repeat_interval
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "GOOGL"
    assert data["target_price"] == new_target_price
    assert data["condition"] == new_condition
    assert data["repeat_interval"] == new_repeat_interval
    assert data["is_active"] is True # Should become active

@pytest.mark.asyncio
async def test_set_price_alert_only_updates_price_related_fields(real_db: Session, test_user: User):
    # Create an initial alert with disclosure notification enabled using the service
    price_alert_service = PriceAlertService()
    initial_alert = await price_alert_service.create_alert(
        real_db,
        user_id=test_user.id,
        alert=PriceAlertCreate(
            symbol="FB",
            notify_on_disclosure=True,
            is_active=True
        )
    )
    # db.add(initial_alert)
    # db.flush()
    # db.refresh(initial_alert)
    assert initial_alert.notify_on_disclosure is True
    assert initial_alert.target_price is None

    # Set a price alert for the same symbol
    new_target_price = 300.0
    new_condition = "above"
    response = client.post(
        "/bot/alert/price",
        json={
            "telegram_user_id": test_user.telegram_id,
            "symbol": "FB",
            "target_price": new_target_price,
            "condition": new_condition
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "FB"
    assert data["target_price"] == new_target_price
    assert data["condition"] == new_condition
    assert data["notify_on_disclosure"] is True # Should remain True

@pytest.mark.asyncio
async def test_list_alerts_for_bot(real_db: Session, test_user: User):
    # Create some alerts for the test user
    price_alert_service = PriceAlertService()
    alert1 = await price_alert_service.create_alert(real_db, user_id=test_user.id, alert=PriceAlertCreate(symbol="AAPL", target_price=150.0, condition="above"))
    alert2 = await price_alert_service.create_alert(real_db, user_id=test_user.id, alert=PriceAlertCreate(symbol="GOOG", notify_on_disclosure=True))

    response = client.post(
        "/bot/alert/list",
        json={"telegram_user_id": test_user.telegram_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(a["symbol"] == "AAPL" for a in data)
    assert any(a["symbol"] == "GOOG" for a in data)

def test_list_alerts_for_bot_no_alerts(real_db: Session, test_user: User):
    response = client.post(
        "/bot/alert/list",
        json={"telegram_user_id": test_user.telegram_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

def test_list_alerts_for_bot_user_not_found(real_db: Session):
    response = client.post(
        "/bot/alert/list",
        json={"telegram_user_id": 99999}
    )
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_remove_alert_for_bot_success(real_db: Session, test_user: User):
    price_alert_service = PriceAlertService()
    alert = await price_alert_service.create_alert(real_db, user_id=test_user.id, alert=PriceAlertCreate(symbol="TEST", target_price=100.0, condition="above"))

    response = client.post(
        "/bot/alert/remove",
        json={"telegram_user_id": test_user.telegram_id, "alert_id": alert.id}
    )
    assert response.status_code == 200
    assert response.json()["message"] == f"Alert {alert.id} removed successfully"

    # Verify alert is deleted from DB
    # deleted_alert = price_alert_service.get_alert_by_id(real_db, alert.id)
    # assert deleted_alert is None
    # API를 통해 알림 목록을 다시 조회하여 삭제 여부 확인
    list_response = client.post(
        "/bot/alert/list",
        json={"telegram_user_id": test_user.telegram_id}
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 0

def test_remove_alert_for_bot_not_found(real_db: Session):
    response = client.post(
        "/bot/alert/remove",
        json={"telegram_user_id": 99999999999, "alert_id": 99999}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

@pytest.mark.asyncio
async def test_remove_alert_for_bot_unauthorized(real_db: Session, test_user: User):
    # Create an alert for a different user
    other_user = User(telegram_id=9876543210, username="other_user", password_hash="hashed_password")
    real_db.add(other_user)
    real_db.commit()
    real_db.refresh(other_user)

    price_alert_service = PriceAlertService()
    alert = await price_alert_service.create_alert(real_db, user_id=other_user.id, alert=PriceAlertCreate(symbol="OTHER", target_price=50.0, condition="below"))

    response = client.post(
        "/bot/alert/remove",
        json={"telegram_user_id": test_user.telegram_id, "alert_id": alert.id}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found or not authorized"

@pytest.mark.asyncio
async def test_deactivate_alert_for_bot_success(real_db: Session, test_user: User):
    price_alert_service = PriceAlertService()
    alert = await price_alert_service.create_alert(real_db, user_id=test_user.id, alert=PriceAlertCreate(symbol="DEACT", target_price=200.0, condition="above", is_active=True))

    response = client.post(
        "/bot/alert/deactivate",
        json={"telegram_user_id": test_user.telegram_id, "alert_id": alert.id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == alert.id
    assert data["is_active"] is False

    # Verify alert is deactivated in DB
    deactivated_alert = price_alert_service.get_alert_by_id(real_db, alert.id)
    assert deactivated_alert.is_active is False

def test_deactivate_alert_for_bot_not_found(real_db: Session):
    response = client.post(
        "/bot/alert/deactivate",
        json={"telegram_user_id": 99999999999, "alert_id": 99999}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

@pytest.mark.asyncio
async def test_deactivate_alert_for_bot_unauthorized(real_db: Session, test_user: User):
    # Create an alert for a different user
    other_user = User(telegram_id=1234567890, username="another_user", password_hash="hashed_password")
    real_db.add(other_user)
    real_db.commit()
    real_db.refresh(other_user)

    price_alert_service = PriceAlertService()
    alert = await price_alert_service.create_alert(real_db, user_id=other_user.id, alert=PriceAlertCreate(symbol="ANOTHER", target_price=300.0, condition="below", is_active=True))

    response = client.post(
        "/bot/alert/deactivate",
        json={"telegram_user_id": test_user.telegram_id, "alert_id": alert.id}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found or not authorized"
