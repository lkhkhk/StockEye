import pytest
import json
import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from src.common.tests.unit.conftest import TestUser, TestStockMaster, TestPriceAlert, TestDailyPrice
from src.common.services.price_alert_service import PriceAlertService
from src.common.models.stock_master import StockMaster
from src.common.models.user import User
from src.common.models.price_alert import PriceAlert
import logging

@pytest.fixture
def price_alert_service():
    return PriceAlertService()

# Test cases for check_and_notify_price_alerts
@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_price_alerts_no_active_alerts(mock_send_telegram, db_session, price_alert_service):
    await price_alert_service.check_and_notify_price_alerts(db_session)
    mock_send_telegram.assert_not_called()

@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_price_alerts_target_price_above_triggered(mock_send_telegram, db_session, price_alert_service):
    # Setup: active alert, user, stock, and daily price
    user = TestUser(id=1, username="testuser", email="test@example.com", hashed_password="hashedpassword", telegram_id=123)
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add_all([user, stock])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(stock)

    alert = TestPriceAlert(user_id=user.id, symbol="AAPL", target_price=150.0, condition="above", is_active=True, notify_on_disclosure=False)
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    daily_price = TestDailyPrice(symbol="AAPL", date=datetime.date.today(), open=140.0, high=160.0, low=140.0, close=155.0, volume=1000000)
    db_session.add(daily_price)
    db_session.commit()

    # Run the check
    await price_alert_service.check_and_notify_price_alerts(db_session)

    # Assertions
    mock_send_telegram.assert_called_once()
    call_args = mock_send_telegram.call_args[0]
    assert call_args[0] == user.telegram_id
    assert "Apple Inc." in call_args[1]
    assert "150.0원 이상으로 상승" in call_args[1]
    assert "현재가: 155.0원" in call_args[1]

    # Check if notification time is updated
    db_session.refresh(alert)
    assert alert.last_notified_at is not None


@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_price_alerts_target_price_below_triggered(mock_send_telegram, db_session, price_alert_service):
    # Setup: active alert, user, stock, and daily price
    user = TestUser(id=1, username="testuser", email="test@example.com", hashed_password="hashedpassword", telegram_id=123)
    stock = TestStockMaster(symbol="GOOG", name="Google Inc.")
    db_session.add_all([user, stock])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(stock)

    alert = TestPriceAlert(user_id=user.id, symbol="GOOG", target_price=2000.0, condition="below", is_active=True, notify_on_disclosure=False)
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    daily_price = TestDailyPrice(symbol="GOOG", date=datetime.date.today(), open=2100.0, high=2100.0, low=1950.0, close=1980.0, volume=500000)
    db_session.add(daily_price)
    db_session.commit()

    # Run the check
    await price_alert_service.check_and_notify_price_alerts(db_session)

    # Assertions
    mock_send_telegram.assert_called_once()
    call_args = mock_send_telegram.call_args[0]
    assert call_args[0] == user.telegram_id
    assert "Google Inc." in call_args[1]
    assert "2000.0원 이하로 하락" in call_args[1]
    assert "현재가: 1980.0원" in call_args[1]

    # Check if notification time is updated
    db_session.refresh(alert)
    assert alert.last_notified_at is not None

@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_price_alerts_target_price_not_triggered(mock_send_telegram, db_session, price_alert_service):
    # Setup: active alert, user, stock, and daily price (condition not met)
    user = TestUser(id=1, username="testuser", email="test@example.com", hashed_password="hashedpassword", telegram_id=123)
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add_all([user, stock])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(stock)

    alert = TestPriceAlert(user_id=user.id, symbol="AAPL", target_price=150.0, condition="above", is_active=True, notify_on_disclosure=False)
    db_session.add(alert)
    db_session.commit()

    daily_price = TestDailyPrice(symbol="AAPL", date=datetime.date.today(), open=140.0, high=145.0, low=135.0, close=145.0, volume=1000000)
    db_session.add(daily_price)
    db_session.commit()

    # Run the check
    await price_alert_service.check_and_notify_price_alerts(db_session)

    # Assertions
    mock_send_telegram.assert_not_called()
    db_session.refresh(alert)
    assert alert.is_active is True # Should remain active

@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_price_alerts_with_repeat_interval(mock_send_telegram, db_session, price_alert_service):
    # Setup: active alert with repeat_interval, user, stock
    user = TestUser(id=1, username="testuser", email="test@example.com", hashed_password="hashedpassword", telegram_id=123)
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add_all([user, stock])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(stock)

    alert = TestPriceAlert(user_id=user.id, symbol="AAPL", target_price=150.0, condition="above", is_active=True, notify_on_disclosure=False, notification_interval_hours=1)
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    daily_price = TestDailyPrice(symbol="AAPL", date=datetime.date.today(), open=140.0, high=160.0, low=140.0, close=155.0, volume=1000000)
    db_session.add(daily_price)
    db_session.commit()

    # Run the check
    await price_alert_service.check_and_notify_price_alerts(db_session)

    # Assertions
    mock_send_telegram.assert_called_once()
    db_session.refresh(alert)
    assert alert.is_active is True # Should remain active because of repeat_interval

@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_price_alerts_no_current_price(mock_send_telegram, db_session, price_alert_service):
    # Setup: active alert, user, but no daily price for the symbol
    user = TestUser(id=1, username="testuser", email="test@example.com", hashed_password="hashedpassword", telegram_id=123)
    stock = TestStockMaster(symbol="NONEXISTENT", name="Nonexistent Inc.") # Add stock master for nonexistent symbol
    db_session.add_all([user, stock])
    db_session.commit()
    db_session.refresh(user)

    alert = TestPriceAlert(user_id=user.id, symbol="NONEXISTENT", target_price=100.0, condition="above", is_active=True, notify_on_disclosure=False)
    db_session.add(alert)
    db_session.commit()

    # Run the check
    await price_alert_service.check_and_notify_price_alerts(db_session)

    # Assertions
    mock_send_telegram.assert_not_called()
    db_session.refresh(alert)
    assert alert.is_active is True # Should remain active

@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_price_alerts_change_percent_up_triggered(mock_send_telegram, db_session, price_alert_service):
    # Setup: active alert for percentage increase, user, stock, and daily prices
    user = TestUser(id=1, username="testuser", email="test@example.com", hashed_password="hashedpassword", telegram_id=123)
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add_all([user, stock])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(stock)

    alert = TestPriceAlert(user_id=user.id, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, notify_on_disclosure=False)
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    # Previous day's price
    prev_date = datetime.date.today() - datetime.timedelta(days=1)
    prev_price = TestDailyPrice(symbol="AAPL", date=prev_date, open=100.0, high=100.0, low=100.0, close=100.0, volume=1000000)
    # Current day's price (6% increase)
    current_price = TestDailyPrice(symbol="AAPL", date=datetime.date.today(), open=105.0, high=107.0, low=104.0, close=106.0, volume=1200000)
    db_session.add_all([prev_price, current_price])
    db_session.commit()

    # Run the check
    await price_alert_service.check_and_notify_price_alerts(db_session)

    # Assertions
    mock_send_telegram.assert_called_once()
    call_args = mock_send_telegram.call_args[0]
    assert call_args[0] == user.telegram_id
    assert "변동률 도달" in call_args[1]
    assert "5.0% up" in call_args[1]
    assert "6.00%" in call_args[1]

@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_price_alerts_change_percent_down_triggered(mock_send_telegram, db_session, price_alert_service):
    # Setup: active alert for percentage decrease
    user = TestUser(id=1, username="testuser", email="test@example.com", hashed_password="hashedpassword", telegram_id=123)
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add_all([user, stock])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(stock)

    alert = TestPriceAlert(user_id=user.id, symbol="AAPL", change_percent=-5.0, change_type="down", is_active=True, notify_on_disclosure=False)
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    # Previous day's price
    prev_date = datetime.date.today() - datetime.timedelta(days=1)
    prev_price = TestDailyPrice(symbol="AAPL", date=prev_date, open=100.0, high=100.0, low=100.0, close=100.0, volume=1000000)
    # Current day's price (-6% decrease)
    current_price = TestDailyPrice(symbol="AAPL", date=datetime.date.today(), open=95.0, high=96.0, low=93.0, close=94.0, volume=1200000)
    db_session.add_all([prev_price, current_price])
    db_session.commit()

    # Run the check
    await price_alert_service.check_and_notify_price_alerts(db_session)

    # Assertions
    mock_send_telegram.assert_called_once()
    call_args = mock_send_telegram.call_args[0]
    assert call_args[0] == user.telegram_id
    assert "변동률 도달" in call_args[1]
    assert "-5.0% down" in call_args[1]
    assert "-6.00%" in call_args[1]

@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_price_alerts_change_percent_not_triggered(mock_send_telegram, db_session, price_alert_service):
    # Setup: active alert for percentage increase, but condition not met
    user = TestUser(id=1, username="testuser", email="test@example.com", hashed_password="hashedpassword", telegram_id=123)
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add_all([user, stock])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(stock)

    alert = TestPriceAlert(user_id=user.id, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, notify_on_disclosure=False)
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    # Previous day's price
    prev_date = datetime.date.today() - datetime.timedelta(days=1)
    prev_price = TestDailyPrice(symbol="AAPL", date=prev_date, open=100.0, high=100.0, low=100.0, close=100.0, volume=1000000)
    # Current day's price (4% increase)
    current_price = TestDailyPrice(symbol="AAPL", date=datetime.date.today(), open=102.0, high=105.0, low=101.0, close=104.0, volume=1200000)
    db_session.add_all([prev_price, current_price])
    db_session.commit()

    # Run the check
    await price_alert_service.check_and_notify_price_alerts(db_session)

    # Assertions
    mock_send_telegram.assert_not_called()
    db_session.refresh(alert)
    assert alert.is_active is True # Should remain active

@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_price_alerts_not_enough_price_data(mock_send_telegram, db_session, price_alert_service):
    # Setup: active alert for percentage change, but only one price point exists
    user = TestUser(id=1, username="testuser", email="test@example.com", hashed_password="hashedpassword", telegram_id=123)
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add_all([user, stock])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(stock)

    alert = TestPriceAlert(user_id=user.id, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, notify_on_disclosure=False)
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    # Only one price point
    current_price = TestDailyPrice(symbol="AAPL", date=datetime.date.today(), open=105.0, high=107.0, low=104.0, close=106.0, volume=1200000)
    db_session.add(current_price)
    db_session.commit()

    # Run the check
    await price_alert_service.check_and_notify_price_alerts(db_session)

    # Assertions
    mock_send_telegram.assert_not_called()
    db_session.refresh(alert)
    assert alert.is_active is True # Should remain active

@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_price_alerts_skip_due_to_interval(
    mock_send_telegram_message, price_alert_service, caplog, db_session
):
    """
    check_and_notify_price_alerts: 알림 주기에 따라 알림이 건너뛰어지는 경우를 테스트
    """
    # Given
    stock = TestStockMaster(symbol="005930", name="삼성전자")
    user = TestUser(id=1, username="testuser", telegram_id=123)
    db_session.add_all([stock, user])
    db_session.commit()
    db_session.refresh(stock)
    db_session.refresh(user)

    daily_price = TestDailyPrice(symbol="005930", date=datetime.date.today(), close=100000, open=0, high=0, low=0, volume=0)
    db_session.add(daily_price)
    db_session.commit()

    # Mock PriceAlert - last_notified_at is recent
    recent_notification_time = datetime.datetime.now() - datetime.timedelta(hours=1) # 1 hour ago
    alert = TestPriceAlert(
        user_id=user.id,
        symbol="005930",
        condition="above",
        target_price=90000,
        is_active=True,
        last_notified_at=recent_notification_time,
        notification_count=0,
        notification_interval_hours=2 # Notify every 2 hours
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    # When
    with caplog.at_level(logging.INFO):
        await price_alert_service.check_and_notify_price_alerts(db_session)

    # Then
    mock_send_telegram_message.assert_not_awaited()
    assert f"알림 ID {alert.id}는 최근에 전송되었으므로 건너뜁니다." in caplog.text
    db_session.refresh(alert)
    assert alert.notification_count == 0 # Should not have increased

@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.send_telegram_message', new_callable=AsyncMock)
async def test_check_and_notify_price_alerts_not_skip_due_to_interval(
    mock_send_telegram_message, price_alert_service, caplog, db_session
):
    """
    check_and_notify_price_alerts: 알림 주기가 지나 알림이 정상적으로 전송되는 경우를 테스트
    """
    # Given
    stock = TestStockMaster(symbol="005930", name="삼성전자")
    user = TestUser(id=1, username="testuser", telegram_id=123)
    db_session.add_all([stock, user])
    db_session.commit()
    db_session.refresh(stock)
    db_session.refresh(user)

    daily_price = TestDailyPrice(symbol="005930", date=datetime.date.today(), close=100000, open=0, high=0, low=0, volume=0)
    db_session.add(daily_price)
    db_session.commit()

    # last_notified_at is old
    old_notification_time = datetime.datetime.now() - datetime.timedelta(hours=3) # 3 hours ago
    alert = TestPriceAlert(
        user_id=user.id,
        symbol="005930",
        condition="above",
        target_price=90000,
        is_active=True,
        last_notified_at=old_notification_time,
        notification_count=1,
        notification_interval_hours=2 # Notify every 2 hours
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    # When
    await price_alert_service.check_and_notify_price_alerts(db_session)

    # Then
    mock_send_telegram_message.assert_awaited_once()
    db_session.refresh(alert)
    assert alert.notification_count == 2 # Should have increased
    assert alert.last_notified_at > old_notification_time
    assert f"알림 ID {alert.id}는 최근에 전송되었으므로 건너뜁니다." not in caplog.text