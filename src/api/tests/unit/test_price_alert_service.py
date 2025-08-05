import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.api.services.price_alert_service import PriceAlertService
from src.api.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
from src.api.models.price_alert import PriceAlert
from src.api.models.daily_price import DailyPrice

# Fixture for PriceAlertService instance
@pytest.fixture
def price_alert_service():
    return PriceAlertService()

# Fixture for a mock database session
@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

# Test cases for create_alert method
def test_create_alert_success_target_price(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="AAPL",
        target_price=150.0,
        condition="gte",
        notify_on_disclosure=False
    )
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.side_effect = lambda x: x # Simulate refresh by returning the object itself

    with patch('src.api.services.price_alert_service.PriceAlert') as MockPriceAlert:
        mock_price_alert_instance = MockPriceAlert.return_value
        mock_price_alert_instance.id = 1
        mock_price_alert_instance.user_id = 1
        mock_price_alert_instance.symbol = "AAPL"
        mock_price_alert_instance.target_price = 150.0
        mock_price_alert_instance.condition = "gte"
        mock_price_alert_instance.change_percent = None
        mock_price_alert_instance.change_type = None
        mock_price_alert_instance.notify_on_disclosure = False
        mock_price_alert_instance.repeat_interval = None
        mock_price_alert_instance.is_active = True

        alert = price_alert_service.create_alert(mock_db, 1, alert_create)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_price_alert_instance)
        assert alert.symbol == "AAPL"
        assert alert.target_price == 150.0
        assert alert.condition == "gte"
        assert alert.notify_on_disclosure == False
        assert alert.is_active == True

def test_create_alert_success_change_percent(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="GOOG",
        change_percent=5.0,
        change_type="up",
        notify_on_disclosure=False
    )
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.side_effect = lambda x: x

    with patch('src.api.services.price_alert_service.PriceAlert') as MockPriceAlert:
        mock_price_alert_instance = MockPriceAlert.return_value
        mock_price_alert_instance.id = 2
        mock_price_alert_instance.user_id = 1
        mock_price_alert_instance.symbol = "GOOG"
        mock_price_alert_instance.target_price = None
        mock_price_alert_instance.condition = None
        mock_price_alert_instance.change_percent = 5.0
        mock_price_alert_instance.change_type = "up"
        mock_price_alert_instance.notify_on_disclosure = False
        mock_price_alert_instance.repeat_interval = None
        mock_price_alert_instance.is_active = True

        alert = price_alert_service.create_alert(mock_db, 1, alert_create)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_price_alert_instance)
        assert alert.symbol == "GOOG"
        assert alert.change_percent == 5.0
        assert alert.change_type == "up"
        assert alert.notify_on_disclosure == False
        assert alert.is_active == True

def test_create_alert_success_disclosure(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="MSFT",
        notify_on_disclosure=True
    )
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.side_effect = lambda x: x

    with patch('src.api.services.price_alert_service.PriceAlert') as MockPriceAlert:
        mock_price_alert_instance = MockPriceAlert.return_value
        mock_price_alert_instance.id = 3
        mock_price_alert_instance.user_id = 1
        mock_price_alert_instance.symbol = "MSFT"
        mock_price_alert_instance.target_price = None
        mock_price_alert_instance.condition = None
        mock_price_alert_instance.change_percent = None
        mock_price_alert_instance.change_type = None
        mock_price_alert_instance.notify_on_disclosure = True
        mock_price_alert_instance.repeat_interval = None
        mock_price_alert_instance.is_active = True

        alert = price_alert_service.create_alert(mock_db, 1, alert_create)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_price_alert_instance)
        assert alert.symbol == "MSFT"
        assert alert.notify_on_disclosure == True
        assert alert.is_active == True

def test_create_alert_no_condition_set(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="AMZN",
        notify_on_disclosure=False # Explicitly set to False
    )
    with pytest.raises(HTTPException) as exc_info:
        price_alert_service.create_alert(mock_db, 1, alert_create)
    assert exc_info.value.status_code == 400
    assert "최소 하나의 알림 조건" in exc_info.value.detail
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()

def test_create_alert_change_percent_without_type(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="NFLX",
        change_percent=10.0,
        notify_on_disclosure=False
    )
    with pytest.raises(HTTPException) as exc_info:
        price_alert_service.create_alert(mock_db, 1, alert_create)
    assert exc_info.value.status_code == 400
    assert "변동률 알림 설정 시 변동 유형(change_type)도 함께 설정해야 합니다." in exc_info.value.detail
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()

def test_create_alert_change_type_without_percent(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="TSLA",
        change_type="down",
        notify_on_disclosure=False
    )
    with pytest.raises(HTTPException) as exc_info:
        price_alert_service.create_alert(mock_db, 1, alert_create)
    assert exc_info.value.status_code == 400
    assert "변동 유형(change_type) 설정 시 변동률(change_percent)도 함께 설정해야 합니다." in exc_info.value.detail
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()

def test_create_alert_db_exception(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="NVDA",
        target_price=500.0,
        condition="lte",
        notify_on_disclosure=False
    )
    mock_db.add.side_effect = Exception("DB Error")

    with pytest.raises(Exception) as exc_info:
        price_alert_service.create_alert(mock_db, 1, alert_create)
    assert "DB Error" in str(exc_info.value)
    mock_db.add.assert_called_once()
    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()

# Test cases for get_alerts method
def test_get_alerts_success(price_alert_service, mock_db):
    mock_alert1 = MagicMock(spec=PriceAlert, id=1, user_id=1, symbol="AAPL")
    mock_alert2 = MagicMock(spec=PriceAlert, id=2, user_id=1, symbol="GOOG")
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_alert1, mock_alert2]

    alerts = price_alert_service.get_alerts(mock_db, 1)

    mock_db.query.assert_called_once_with(PriceAlert)
    mock_db.query.return_value.filter.assert_called_once()
    mock_db.query.return_value.filter.return_value.order_by.assert_called_once()
    assert len(alerts) == 2
    assert alerts[0].symbol == "AAPL"
    assert alerts[1].symbol == "GOOG"

def test_get_alerts_no_alerts(price_alert_service, mock_db):
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    alerts = price_alert_service.get_alerts(mock_db, 1)

    assert len(alerts) == 0

# Test cases for get_alert_by_user_and_symbol method
def test_get_alert_by_user_and_symbol_found(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, user_id=1, symbol="AAPL")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_alert

    alert = price_alert_service.get_alert_by_user_and_symbol(mock_db, 1, "AAPL")

    mock_db.query.assert_called_once_with(PriceAlert)
    mock_db.query.return_value.filter.assert_called_once()
    assert alert.symbol == "AAPL"

def test_get_alert_by_user_and_symbol_not_found(price_alert_service, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    alert = price_alert_service.get_alert_by_user_and_symbol(mock_db, 1, "NONEXISTENT")

    assert alert is None

# Test cases for get_alert_by_id method
def test_get_alert_by_id_found(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, user_id=1, symbol="AAPL")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_alert

    alert = price_alert_service.get_alert_by_id(mock_db, 1)

    mock_db.query.assert_called_once_with(PriceAlert)
    mock_db.query.return_value.filter.assert_called_once()
    assert alert.id == 1

def test_get_alert_by_id_not_found(price_alert_service, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    alert = price_alert_service.get_alert_by_id(mock_db, 999)

    assert alert is None

# Test cases for get_all_active_alerts method
def test_get_all_active_alerts_success(price_alert_service, mock_db):
    mock_alert1 = MagicMock(spec=PriceAlert, id=1, is_active=True)
    mock_alert2 = MagicMock(spec=PriceAlert, id=2, is_active=True)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert1, mock_alert2]

    alerts = price_alert_service.get_all_active_alerts(mock_db)

    mock_db.query.assert_called_once_with(PriceAlert)
    mock_db.query.return_value.filter.assert_called_once()
    assert len(alerts) == 2
    assert alerts[0].is_active == True
    assert alerts[1].is_active == True

def test_get_all_active_alerts_no_active_alerts(price_alert_service, mock_db):
    mock_db.query.return_value.filter.return_value.all.return_value = []

    alerts = price_alert_service.get_all_active_alerts(mock_db)

    assert len(alerts) == 0

# Test cases for update_alert method
def test_update_alert_success(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", target_price=150.0, is_active=True, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_alert
    mock_db.commit.return_value = None
    mock_db.refresh.side_effect = lambda x: x

    alert_update = PriceAlertUpdate(target_price=160.0, is_active=False, notify_on_disclosure=True)
    updated_alert = price_alert_service.update_alert(mock_db, 1, alert_update)

    mock_db.query.assert_called_once_with(PriceAlert)
    mock_db.query.return_value.filter.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_alert)
    assert updated_alert.target_price == 160.0
    assert updated_alert.is_active == False
    assert updated_alert.notify_on_disclosure == True

def test_update_alert_not_found(price_alert_service, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    alert_update = PriceAlertUpdate(target_price=160.0)

    with pytest.raises(HTTPException) as exc_info:
        price_alert_service.update_alert(mock_db, 999, alert_update)
    assert exc_info.value.status_code == 404
    assert "Alert not found" in exc_info.value.detail
    mock_db.commit.assert_not_called()

def test_update_alert_db_exception(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", target_price=150.0)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_alert
    mock_db.commit.side_effect = Exception("DB Error during update")

    alert_update = PriceAlertUpdate(target_price=160.0)

    with pytest.raises(Exception) as exc_info:
        price_alert_service.update_alert(mock_db, 1, alert_update)
    assert "DB Error during update" in str(exc_info.value)
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_called_once()

# Test cases for delete_alert method
def test_delete_alert_success(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_alert
    mock_db.delete.return_value = None
    mock_db.commit.return_value = None

    result = price_alert_service.delete_alert(mock_db, 1)

    mock_db.query.assert_called_once_with(PriceAlert)
    mock_db.query.return_value.filter.assert_called_once()
    mock_db.delete.assert_called_once_with(mock_alert)
    mock_db.commit.assert_called_once()
    assert result is True

def test_delete_alert_not_found(price_alert_service, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        price_alert_service.delete_alert(mock_db, 999)
    assert exc_info.value.status_code == 404
    assert "Alert not found" in exc_info.value.detail
    mock_db.delete.assert_not_called()
    mock_db.commit.assert_not_called()

def test_delete_alert_db_exception(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_alert
    mock_db.delete.side_effect = Exception("DB Error during delete")

    with pytest.raises(Exception) as exc_info:
        price_alert_service.delete_alert(mock_db, 1)
    assert "DB Error during delete" in str(exc_info.value)
    mock_db.delete.assert_called_once()
    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()

# Test cases for check_alerts method
def test_check_alerts_target_price_gte_triggered(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", target_price=150.0, condition="gte", is_active=True, change_percent=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    triggered_alerts = price_alert_service.check_alerts(mock_db, "AAPL", 155.0)

    assert len(triggered_alerts) == 1
    assert triggered_alerts[0].id == 1

def test_check_alerts_target_price_lte_triggered(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", target_price=150.0, condition="lte", is_active=True, change_percent=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    triggered_alerts = price_alert_service.check_alerts(mock_db, "AAPL", 145.0)

    assert len(triggered_alerts) == 1
    assert triggered_alerts[0].id == 1

def test_check_alerts_change_percent_up_triggered(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, target_price=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    mock_daily_price1 = MagicMock(spec=DailyPrice, close=100.0) # Yesterday
    mock_daily_price2 = MagicMock(spec=DailyPrice, close=105.0) # Today
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_daily_price2, mock_daily_price1]

    triggered_alerts = price_alert_service.check_alerts(mock_db, "AAPL", 105.0)

    assert len(triggered_alerts) == 1
    assert triggered_alerts[0].id == 1

def test_check_alerts_change_percent_down_triggered(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", change_percent=5.0, change_type="down", is_active=True, target_price=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    mock_daily_price1 = MagicMock(spec=DailyPrice, close=100.0) # Yesterday
    mock_daily_price2 = MagicMock(spec=DailyPrice, close=95.0) # Today
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_daily_price2, mock_daily_price1]

    triggered_alerts = price_alert_service.check_alerts(mock_db, "AAPL", 95.0)

    assert len(triggered_alerts) == 1
    assert triggered_alerts[0].id == 1

def test_check_alerts_no_trigger(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", target_price=150.0, condition="gte", is_active=True, change_percent=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    triggered_alerts = price_alert_service.check_alerts(mock_db, "AAPL", 140.0) # Price not met

    assert len(triggered_alerts) == 0

def test_check_alerts_insufficient_daily_price_data(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, target_price=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [MagicMock(spec=DailyPrice, close=100.0)] # Only one day of data

    triggered_alerts = price_alert_service.check_alerts(mock_db, "AAPL", 105.0)

    assert len(triggered_alerts) == 0

def test_check_alerts_yesterday_close_is_zero(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, target_price=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    mock_daily_price1 = MagicMock(spec=DailyPrice, close=0.0) # Yesterday close is zero
    mock_daily_price2 = MagicMock(spec=DailyPrice, close=105.0) # Today
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_daily_price2, mock_daily_price1]

    triggered_alerts = price_alert_service.check_alerts(mock_db, "AAPL", 105.0)

    assert len(triggered_alerts) == 0
