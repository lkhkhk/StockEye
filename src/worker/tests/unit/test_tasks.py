import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta

from src.worker import tasks
from src.common.models.price_alert import PriceAlert
from src.common.models.user import User
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice

# Test for update_stock_master_task
@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.StockMasterService')
@patch('src.worker.tasks.redis.from_url')
@patch('src.worker.tasks.asyncio.run')
def test_update_stock_master_task(mock_asyncio_run, mock_redis_from_url, mock_stock_master_service_class, mock_get_db):
    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db])
    mock_stock_master_service_instance = MagicMock()
    # Since the service method is async, the instance should be an AsyncMock if we want to await it
    # but we are mocking asyncio.run, so the instance can be a regular MagicMock
    mock_stock_master_service_class.return_value = mock_stock_master_service_instance
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client

    tasks.update_stock_master_task(chat_id=12345)

    mock_get_db.assert_called_once()
    mock_stock_master_service_class.assert_called_once()
    mock_asyncio_run.assert_called_once_with(mock_stock_master_service_instance.update_stock_master(mock_db))
    mock_redis_from_url.assert_called_once_with(f"redis://{tasks.REDIS_HOST}")
    assert mock_redis_client.publish.call_count == 1
    mock_redis_client.close.assert_called_once()

# Test for update_daily_price_task
@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.MarketDataService')
@patch('src.worker.tasks.redis.from_url')
@patch('src.worker.tasks.asyncio.run')
def test_update_daily_price_task(mock_asyncio_run, mock_redis_from_url, mock_market_data_service_class, mock_get_db):
    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db])
    mock_market_data_service_instance = MagicMock()
    mock_market_data_service_class.return_value = mock_market_data_service_instance
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client

    tasks.update_daily_price_task(chat_id=12345)

    mock_get_db.assert_called_once()
    mock_market_data_service_class.assert_called_once()
    mock_asyncio_run.assert_called_once_with(mock_market_data_service_instance.update_daily_prices(mock_db))
    mock_redis_from_url.assert_called_once_with(f"redis://{tasks.REDIS_HOST}")
    assert mock_redis_client.publish.call_count == 1
    mock_redis_client.close.assert_called_once()

# Test for check_disclosures_task
@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.DisclosureService')
@patch('src.worker.tasks.redis.from_url')
@patch('src.worker.tasks.asyncio.run')
def test_check_disclosures_task(mock_asyncio_run, mock_redis_from_url, mock_disclosure_service_class, mock_get_db):
    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db])
    mock_disclosure_service_instance = MagicMock()
    mock_disclosure_service_class.return_value = mock_disclosure_service_instance
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client

    tasks.check_disclosures_task(chat_id=12345)

    mock_get_db.assert_called_once()
    mock_disclosure_service_class.assert_called_once()
    mock_asyncio_run.assert_called_once_with(mock_disclosure_service_instance.check_and_notify_new_disclosures(db=mock_db))
    mock_redis_from_url.assert_called_once_with(f"redis://{tasks.REDIS_HOST}")
    assert mock_redis_client.publish.call_count == 1
    mock_redis_client.close.assert_called_once()

# Test for check_price_alerts_task
@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.PriceAlertService')
@patch('src.worker.tasks.MarketDataService')
@patch('src.worker.tasks.redis.from_url')
def test_check_price_alerts_task(mock_redis_from_url, mock_market_data_service_class, mock_price_alert_service_class, mock_get_db):
    # --- Mock Setup ---
    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db])

    mock_price_alert_service_instance = MagicMock()
    mock_price_alert_service_class.return_value = mock_price_alert_service_instance
    active_alerts = [
        MagicMock(symbol='005930', condition='gte', target_price=70000, user_id=1, repeat_interval=None),
        MagicMock(symbol='000660', condition='lte', target_price=120000, user_id=2, repeat_interval='daily'),
    ]
    mock_price_alert_service_instance.get_all_active_alerts.return_value = active_alerts

    mock_market_data_service_instance = MagicMock()
    mock_market_data_service_class.return_value = mock_market_data_service_instance
    def get_current_price_side_effect(symbol, db):
        if symbol == '005930': return {"current_price": 75000}
        if symbol == '000660': return {"current_price": 110000}
        return {"current_price": None}
    mock_market_data_service_instance.get_current_price_and_change.side_effect = get_current_price_side_effect

    def mock_query_side_effect(model):
        if model == User:
            mock_filter_result = MagicMock()
            def filter_side_effect(criterion):
                user_id = criterion.right.value
                mock_user = MagicMock(telegram_id=f'tid_{user_id}')
                mock_filter_result.first.return_value = mock_user
                return mock_filter_result
            mock_query = MagicMock()
            mock_query.filter.side_effect = filter_side_effect
            return mock_query
        return MagicMock()
    mock_db.query.side_effect = mock_query_side_effect

    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client

    # --- Run Task ---
    tasks.check_price_alerts_task(chat_id=12345)

    # --- Assertions ---
    assert mock_price_alert_service_instance.get_all_active_alerts.call_count == 1
    assert mock_market_data_service_instance.get_current_price_and_change.call_count == 2
    # 2 alerts triggered + 1 completion message
    assert mock_redis_client.publish.call_count == 3 
    mock_db.commit.assert_called()

# Test for run_historical_price_update_task
@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.redis.from_url')
@patch('src.worker.tasks.StockMasterService')
@patch('src.worker.tasks.yf.download')
def test_run_historical_price_update_task(mock_yf_download, mock_stock_master_service_class, mock_redis_from_url, mock_get_db):
    # Mock DB and Redis
    # Create specific db mock instances for each scenario
    db_mock_specific = MagicMock()
    db_mock_all = MagicMock()
    # Configure side_effect to return the specific db mock for each call
    mock_get_db.side_effect = [iter([db_mock_specific]), iter([db_mock_all])]
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client

    # Mock StockMasterService
    mock_stock_master_service_instance = MagicMock()
    mock_stock_master_service_class.return_value = mock_stock_master_service_instance

    # Test data
    chat_id = 12345
    start_date_str = "2023-01-01"
    end_date_str = "2023-01-07"
    
    # Mock yfinance download data
    mock_data_specific = MagicMock()
    mock_data_specific.empty = False
    mock_data_specific.iterrows.return_value = [
        (datetime(2023, 1, 2), {'Open': 100.0, 'High': 105.0, 'Low': 99.0, 'Close': 104.0, 'Volume': 1000}),
        (datetime(2023, 1, 3), {'Open': 104.0, 'High': 106.0, 'Low': 103.0, 'Close': 105.0, 'Volume': 1200}),
    ]
    mock_data_all_stock1 = MagicMock()
    mock_data_all_stock1.empty = False
    mock_data_all_stock1.iterrows.return_value = [
        (datetime(2023, 1, 2), {'Open': 200.0, 'High': 205.0, 'Low': 199.0, 'Close': 204.0, 'Volume': 2000}),
        (datetime(2023, 1, 3), {'Open': 204.0, 'High': 206.0, 'Low': 203.0, 'Close': 205.0, 'Volume': 2200}),
    ]
    mock_data_all_stock2 = MagicMock()
    mock_data_all_stock2.empty = False
    mock_data_all_stock2.iterrows.return_value = [
        (datetime(2023, 1, 2), {'Open': 300.0, 'High': 305.0, 'Low': 299.0, 'Close': 304.0, 'Volume': 3000}),
        (datetime(2023, 1, 3), {'Open': 304.0, 'High': 306.0, 'Low': 303.0, 'Close': 305.0, 'Volume': 3200}),
    ]

    # Test case 1: Update for a specific stock
    specific_stock = MagicMock(symbol="005930", name="삼성전자", is_delisted=False)
    mock_stock_master_service_instance.search_stocks.return_value = [specific_stock]
    
    db_mock_specific.query.return_value.filter.return_value.first.return_value = None # No existing price
    db_mock_specific.query.return_value.filter.return_value.all.return_value = [specific_stock] # For the all stocks query
    mock_yf_download.return_value = mock_data_specific # Set return value for specific stock

    tasks.run_historical_price_update_task(chat_id, start_date_str, end_date_str, stock_identifier="005930")

    mock_stock_master_service_instance.search_stocks.assert_called_once_with(keyword="005930", db=db_mock_specific, limit=1)
    mock_yf_download.assert_called_once_with("005930.KS", start=datetime(2023, 1, 1), end=datetime(2023, 1, 8))
    assert db_mock_specific.add.call_count == 2 # Two new daily prices
    assert db_mock_specific.commit.call_count == 1
    assert mock_redis_client.publish.call_count == 1 # Completion message
    mock_redis_client.close.assert_called_once()

    # Reset mocks for next test case
    mock_yf_download.reset_mock()
    mock_stock_master_service_instance.search_stocks.reset_mock()
    db_mock_specific.add.reset_mock()
    db_mock_specific.commit.reset_mock()
    mock_redis_client.publish.reset_mock()
    mock_redis_client.close.reset_mock()

    # Test case 2: Update for all stocks
    all_stocks = [
        MagicMock(symbol="005930", name="삼성전자", is_delisted=False),
        MagicMock(symbol="000660", name="SK하이닉스", is_delisted=False),
    ]
    db_mock_all.query.return_value.filter.return_value.all.return_value = all_stocks
    db_mock_all.query.return_value.filter.return_value.first.return_value = None # No existing price
    mock_yf_download.side_effect = [mock_data_all_stock1, mock_data_all_stock2] # Return mock_data for each stock

    tasks.run_historical_price_update_task(chat_id, start_date_str, end_date_str)

    mock_stock_master_service_instance.search_stocks.assert_not_called()
    assert mock_yf_download.call_count == 2 # Called for each stock
    mock_yf_download.assert_has_calls([
        call("005930.KS", start=datetime(2023, 1, 1), end=datetime(2023, 1, 8)),
        call("000660.KS", start=datetime(2023, 1, 1), end=datetime(2023, 1, 8)),
    ])
    assert db_mock_all.add.call_count == 4 # Two new daily prices for each of two stocks
    assert db_mock_all.commit.call_count == 1 # Only one final commit
    assert mock_redis_client.publish.call_count == 1 # Only one final completion message
    mock_redis_client.close.assert_called_once()


# --- Helper Function Tests (Phase 2) ---

def test_publish_message_success():
    """_publish_message가 Redis에 메시지를 성공적으로 게시하는지 테스트"""
    # GIVEN
    mock_redis_client = MagicMock()
    chat_id = 12345
    text = "테스트 메시지"
    
    # WHEN
    tasks._publish_message(mock_redis_client, chat_id, text)
    
    # THEN
    mock_redis_client.publish.assert_called_once()
    call_args = mock_redis_client.publish.call_args[0]
    assert call_args[0] == "notifications"
    
    # Verify JSON structure
    published_data = json.loads(call_args[1])
    assert published_data["chat_id"] == chat_id
    assert published_data["text"] == text


def test_publish_message_no_chat_id():
    """_publish_message가 chat_id가 None일 때 메시지를 게시하지 않는지 테스트"""
    # GIVEN
    mock_redis_client = MagicMock()
    chat_id = None
    text = "테스트 메시지"
    
    # WHEN
    tasks._publish_message(mock_redis_client, chat_id, text)
    
    # THEN
    mock_redis_client.publish.assert_not_called()


def test_publish_message_redis_error():
    """_publish_message가 Redis 에러를 처리하는지 테스트"""
    # GIVEN
    mock_redis_client = MagicMock()
    mock_redis_client.publish.side_effect = Exception("Redis connection error")
    chat_id = 12345
    text = "테스트 메시지"
    
    # WHEN - should not raise exception
    tasks._publish_message(mock_redis_client, chat_id, text)
    
    # THEN
    mock_redis_client.publish.assert_called_once()


@patch('src.worker.tasks._publish_message')
def test_publish_completion_message_success(mock_publish_message):
    """_publish_completion_message가 성공 메시지를 올바르게 포맷하는지 테스트"""
    # GIVEN
    mock_redis_client = MagicMock()
    chat_id = 12345
    job_name = "테스트 작업"
    success = True
    start_time = datetime(2025, 12, 2, 10, 0, 0)
    details = "추가 정보"
    
    # WHEN
    with patch('src.worker.tasks.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 12, 2, 10, 0, 5)  # 5 seconds later
        tasks._publish_completion_message(mock_redis_client, chat_id, job_name, success, start_time, details)
    
    # THEN
    mock_publish_message.assert_called_once()
    call_args = mock_publish_message.call_args[0]
    assert call_args[0] == mock_redis_client
    assert call_args[1] == chat_id
    
    message = call_args[2]
    assert "✅" in message
    assert job_name in message
    assert "성공" in message
    assert "5.00초" in message
    assert details in message


@patch('src.worker.tasks._publish_message')
def test_publish_completion_message_failure(mock_publish_message):
    """_publish_completion_message가 실패 메시지를 올바르게 포맷하는지 테스트"""
    # GIVEN
    mock_redis_client = MagicMock()
    chat_id = 12345
    job_name = "테스트 작업"
    success = False
    start_time = datetime(2025, 12, 2, 10, 0, 0)
    
    # WHEN
    with patch('src.worker.tasks.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 12, 2, 10, 0, 3)  # 3 seconds later
        tasks._publish_completion_message(mock_redis_client, chat_id, job_name, success, start_time)
    
    # THEN
    mock_publish_message.assert_called_once()
    call_args = mock_publish_message.call_args[0]
    
    message = call_args[2]
    assert "❌" in message
    assert job_name in message
    assert "실패" in message
    assert "3.00초" in message


@patch('src.worker.tasks._publish_message')
def test_publish_completion_message_no_chat_id(mock_publish_message):
    """_publish_completion_message가 chat_id가 None일 때 메시지를 게시하지 않는지 테스트"""
    # GIVEN
    mock_redis_client = MagicMock()
    chat_id = None
    job_name = "테스트 작업"
    success = True
    start_time = datetime.now()
    
    # WHEN
    tasks._publish_completion_message(mock_redis_client, chat_id, job_name, success, start_time)
    
    # THEN
    mock_publish_message.assert_not_called()
