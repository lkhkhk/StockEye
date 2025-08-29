import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.common.services.price_alert_service import PriceAlertService
from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
from src.common.models.price_alert import PriceAlert
from src.common.models.daily_price import DailyPrice
import redis.asyncio as redis
import json
import asyncio
from src.common.models.user import User
from src.common.models.stock_master import StockMaster
from datetime import date, timedelta

# Fixture for PriceAlertService instance
@pytest.fixture
def price_alert_service():
    return PriceAlertService()

# Fixture for a mock database session
@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

# Test cases for create_alert method
@pytest.mark.asyncio
async def test_create_alert_success_target_price(price_alert_service, mock_db):
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

        alert = await price_alert_service.create_alert(mock_db, 1, alert_create)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_price_alert_instance)
        assert alert.symbol == "AAPL"
        assert alert.target_price == 150.0
        assert alert.condition == "gte"
        assert alert.notify_on_disclosure == False
        assert alert.is_active == True

@pytest.mark.asyncio
async def test_create_alert_success_change_percent(price_alert_service, mock_db):
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

        alert = await price_alert_service.create_alert(mock_db, 1, alert_create)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_price_alert_instance)
        assert alert.symbol == "GOOG"
        assert alert.change_percent == 5.0
        assert alert.change_type == "up"
        assert alert.notify_on_disclosure == False
        assert alert.is_active == True

@pytest.mark.asyncio
async def test_create_alert_success_disclosure(price_alert_service, mock_db):
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

        alert = await price_alert_service.create_alert(mock_db, 1, alert_create)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_price_alert_instance)
        assert alert.symbol == "MSFT"
        assert alert.notify_on_disclosure == True
        assert alert.is_active == True

@pytest.mark.asyncio
async def test_create_alert_no_condition_set(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="AMZN",
        notify_on_disclosure=False # Explicitly set to False
    )
    with pytest.raises(HTTPException) as exc_info:
        await price_alert_service.create_alert(mock_db, 1, alert_create)
    assert exc_info.value.status_code == 400
    assert "최소 하나의 알림 조건" in exc_info.value.detail
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()

@pytest.mark.asyncio
async def test_create_alert_change_percent_without_type(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="NFLX",
        change_percent=10.0,
        notify_on_disclosure=False
    )
    with pytest.raises(HTTPException) as exc_info:
        await price_alert_service.create_alert(mock_db, 1, alert_create)
    assert exc_info.value.status_code == 400
    assert "변동률 알림 설정 시 변동 유형(change_type)도 함께 설정해야 합니다." in exc_info.value.detail
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()

@pytest.mark.asyncio
async def test_create_alert_change_type_without_percent(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="TSLA",
        change_type="down",
        notify_on_disclosure=False
    )
    with pytest.raises(HTTPException) as exc_info:
        await price_alert_service.create_alert(mock_db, 1, alert_create)
    assert exc_info.value.status_code == 400
    assert "변동 유형(change_type) 설정 시 변동률(change_percent)도 함께 설정해야 합니다." in exc_info.value.detail
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()

@pytest.mark.asyncio
async def test_create_alert_db_exception(price_alert_service, mock_db):
    alert_create = PriceAlertCreate(
        symbol="NVDA",
        target_price=500.0,
        condition="lte",
        notify_on_disclosure=False
    )
    mock_db.add.side_effect = Exception("DB Error")

    with pytest.raises(Exception) as exc_info:
        await price_alert_service.create_alert(mock_db, 1, alert_create)
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
@pytest.mark.asyncio
async def test_update_alert_success(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", target_price=150.0, is_active=True, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_alert
    mock_db.commit.return_value = None
    mock_db.refresh.side_effect = lambda x: x

    alert_update = PriceAlertUpdate(target_price=160.0, is_active=False, notify_on_disclosure=True)
    updated_alert = await price_alert_service.update_alert(mock_db, 1, alert_update)

    mock_db.query.assert_called_once_with(PriceAlert)
    mock_db.query.return_value.filter.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_alert)
    assert updated_alert.target_price == 160.0
    assert updated_alert.is_active == False
    assert updated_alert.notify_on_disclosure == True

@pytest.mark.asyncio
async def test_update_alert_not_found(price_alert_service, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    alert_update = PriceAlertUpdate(target_price=160.0)

    with pytest.raises(HTTPException) as exc_info:
        await price_alert_service.update_alert(mock_db, 999, alert_update)
    assert exc_info.value.status_code == 404
    assert "Alert not found" in exc_info.value.detail
    mock_db.commit.assert_not_called()

@pytest.mark.asyncio
async def test_update_alert_db_exception(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", target_price=150.0)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_alert
    mock_db.commit.side_effect = Exception("DB Error during update")

    alert_update = PriceAlertUpdate(target_price=160.0)

    with pytest.raises(Exception) as exc_info:
        await price_alert_service.update_alert(mock_db, 1, alert_update)
    assert "DB Error during update" in str(exc_info.value)
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_called_once()

# Test cases for delete_alert method
@pytest.mark.asyncio
async def test_delete_alert_success(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_alert
    mock_db.delete.return_value = None
    mock_db.commit.return_value = None

    result = await price_alert_service.delete_alert(mock_db, 1)

    mock_db.query.assert_called_once_with(PriceAlert)
    mock_db.query.return_value.filter.assert_called_once()
    mock_db.delete.assert_called_once_with(mock_alert)
    mock_db.commit.assert_called_once()
    assert result is True

@pytest.mark.asyncio
async def test_delete_alert_not_found(price_alert_service, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await price_alert_service.delete_alert(mock_db, 999)
    assert exc_info.value.status_code == 404
    assert "Alert not found" in exc_info.value.detail
    mock_db.delete.assert_not_called()
    mock_db.commit.assert_not_called()

@pytest.mark.asyncio
async def test_delete_alert_db_exception(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_alert
    mock_db.delete.side_effect = Exception("DB Error during delete")

    with pytest.raises(Exception) as exc_info:
        await price_alert_service.delete_alert(mock_db, 1)
    assert "DB Error during delete" in str(exc_info.value)
    mock_db.delete.assert_called_once()
    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()

# Test cases for check_alerts method
@pytest.mark.asyncio
async def test_check_alerts_target_price_gte_triggered(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", target_price=150.0, condition="gte", is_active=True, change_percent=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 155.0)

    assert len(triggered_alerts) == 1
    assert triggered_alerts[0].id == 1

@pytest.mark.asyncio
async def test_check_alerts_target_price_lte_triggered(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", target_price=150.0, condition="lte", is_active=True, change_percent=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 145.0)

    assert len(triggered_alerts) == 1
    assert triggered_alerts[0].id == 1

@pytest.mark.asyncio
async def test_check_alerts_change_percent_up_triggered(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, target_price=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    mock_daily_price1 = MagicMock(spec=DailyPrice, close=100.0) # Yesterday
    mock_daily_price2 = MagicMock(spec=DailyPrice, close=105.0) # Today
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_daily_price2, mock_daily_price1]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 105.0)

    assert len(triggered_alerts) == 1
    assert triggered_alerts[0].id == 1

@pytest.mark.asyncio
async def test_check_alerts_change_percent_down_triggered(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", change_percent=5.0, change_type="down", is_active=True, target_price=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    mock_daily_price1 = MagicMock(spec=DailyPrice, close=100.0) # Yesterday
    mock_daily_price2 = MagicMock(spec=DailyPrice, close=95.0) # Today
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_daily_price2, mock_daily_price1]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 95.0)

    assert len(triggered_alerts) == 1
    assert triggered_alerts[0].id == 1

@pytest.mark.asyncio
async def test_check_alerts_no_trigger(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", target_price=150.0, condition="gte", is_active=True, change_percent=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 140.0) # Price not met

    assert len(triggered_alerts) == 0

@pytest.mark.asyncio
async def test_check_alerts_insufficient_daily_price_data(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, target_price=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [MagicMock(spec=DailyPrice, close=100.0)] # Only one day of data

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 105.0)

    assert len(triggered_alerts) == 0

@pytest.mark.asyncio
async def test_check_alerts_yesterday_close_is_zero(price_alert_service, mock_db):
    mock_alert = MagicMock(spec=PriceAlert, id=1, symbol="AAPL", change_percent=5.0, change_type="up", is_active=True, target_price=None, notify_on_disclosure=False)
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_alert]

    mock_daily_price1 = MagicMock(spec=DailyPrice, close=0.0) # Yesterday close is zero
    mock_daily_price2 = MagicMock(spec=DailyPrice, close=105.0) # Today
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_daily_price2, mock_daily_price1]

    triggered_alerts = await price_alert_service.check_alerts(mock_db, "AAPL", 105.0)

    assert len(triggered_alerts) == 0


# --- Integration Test for Redis Publish ---

REDIS_HOST = "stockeye-redis"
REDIS_PORT = 6379

@pytest.mark.asyncio
async def test_check_price_alerts_publishes_to_redis_on_trigger(price_alert_service, real_db):
    """알림 조건 충족 시 check_price_alerts가 Redis에 메시지를 발행하는지 통합 테스트"""
    # 1. Redis 구독 클라이언트 설정
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("notifications")
    await asyncio.sleep(0.1)

    # 2. Given: 테스트 데이터 설정
    # 사용자 생성
    test_user = User(id=1, username="testuser", email="test@example.com", telegram_id="12345", password_hash="hashed_password")
    real_db.add(test_user)

    # 주식 마스터 생성
    stock = StockMaster(symbol="005930", name="삼성전자", market="KOSPI")
    real_db.add(stock)
    real_db.commit() # User와 StockMaster를 먼저 커밋

    # 가격 알림 생성 (80,000원 이상이면 알림)
    alert = PriceAlert(user_id=test_user.id, symbol=stock.symbol, target_price=80000, condition="gte", is_active=True)
    real_db.add(alert)
    real_db.commit() # PriceAlert를 나중에 커밋

    # 3. When: 알림 조건 충족 및 서비스 메소드 호출
    # 새로운 가격 정보 추가 (81,000원)
    new_price = DailyPrice(symbol=stock.symbol, date=date.today(), open=80000, high=82000, low=79000, close=81000, volume=1000000)
    real_db.add(new_price)
    real_db.commit()

    # 서비스 메소드 호출
    await price_alert_service.check_and_notify_price_alerts(real_db)

    # 4. Then: 결과 검증
    # Redis 메시지 확인
    message = await pubsub.get_message(timeout=1)
    # Redis 제어 메시지(예: subscribe 확인)를 건너뛰고 실제 메시지를 찾습니다.
    while message and message['type'] != 'message':
        message = await pubsub.get_message(timeout=1)

    assert message is not None, "Redis 채널에서 메시지를 수신하지 못했습니다."
    assert message['channel'] == 'notifications'
    data = json.loads(message['data'])
    assert data['chat_id'] == str(test_user.telegram_id)
    assert "목표 가격 도달: 005930 80000.0 gte (현재가: 81000.0)" in data['text']
    assert "81000.0" in data['text']

    # DB 상태 확인 (알림이 비활성화되었는지)
    triggered_alert = real_db.query(PriceAlert).filter(PriceAlert.id == alert.id).first()
    assert triggered_alert.is_active is False

    # 5. Clean up
    await pubsub.unsubscribe()
    await redis_client.close()
