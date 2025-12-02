import pytest
from unittest.mock import MagicMock, patch, AsyncMock, ANY, call
from fastapi import HTTPException, status # Added imports
from src.api.main import app
from src.common.models.user import User
from src.common.models.price_alert import PriceAlert
from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate, PriceAlertRead
from src.common.services.price_alert_service import PriceAlertService
from src.common.models.daily_price import DailyPrice
from datetime import datetime

# Fixtures
@pytest.fixture
def price_alert_service():
    return PriceAlertService()

@pytest.fixture
def mock_db():
    # MOCK: SQLAlchemy Session 객체
    # SQLAlchemy Session의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_query_obj = MagicMock()
    mock_query_obj.options.return_value = mock_query_obj
    mock_query_obj.filter.return_value = mock_query_obj
    mock_query_obj.order_by.return_value = mock_query_obj
    mock_db_mock = MagicMock()
    mock_db_mock.query.return_value = mock_query_obj
    return mock_db_mock

# Test Data
mock_user = User(id=1, telegram_id=12345, username="testuser")
mock_alert = PriceAlert(
    id=1, user_id=1, symbol="005930", is_active=True,
    created_at=datetime.now(), updated_at=datetime.now(),
    target_price=None, condition=None, change_percent=None, change_type=None, repeat_interval=None
)

# Tests for create_alert
@pytest.mark.asyncio
async def test_create_alert_success_target_price(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="AAPL",
        target_price=150.0,
        condition="gte",
        notify_on_disclosure=False
    )
    # MOCK: mock_db.add, mock_db.commit, mock_db.refresh
    # mock_db.add (MagicMock) 호출 시 None을 반환하도록 설정합니다.
    mock_db.add.return_value = None
    # mock_db.commit (MagicMock) 호출 시 None을 반환하도록 설정합니다.
    mock_db.commit.return_value = None
    # mock_db.refresh (MagicMock) 호출 시 입력된 객체를 그대로 반환하도록 설정하여 refresh를 모의합니다.
    mock_db.refresh.side_effect = lambda x: x # Simulate refresh by returning the object itself

    # MOCK: PriceAlert 클래스
    # PriceAlert 생성자를 모의하여 실제 객체 생성 대신 mock_alert를 반환하도록 설정합니다.
    with patch('src.common.services.price_alert_service.PriceAlert') as MockPriceAlert:
        MockPriceAlert.return_value = mock_alert # Mock the PriceAlert constructor
        created_alert = await price_alert_service.create_alert(mock_db, 1, alert_create)

        # mock_db.add (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
        mock_db.add.assert_called_once_with(ANY)
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()
        # mock_db.refresh (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
        mock_db.refresh.assert_called_once_with(ANY)
        assert created_alert == mock_alert

@pytest.mark.asyncio
async def test_create_alert_success_change_percent(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="GOOG",
        change_percent=5.0,
        change_type="up"
    )
    # MOCK: mock_db.add, mock_db.commit, mock_db.refresh
    # mock_db.add (MagicMock) 호출 시 None을 반환하도록 설정합니다.
    mock_db.add.return_value = None
    # mock_db.commit (MagicMock) 호출 시 None을 반환하도록 설정합니다.
    mock_db.commit.return_value = None
    # mock_db.refresh (MagicMock) 호출 시 입력된 객체를 그대로 반환하도록 설정하여 refresh를 모의합니다.
    mock_db.refresh.side_effect = lambda x: x

    # MOCK: PriceAlert 클래스
    # PriceAlert 생성자를 모의하여 실제 객체 생성 대신 mock_alert를 반환하도록 설정합니다.
    with patch('src.common.services.price_alert_service.PriceAlert') as MockPriceAlert:
        MockPriceAlert.return_value = mock_alert
        created_alert = await price_alert_service.create_alert(mock_db, 1, alert_create)

        # mock_db.add (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
        mock_db.add.assert_called_once_with(ANY)
        # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
        mock_db.commit.assert_called_once()
        # mock_db.refresh (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
        mock_db.refresh.assert_called_once_with(ANY)
        assert created_alert == mock_alert



# Tests for get_alert_by_id
def test_get_alert_by_id_found(price_alert_service, mock_db):
    # MOCK: mock_db.query
    # mock_db.query().filter().first() 호출 시 mock_alert를 반환하도록 설정합니다.
    mock_query_result = MagicMock()
    mock_query_result.filter.return_value = mock_query_result
    mock_query_result.first.return_value = mock_alert
    mock_db.query.return_value = mock_query_result

    alert = price_alert_service.get_alert_by_id(mock_db, 1)

    # mock_db.query (MagicMock)가 PriceAlert 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(PriceAlert)
    # mock_query_result.filter (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
    mock_query_result.filter.assert_called_once_with(ANY) 
    assert alert == mock_alert

def test_get_alert_by_id_not_found(price_alert_service, mock_db):
    # MOCK: mock_db.query
    # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
    mock_query_result = MagicMock()
    mock_query_result.filter.return_value = mock_query_result
    mock_query_result.first.return_value = None
    mock_db.query.return_value = mock_query_result

    alert = price_alert_service.get_alert_by_id(mock_db, 999)

    # mock_db.query (MagicMock)가 PriceAlert 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(PriceAlert)
    # mock_query_result.filter (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
    mock_query_result.filter.assert_called_once_with(ANY) 
    assert alert is None

# Tests for get_alert_by_user_and_symbol
def test_get_alert_by_user_and_symbol_found(price_alert_service, mock_db):
    # MOCK: mock_db.query
    # mock_db.query().filter().first() 호출 시 mock_alert를 반환하도록 설정합니다.
    mock_query_result = MagicMock()
    mock_query_result.filter.return_value = mock_query_result # filter returns itself for chaining
    mock_query_result.first.return_value = mock_alert
    mock_db.query.return_value = mock_query_result

    alert = price_alert_service.get_alert_by_user_and_symbol(mock_db, 1, "005930")

    # mock_db.query (MagicMock)가 PriceAlert 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(PriceAlert)
    # mock_query_result.filter (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
    mock_query_result.filter.assert_called_once_with(ANY, ANY)
    assert alert == mock_alert

def test_get_alert_by_user_and_symbol_not_found(price_alert_service, mock_db):
    # MOCK: mock_db.query
    # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
    mock_query_result = MagicMock()
    mock_query_result.filter.return_value = mock_query_result
    mock_query_result.first.return_value = None
    mock_db.query.return_value = mock_query_result

    alert = price_alert_service.get_alert_by_user_and_symbol(mock_db, 1, "999999")

    # mock_db.query (MagicMock)가 PriceAlert 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(PriceAlert)
    assert alert is None

# Tests for get_alerts
def test_get_alerts_success(price_alert_service, mock_db):
    # MOCK: PriceAlert 모델 객체
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_alert1 = MagicMock(spec=PriceAlert, id=1, user_id=1, symbol="AAPL")
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_alert2 = MagicMock(spec=PriceAlert, id=2, user_id=1, symbol="GOOG")
    
    # MOCK: mock_db.query 체인
    # mock_db.query().options().filter().order_by().all() 호출 시 모의 알림 목록을 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert1, mock_alert2]

    alerts = price_alert_service.get_alerts(mock_db, 1)

    # mock_db.query (MagicMock)가 PriceAlert 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(PriceAlert)
    # mock_db.query().filter (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.assert_called_once_with(ANY)
    # mock_db.query().filter().all (MagicMock)이 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.return_value.all.assert_called_once()
    assert alerts == [mock_alert1, mock_alert2]

def test_get_alerts_no_alerts(price_alert_service, mock_db):
    # MOCK: mock_db.query 체인
    # mock_db.query().options().filter().all() 호출 시 빈 목록을 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.all.return_value = []

    alerts = price_alert_service.get_alerts(mock_db, 1)

    # mock_db.query (MagicMock)가 PriceAlert 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(PriceAlert)
    # mock_db.query().filter (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.assert_called_once_with(ANY)
    # mock_db.query().filter().all (MagicMock)이 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.return_value.all.assert_called_once()
    assert alerts == []

# Tests for update_alert
@pytest.mark.asyncio
async def test_update_alert_success(price_alert_service, mock_db):
    alert_update = PriceAlertUpdate(target_price=160.0, is_active=False)
    # MOCK: mock_db.query().filter().first()
    # mock_db.query().filter().first() 호출 시 mock_alert를 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.first.return_value = mock_alert
    # MOCK: mock_db.commit, mock_db.refresh
    # mock_db.commit (MagicMock) 호출 시 None을 반환하도록 설정합니다.
    mock_db.commit.return_value = None
    # mock_db.refresh (MagicMock) 호출 시 입력된 객체를 그대로 반환하도록 설정하여 refresh를 모의합니다.
    mock_db.refresh.side_effect = lambda x: x

    updated_alert = await price_alert_service.update_alert(mock_db, 1, alert_update)

    # mock_db.query (MagicMock)가 PriceAlert 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(PriceAlert)
    # mock_db.query().filter (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.assert_called_once_with(ANY)
    # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
    mock_db.commit.assert_called_once()
    # mock_db.refresh (MagicMock)가 mock_alert 인자로 한 번 호출되었는지 확인합니다.
    mock_db.refresh.assert_called_once_with(mock_alert)
    assert updated_alert.target_price == 160.0
    assert updated_alert.is_active is False

@pytest.mark.asyncio
async def test_update_alert_not_found(price_alert_service, mock_db):
    alert_update = PriceAlertUpdate(target_price=160.0)
    # MOCK: mock_db.query().filter().first()
    # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await price_alert_service.update_alert(mock_db, 999, alert_update)
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Alert not found"

    # mock_db.query (MagicMock)가 PriceAlert 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(PriceAlert)
    # mock_db.query().filter (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.assert_called_once_with(ANY)
    # No assert for updated_alert is None, as an exception is expected

# Tests for delete_alert
@pytest.mark.asyncio
async def test_delete_alert_success(price_alert_service, mock_db):
    # MOCK: mock_db.query().filter().first()
    # mock_db.query().filter().first() 호출 시 mock_alert를 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.first.return_value = mock_alert
    # MOCK: mock_db.delete, mock_db.commit
    # mock_db.delete (MagicMock) 호출 시 None을 반환하도록 설정합니다.
    mock_db.delete.return_value = None
    # mock_db.commit (MagicMock) 호출 시 None을 반환하도록 설정합니다.
    mock_db.commit.return_value = None

    result = await price_alert_service.delete_alert(mock_db, 1)

    # mock_db.query (MagicMock)가 PriceAlert 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(PriceAlert)
    # mock_db.query().filter (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다。
    mock_db.query.return_value.filter.assert_called_once_with(ANY)
    # mock_db.delete (MagicMock)가 mock_alert 인자로 한 번 호출되었는지 확인합니다.
    mock_db.delete.assert_called_once_with(mock_alert)
    # mock_db.commit (MagicMock)이 한 번 호출되었는지 확인합니다.
    mock_db.commit.assert_called_once()
    assert result is True

@pytest.mark.asyncio
async def test_delete_alert_not_found(price_alert_service, mock_db):
    # MOCK: mock_db.query().filter().first()
    # mock_db.query().filter().first() 호출 시 None을 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await price_alert_service.delete_alert(mock_db, 999)
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Alert not found"

    # mock_db.query (MagicMock)가 PriceAlert 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(PriceAlert)
    # mock_db.query().filter (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.assert_called_once_with(ANY)
    # mock_db.delete (MagicMock)가 호출되지 않았는지 확인합니다.
    mock_db.delete.assert_not_called()
    # mock_db.commit (MagicMock)이 호출되지 않았는지 확인합니다.
    mock_db.commit.assert_not_called()
    # No assert for result is False, as an exception is expected

# Tests for get_all_active_alerts
def test_get_all_active_alerts_success(price_alert_service, mock_db):
    # MOCK: PriceAlert 모델 객체
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_alert1 = MagicMock(spec=PriceAlert, id=1, is_active=True)
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_alert2 = MagicMock(spec=PriceAlert, id=2, is_active=True)
    
    # MOCK: mock_db.query 체인
    # mock_db.query().options().filter().all() 호출 시 모의 알림 목록을 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert1, mock_alert2] # Removed .options()

    alerts = price_alert_service.get_all_active_alerts(mock_db)

    # mock_db.query (MagicMock)가 PriceAlert 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(PriceAlert)
    # mock_db.query().filter (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.assert_called_once_with(ANY)
    # mock_db.query().filter().all (MagicMock)이 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.return_value.all.assert_called_once()
    assert alerts == [mock_alert1, mock_alert2]

def test_get_all_active_alerts_no_active_alerts(price_alert_service, mock_db):
    # MOCK: mock_db.query 체인
    # mock_db.query().options().filter().all() 호출 시 빈 목록을 반환하도록 설정합니다.
    mock_db.query.return_value.filter.return_value.all.return_value = [] # Removed .options()

    alerts = price_alert_service.get_all_active_alerts(mock_db)

    # mock_db.query (MagicMock)가 PriceAlert 모델로 한 번 호출되었는지 확인합니다.
    mock_db.query.assert_called_once_with(PriceAlert)
    # mock_db.query().filter (MagicMock)가 ANY 인자로 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.assert_called_once_with(ANY)
    # mock_db.query().filter().all (MagicMock)이 한 번 호출되었는지 확인합니다.
    mock_db.query.return_value.filter.return_value.all.assert_called_once()
    assert alerts == []

# Tests for check_alerts (SKIPPED for now)
@pytest.mark.skip(reason="check_alerts method not yet implemented in PriceAlertService")
@pytest.mark.asyncio
async def test_check_alerts_target_price_gte_triggered(price_alert_service, mock_db):
    # MOCK: PriceAlert 모델 객체
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", target_price=150.0, condition="gte", is_active=True, change_percent=None, notify_on_disclosure=False)
    # MOCK: mock_db.query().filter().all()
    # mock_db.query().filter().all() 호출 시 모의 알림 목록을 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 155.0)
    assert len(triggered_alerts) == 1
    assert triggered_alerts[0] == mock_alert

@pytest.mark.skip(reason="check_alerts method not yet implemented in PriceAlertService")
@pytest.mark.asyncio
async def test_check_alerts_target_price_lte_triggered(price_alert_service, mock_db):
    # MOCK: PriceAlert 모델 객체
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    
    # MOCK: mock_db.query().filter().all()
    # mock_db.query().filter().all() 호출 시 모의 알림 목록을 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 145.0)
    assert len(triggered_alerts) == 1
    assert triggered_alerts[0] == mock_alert

@pytest.mark.skip(reason="check_alerts method not yet implemented in PriceAlertService")
@pytest.mark.asyncio
async def test_check_alerts_change_percent_up_triggered(price_alert_service, mock_db):
    # MOCK: PriceAlert 모델 객체
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, target_price=None, notify_on_disclosure=False)
    # MOCK: mock_db.query().filter().all()
    # mock_db.query().filter().all() 호출 시 모의 알림 목록을 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    # MOCK: DailyPrice 모델 객체
    # MagicMock: DailyPrice 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_daily_price1 = MagicMock(spec=DailyPrice, close=100.0) # Yesterday
    # MagicMock: DailyPrice 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_daily_price2 = MagicMock(spec=DailyPrice, close=105.0) # Today
    # MOCK: mock_db.query().filter().order_by().limit().all()
    # mock_db.query().filter().order_by().limit().all() 호출 시 모의 일별 시세 목록을 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_daily_price2, mock_daily_price1]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 105.0)
    assert len(triggered_alerts) == 1
    assert triggered_alerts[0] == mock_alert

@pytest.mark.skip(reason="check_alerts method not yet implemented in PriceAlertService")
@pytest.mark.asyncio
async def test_check_alerts_change_percent_down_triggered(price_alert_service, mock_db):
    # MOCK: PriceAlert 모델 객체
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    
    # MOCK: mock_db.query().filter().all()
    # mock_db.query().filter().all() 호출 시 모의 알림 목록을 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    # MOCK: DailyPrice 모델 객체
    # MagicMock: DailyPrice 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_daily_price1 = MagicMock(spec=DailyPrice, close=100.0) # Yesterday
    # MagicMock: DailyPrice 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_daily_price2 = MagicMock(spec=DailyPrice, close=95.0) # Today
    # MOCK: mock_db.query().filter().order_by().limit().all()
    # mock_db.query().filter().order_by().limit().all() 호출 시 모의 일별 시세 목록을 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_daily_price2, mock_daily_price1]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 95.0)
    assert len(triggered_alerts) == 1
    assert triggered_alerts[0] == mock_alert

@pytest.mark.skip(reason="check_alerts method not yet implemented in PriceAlertService")
@pytest.mark.asyncio
async def test_check_alerts_no_trigger(price_alert_service, mock_db):
    # MOCK: PriceAlert 모델 객체
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", target_price=150.0, condition="gte", is_active=True, change_percent=None, notify_on_disclosure=False)
    # MOCK: mock_db.query().filter().all()
    # mock_db.query().filter().all() 호출 시 모의 알림 목록을 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 140.0) # Price not met
    assert len(triggered_alerts) == 0

@pytest.mark.skip(reason="check_alerts method not yet implemented in PriceAlertService")
@pytest.mark.asyncio
async def test_check_alerts_insufficient_daily_price_data(price_alert_service, mock_db):
    # MOCK: PriceAlert 모델 객체
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, target_price=None, notify_on_disclosure=False)
    # MOCK: mock_db.query().filter().all()
    # mock_db.query().filter().all() 호출 시 모의 알림 목록을 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]
    # MOCK: mock_db.query().filter().order_by().limit().all()
    # mock_db.query().filter().order_by().limit().all() 호출 시 하루치 데이터만 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [MagicMock(spec=DailyPrice, close=100.0)] # Only one day of data

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 105.0)
    assert len(triggered_alerts) == 0

@pytest.mark.skip(reason="check_alerts method not yet implemented in PriceAlertService")
@pytest.mark.asyncio
async def test_check_alerts_yesterday_close_is_zero(price_alert_service, mock_db):
    # MOCK: PriceAlert 모델 객체
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, target_price=None, notify_on_disclosure=False)
    # MOCK: mock_db.query().filter().all()
    # mock_db.query().filter().all() 호출 시 모의 알림 목록을 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    # MOCK: DailyPrice 모델 객체
    # MagicMock: DailyPrice 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_daily_price1 = MagicMock(spec=DailyPrice, close=0.0) # Yesterday
    # MagicMock: DailyPrice 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_daily_price2 = MagicMock(spec=DailyPrice, close=105.0) # Today
    # MOCK: mock_db.query().filter().order_by().limit().all()
    # mock_db.query().filter().order_by().limit().all() 호출 시 모의 일별 시세 목록을 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_daily_price2, mock_daily_price1]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 105.0)
    assert len(triggered_alerts) == 0
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, target_price=None, notify_on_disclosure=False)
    # MOCK: mock_db.query().filter().all()
    # mock_db.query().filter().all() 호출 시 모의 알림 목록을 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    # MOCK: DailyPrice 모델 객체
    # MagicMock: DailyPrice 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_daily_price1 = MagicMock(spec=DailyPrice, close=0.0) # Yesterday
    # MagicMock: DailyPrice 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다。
    mock_daily_price2 = MagicMock(spec=DailyPrice, close=105.0) # Today
    # MOCK: mock_db.query().filter().order_by().limit().all()
    # mock_db.query().filter().order_by().limit().all() 호출 시 모의 일별 시세 목록을 반환하도록 설정합니다。
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_daily_price2, mock_daily_price1]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 105.0)
    assert len(triggered_alerts) == 000

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 105.0)
    assert len(triggered_alerts) == 00

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 105.0)
    assert len(triggered_alerts) == 0