import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock, call
from datetime import datetime

from src.worker import tasks
from src.common.models.price_alert import PriceAlert
from src.common.models.user import User

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