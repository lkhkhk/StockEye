import pytest
from unittest.mock import patch
from fastapi import HTTPException, status
import datetime

from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
from src.common.tests.unit.conftest import TestUser, TestPriceAlert, TestStockMaster

# Test cases for create_alert
@pytest.mark.asyncio
async def test_create_alert_success(db_session, price_alert_service):
    # Create a user and a stock for the alert
    user = TestUser(id=1, username="testuser", email="test@example.com", hashed_password="hashedpassword")
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add_all([user, stock])
    db_session.commit()
    db_session.refresh(user)

    alert_data = PriceAlertCreate(symbol="AAPL", target_price=150.0, condition="gte")
    alert = await price_alert_service.create_alert(db_session, user.id, alert_data)

    assert alert.user_id == user.id
    assert alert.symbol == "AAPL"
    assert alert.target_price == 150.0
    assert alert.condition == "gte"
    assert alert.is_active is True
    assert isinstance(alert.created_at, datetime.datetime)

    db_alert = db_session.query(TestPriceAlert).filter_by(id=alert.id).first()
    assert db_alert is not None
    assert db_alert.symbol == "AAPL"

# Test cases for get_alerts
def test_get_alerts_success(db_session, price_alert_service):
    # Add some test alerts
    user1 = TestUser(id=1, username="user1")
    user2 = TestUser(id=2, username="user2")
    stock1 = TestStockMaster(symbol="AAPL", name="Apple")
    stock2 = TestStockMaster(symbol="GOOG", name="Google")
    stock3 = TestStockMaster(symbol="MSFT", name="Microsoft")
    db_session.add_all([user1, user2, stock1, stock2, stock3])
    db_session.commit()

    alert1 = TestPriceAlert(user_id=1, symbol="AAPL", target_price=150.0, condition="gte")
    alert2 = TestPriceAlert(user_id=1, symbol="GOOG", change_percent=5.0, change_type="up")
    alert3 = TestPriceAlert(user_id=2, symbol="MSFT", target_price=300.0, condition="lte")
    db_session.add_all([alert1, alert2, alert3])
    db_session.commit()

    alerts = price_alert_service.get_alerts(db_session, 1)
    assert len(alerts) == 2
    assert alerts[0].symbol in ["AAPL", "GOOG"]
    assert alerts[1].symbol in ["AAPL", "GOOG"]

    alerts_user2 = price_alert_service.get_alerts(db_session, 2)
    assert len(alerts_user2) == 1
    assert alerts_user2[0].symbol == "MSFT"

def test_get_alerts_empty(db_session, price_alert_service):
    alerts = price_alert_service.get_alerts(db_session, 999)
    assert len(alerts) == 0

# Test cases for get_alert_by_user_and_symbol
def test_get_alert_by_user_and_symbol_found(db_session, price_alert_service):
    user = TestUser(id=1, username="testuser")
    stock = TestStockMaster(symbol="AAPL", name="Apple")
    db_session.add_all([user, stock])
    db_session.commit()
    alert = TestPriceAlert(user_id=1, symbol="AAPL", target_price=150.0, condition="gte")
    db_session.add(alert)
    db_session.commit()

    found_alert = price_alert_service.get_alert_by_user_and_symbol(db_session, 1, "AAPL")
    assert found_alert is not None
    assert found_alert.symbol == "AAPL"

def test_get_alert_by_user_and_symbol_not_found(db_session, price_alert_service):
    found_alert = price_alert_service.get_alert_by_user_and_symbol(db_session, 1, "NONEXISTENT")
    assert found_alert is None

# Test cases for get_alert_by_id
def test_get_alert_by_id_found(db_session, price_alert_service):
    user = TestUser(id=1, username="testuser")
    stock = TestStockMaster(symbol="AAPL", name="Apple")
    db_session.add_all([user, stock])
    db_session.commit()
    alert = TestPriceAlert(user_id=1, symbol="AAPL", target_price=150.0, condition="gte")
    db_session.add(alert)
    db_session.commit()

    found_alert = price_alert_service.get_alert_by_id(db_session, alert.id)
    assert found_alert is not None
    assert found_alert.id == alert.id

def test_get_alert_by_id_not_found(db_session, price_alert_service):
    found_alert = price_alert_service.get_alert_by_id(db_session, 999)
    assert found_alert is None

# Test cases for get_all_active_alerts
def test_get_all_active_alerts(db_session, price_alert_service):
    user1 = TestUser(id=1, username="user1")
    user2 = TestUser(id=2, username="user2")
    stock1 = TestStockMaster(symbol="AAPL", name="Apple")
    stock2 = TestStockMaster(symbol="GOOG", name="Google")
    stock3 = TestStockMaster(symbol="MSFT", name="Microsoft")
    db_session.add_all([user1, user2, stock1, stock2, stock3])
    db_session.commit()

    alert1 = TestPriceAlert(user_id=user1.id, symbol="AAPL", is_active=True)
    alert2 = TestPriceAlert(user_id=user2.id, symbol="GOOG", is_active=False)
    alert3 = TestPriceAlert(user_id=user1.id, symbol="MSFT", is_active=True)
    db_session.add_all([alert1, alert2, alert3])
    db_session.commit()

    active_alerts = price_alert_service.get_all_active_alerts(db_session)
    assert len(active_alerts) == 2
    assert all(alert.is_active for alert in active_alerts)
    assert {alert.symbol for alert in active_alerts} == {"AAPL", "MSFT"}
    assert active_alerts[0].user.username in ["user1", "user2"]

# Test cases for update_alert
@pytest.mark.asyncio
async def test_update_alert_success(db_session, price_alert_service):
    user = TestUser(id=1, username="testuser")
    stock = TestStockMaster(symbol="AAPL", name="Apple")
    db_session.add_all([user, stock])
    db_session.commit()
    alert = TestPriceAlert(user_id=1, symbol="AAPL", target_price=150.0, condition="gte")
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    update_data = PriceAlertUpdate(target_price=160.0, is_active=False)
    updated_alert = await price_alert_service.update_alert(db_session, alert.id, update_data)

    assert updated_alert.target_price == 160.0
    assert updated_alert.is_active is False
    assert updated_alert.updated_at >= alert.updated_at

    db_alert = db_session.query(TestPriceAlert).filter_by(id=alert.id).first()
    assert db_alert.target_price == 160.0
    assert db_alert.is_active is False

@pytest.mark.asyncio
async def test_update_alert_not_found(db_session, price_alert_service):
    update_data = PriceAlertUpdate(target_price=160.0)
    with pytest.raises(HTTPException) as exc_info:
        await price_alert_service.update_alert(db_session, 999, update_data)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Alert not found" in exc_info.value.detail

# Test cases for delete_alert
@pytest.mark.asyncio
async def test_delete_alert_success(db_session, price_alert_service):
    user = TestUser(id=1, username="testuser")
    stock = TestStockMaster(symbol="AAPL", name="Apple")
    db_session.add_all([user, stock])
    db_session.commit()
    alert = TestPriceAlert(user_id=1, symbol="AAPL", target_price=150.0, condition="gte")
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    alert_id = alert.id

    await price_alert_service.delete_alert(db_session, alert_id)

    assert db_session.query(TestPriceAlert).filter_by(id=alert_id).first() is None

@pytest.mark.asyncio
async def test_delete_alert_not_found(db_session, price_alert_service):
    with pytest.raises(HTTPException) as exc_info:
        await price_alert_service.delete_alert(db_session, 999)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Alert not found" in exc_info.value.detail
