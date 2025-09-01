import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, status
import datetime
import redis

from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
from src.common.tests.unit.conftest import TestUser, TestStockMaster, TestPriceAlert, TestDailyPrice

@pytest.mark.asyncio
async def test_create_alert_change_percent_missing_type(db_session, price_alert_service):
    # Add stock master for the symbol
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add(stock)
    db_session.commit()

    alert_data = PriceAlertCreate(symbol="AAPL", change_percent=5.0)
    with pytest.raises(HTTPException) as exc_info:
        await price_alert_service.create_alert(db_session, 1, alert_data)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "변동률 알림 설정 시 변동 유형(change_type)도 함께 설정해야 합니다." in exc_info.value.detail

@pytest.mark.asyncio
async def test_create_alert_change_type_missing_percent(db_session, price_alert_service):
    # Add stock master for the symbol
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add(stock)
    db_session.commit()

    alert_data = PriceAlertCreate(symbol="AAPL", change_type="up")
    with pytest.raises(HTTPException) as exc_info:
        await price_alert_service.create_alert(db_session, 1, alert_data)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "변동 유형(change_type) 설정 시 변동률(change_percent)도 함께 설정해야 합니다." in exc_info.value.detail

@pytest.mark.asyncio
async def test_create_alert_no_conditions(db_session, price_alert_service):
    # Add stock master for the symbol
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add(stock)
    db_session.commit()

    alert_data = PriceAlertCreate(symbol="AAPL", notify_on_disclosure=False)
    with pytest.raises(HTTPException) as exc_info:
        await price_alert_service.create_alert(db_session, 1, alert_data)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "최소 하나의 알림 조건(목표 가격, 변동률, 공시 알림)은 반드시 설정해야 합니다." in exc_info.value.detail

@pytest.mark.asyncio
@patch('src.common.services.price_alert_service.logger')
@patch('src.common.services.price_alert_service.PriceAlertService.get_all_active_alerts')
async def test_check_and_notify_price_alerts_get_all_active_alerts_exception(
    mock_get_all_active_alerts, mock_logger, db_session, price_alert_service
):
    mock_get_all_active_alerts.side_effect = Exception("Database error during alert fetch")
    await price_alert_service.check_and_notify_price_alerts(db_session)
    mock_logger.error.assert_called_once_with(
        "Error checking and notifying price alerts: Database error during alert fetch", exc_info=True
    )

@pytest.mark.asyncio
async def test_create_alert_db_exception(db_session, price_alert_service):
    user = TestUser(id=1, username="testuser", email="test@example.com", hashed_password="hashedpassword")
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add_all([user, stock])
    db_session.commit()

    alert_data = PriceAlertCreate(symbol="AAPL", target_price=150.0, condition="gte")
    with patch.object(db_session, 'commit', side_effect=Exception("DB Error")):
        with patch.object(db_session, 'rollback') as mock_rollback:
            with pytest.raises(Exception) as exc_info:
                await price_alert_service.create_alert(db_session, user.id, alert_data)
            assert "DB Error" in str(exc_info.value)
            mock_rollback.assert_called_once()

@pytest.mark.asyncio
async def test_update_alert_db_exception(db_session, price_alert_service):
    user = TestUser(id=1, username="testuser")
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add_all([user, stock])
    db_session.commit()

    alert = TestPriceAlert(user_id=1, symbol="AAPL", target_price=150.0, condition="gte")
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    update_data = PriceAlertUpdate(target_price=160.0)
    with patch.object(db_session, 'commit', side_effect=Exception("DB Error")):
        with patch.object(db_session, 'rollback') as mock_rollback:
            with pytest.raises(Exception) as exc_info:
                await price_alert_service.update_alert(db_session, alert.id, update_data)
            assert "DB Error" in str(exc_info.value)
            mock_rollback.assert_called_once()

@pytest.mark.asyncio
async def test_delete_alert_db_exception(db_session, price_alert_service):
    user = TestUser(id=1, username="testuser")
    stock = TestStockMaster(symbol="AAPL", name="Apple Inc.")
    db_session.add_all([user, stock])
    db_session.commit()

    alert = TestPriceAlert(user_id=1, symbol="AAPL", target_price=150.0, condition="gte")
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    with patch.object(db_session, 'commit', side_effect=Exception("DB Error")):
        with patch.object(db_session, 'rollback') as mock_rollback:
            with pytest.raises(Exception) as exc_info:
                await price_alert_service.delete_alert(db_session, alert.id)
            assert "DB Error" in str(exc_info.value)
            mock_rollback.assert_called_once()