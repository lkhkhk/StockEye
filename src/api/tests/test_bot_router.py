from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.api.models.user import User
from src.api.models.price_alert import PriceAlert
from src.api.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
from src.api.services.user_service import UserService
from src.api.services.price_alert_service import PriceAlertService
import pytest
from unittest.mock import patch
from datetime import datetime

client = TestClient(app)

@pytest.fixture(name="test_price_alert")
def test_price_alert_fixture(db: Session, test_user: User):
    price_alert_service = PriceAlertService()
    alert_data = PriceAlertCreate(
        symbol="AAPL",
        target_price=150.0,
        condition="above",
        notify_on_disclosure=False
    )
    alert = price_alert_service.create_alert(db, user_id=test_user.id, alert=alert_data)
    yield alert

def test_toggle_disclosure_alert_new_user_and_alert(db: Session, test_user: User):
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

def test_toggle_disclosure_alert_existing_user_new_alert(db: Session, test_user: User):
    symbol = "MSFT"
    response = client.post(
        "/bot/alert/disclosure-toggle",
        json={"telegram_user_id": test_user.telegram_id, "symbol": symbol}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["notify_on_disclosure"] is True

@patch('src.api.services.user_service.UserService.get_user_by_telegram_id')
@patch('src.api.services.price_alert_service.PriceAlertService.get_alert_by_user_and_symbol')
@patch('src.api.services.price_alert_service.PriceAlertService.update_alert')
def test_toggle_disclosure_alert_existing_alert_on_to_off(
    mock_update_alert, mock_get_alert_by_user_and_symbol, mock_get_user_by_telegram_id, db: Session, test_user: User
):
    # Create an initial alert with notify_on_disclosure=True directly in DB
    initial_alert = PriceAlert(
            user_id=test_user.id,
            symbol="AMZN",
            is_active=True,
            notify_on_disclosure=True
        )
    db.add(initial_alert)
    db.flush()
    db.refresh(initial_alert)
    assert initial_alert.notify_on_disclosure is True

    # Mock the service calls
    mock_get_user_by_telegram_id.return_value = test_user
    mock_get_alert_by_user_and_symbol.return_value = initial_alert
    mock_update_alert.return_value = PriceAlert(
        id=1, # 더미 ID 추가
        user_id=test_user.id,
        symbol="AMZN",
        is_active=True,
        notify_on_disclosure=False, # Expected toggled state
        created_at=datetime.now(), # 더미 created_at 추가
        updated_at=datetime.now() # 더미 updated_at 추가
    )

    response = client.post(
        "/bot/alert/disclosure-toggle",
        json={"telegram_user_id": test_user.telegram_id, "symbol": initial_alert.symbol}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == initial_alert.symbol
    assert data["notify_on_disclosure"] is False

def test_toggle_disclosure_alert_existing_alert_off_to_on(db: Session, test_user: User):
    # Create an initial alert with notify_on_disclosure=False directly in DB
    initial_alert = PriceAlert(
        user_id=test_user.id,
        symbol="NFLX",
        target_price=10.0,
        condition="above",
        notify_on_disclosure=False,
        is_active=True
    )
    db.add(initial_alert)
    db.flush()
    db.refresh(initial_alert)
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

def test_set_price_alert_existing_user_new_alert(db: Session, test_user: User):
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

def test_set_price_alert_existing_alert_update(db: Session, test_user: User):
    # Create an initial price alert directly in DB
    initial_alert = PriceAlert(
        user_id=test_user.id,
        symbol="GOOGL",
        target_price=100.0,
        condition="above",
        is_active=False
    )
    db.add(initial_alert)
    db.flush()
    db.refresh(initial_alert)
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

def test_set_price_alert_only_updates_price_related_fields(db: Session, test_user: User):
    # Create an initial alert with disclosure notification enabled directly in DB
    initial_alert = PriceAlert(
        user_id=test_user.id,
        symbol="FB",
        notify_on_disclosure=True,
        is_active=True
    )
    db.add(initial_alert)
    db.flush()
    db.refresh(initial_alert)
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
