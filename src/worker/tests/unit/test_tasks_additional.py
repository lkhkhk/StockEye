import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta
import pandas as pd

from src.worker import tasks
from src.common.models.price_alert import PriceAlert
from src.common.models.user import User
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice


# ===== Exception Handling Tests =====

@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.StockMasterService')
@patch('src.worker.tasks.redis.from_url')
@patch('src.worker.tasks.asyncio.run')
def test_update_stock_master_task_exception(mock_asyncio_run, mock_redis_from_url, mock_stock_master_service_class, mock_get_db):
    """update_stock_master_task 예외 처리 테스트"""
    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db])
    mock_stock_master_service_instance = MagicMock()
    mock_stock_master_service_class.return_value = mock_stock_master_service_instance
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client
    
    # Simulate exception
    mock_asyncio_run.side_effect = Exception("Service error")
    
    tasks.update_stock_master_task(chat_id=12345)
    
    # Verify completion message was sent with failure status
    assert mock_redis_client.publish.call_count == 1
    call_args = mock_redis_client.publish.call_args[0]
    published_data = json.loads(call_args[1])
    assert "❌" in published_data["text"]
    mock_redis_client.close.assert_called_once()


@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.MarketDataService')
@patch('src.worker.tasks.redis.from_url')
@patch('src.worker.tasks.asyncio.run')
def test_update_daily_price_task_exception(mock_asyncio_run, mock_redis_from_url, mock_market_data_service_class, mock_get_db):
    """update_daily_price_task 예외 처리 테스트"""
    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db])
    mock_market_data_service_instance = MagicMock()
    mock_market_data_service_class.return_value = mock_market_data_service_instance
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client
    
    # Simulate exception
    mock_asyncio_run.side_effect = Exception("Market data error")
    
    tasks.update_daily_price_task(chat_id=12345)
    
    # Verify failure handling
    assert mock_redis_client.publish.call_count == 1
    call_args = mock_redis_client.publish.call_args[0]
    published_data = json.loads(call_args[1])
    assert "❌" in published_data["text"]
    mock_redis_client.close.assert_called_once()


@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.DisclosureService')
@patch('src.worker.tasks.redis.from_url')
@patch('src.worker.tasks.asyncio.run')
def test_check_disclosures_task_exception(mock_asyncio_run, mock_redis_from_url, mock_disclosure_service_class, mock_get_db):
    """check_disclosures_task 예외 처리 테스트"""
    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db])
    mock_disclosure_service_instance = MagicMock()
    mock_disclosure_service_class.return_value = mock_disclosure_service_instance
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client
    
    # Simulate exception
    mock_asyncio_run.side_effect = Exception("Disclosure API error")
    
    tasks.check_disclosures_task(chat_id=12345)
    
    # Verify failure handling
    assert mock_redis_client.publish.call_count == 1
    call_args = mock_redis_client.publish.call_args[0]
    published_data = json.loads(call_args[1])
    assert "❌" in published_data["text"]
    mock_redis_client.close.assert_called_once()


@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.PriceAlertService')
@patch('src.worker.tasks.MarketDataService')
@patch('src.worker.tasks.redis.from_url')
def test_check_price_alerts_task_symbol_exception(mock_redis_from_url, mock_market_data_service_class, mock_price_alert_service_class, mock_get_db):
    """check_price_alerts_task 심볼별 예외 처리 테스트"""
    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db])
    
    mock_price_alert_service_instance = MagicMock()
    mock_price_alert_service_class.return_value = mock_price_alert_service_instance
    active_alerts = [
        MagicMock(symbol='005930', condition='gte', target_price=70000, user_id=1, repeat_interval=None),
        MagicMock(symbol='INVALID', condition='lte', target_price=120000, user_id=2, repeat_interval='daily'),
    ]
    mock_price_alert_service_instance.get_all_active_alerts.return_value = active_alerts
    
    mock_market_data_service_instance = MagicMock()
    mock_market_data_service_class.return_value = mock_market_data_service_instance
    
    def get_current_price_side_effect(symbol, db):
        if symbol == '005930':
            return {"current_price": 75000}
        if symbol == 'INVALID':
            raise Exception("Invalid symbol")
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
    
    tasks.check_price_alerts_task(chat_id=12345)
    
    # Should handle exception and continue with other symbols
    assert mock_db.rollback.called
    assert mock_db.commit.called


# ===== Conditional Logic Tests =====

@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.redis.from_url')
@patch('src.worker.tasks.StockMasterService')
@patch('src.worker.tasks.yf.download')
def test_run_historical_price_update_task_no_stock_found(mock_yf_download, mock_stock_master_service_class, mock_redis_from_url, mock_get_db):
    """run_historical_price_update_task 종목 없음 케이스 테스트"""
    db_mock = MagicMock()
    mock_get_db.return_value = iter([db_mock])
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client
    
    mock_stock_master_service_instance = MagicMock()
    mock_stock_master_service_class.return_value = mock_stock_master_service_instance
    mock_stock_master_service_instance.search_stocks.return_value = []  # No stock found
    
    chat_id = 12345
    start_date_str = "2023-01-01"
    end_date_str = "2023-01-07"
    
    tasks.run_historical_price_update_task(chat_id, start_date_str, end_date_str, stock_identifier="INVALID")
    
    # Should publish error message + completion message
    assert mock_redis_client.publish.call_count >= 1
    # Check that error message was published
    first_call_args = mock_redis_client.publish.call_args_list[0][0]
    published_data = json.loads(first_call_args[1])
    assert "찾을 수 없습니다" in published_data["text"]


@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.redis.from_url')
@patch('src.worker.tasks.StockMasterService')
@patch('src.worker.tasks.yf.download')
def test_run_historical_price_update_task_no_stocks_in_db(mock_yf_download, mock_stock_master_service_class, mock_redis_from_url, mock_get_db):
    """run_historical_price_update_task DB에 종목 없음 케이스 테스트"""
    db_mock = MagicMock()
    mock_get_db.return_value = iter([db_mock])
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client
    
    mock_stock_master_service_instance = MagicMock()
    mock_stock_master_service_class.return_value = mock_stock_master_service_instance
    
    db_mock.query.return_value.filter.return_value.all.return_value = []  # No stocks
    
    chat_id = 12345
    start_date_str = "2023-01-01"
    end_date_str = "2023-01-07"
    
    tasks.run_historical_price_update_task(chat_id, start_date_str, end_date_str)
    
    # Should publish error message + completion message
    assert mock_redis_client.publish.call_count >= 1
    # Check that error message was published
    first_call_args = mock_redis_client.publish.call_args_list[0][0]
    published_data = json.loads(first_call_args[1])
    assert "처리할 주식 데이터가 없습니다" in published_data["text"]


@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.redis.from_url')
@patch('src.worker.tasks.StockMasterService')
@patch('src.worker.tasks.yf.download')
def test_run_historical_price_update_task_empty_data(mock_yf_download, mock_stock_master_service_class, mock_redis_from_url, mock_get_db):
    """run_historical_price_update_task 데이터 없음 (상장 폐지) 케이스 테스트"""
    db_mock = MagicMock()
    mock_get_db.return_value = iter([db_mock])
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client
    
    mock_stock_master_service_instance = MagicMock()
    mock_stock_master_service_class.return_value = mock_stock_master_service_instance
    
    delisted_stock = MagicMock(symbol="999999", name="상장폐지종목", is_delisted=False)
    db_mock.query.return_value.filter.return_value.all.return_value = [delisted_stock]
    
    # Empty data from yfinance
    mock_data = MagicMock()
    mock_data.empty = True
    mock_yf_download.return_value = mock_data
    
    chat_id = 12345
    start_date_str = "2023-01-01"
    end_date_str = "2023-01-07"
    
    tasks.run_historical_price_update_task(chat_id, start_date_str, end_date_str)
    
    # Should mark stock as delisted
    assert delisted_stock.is_delisted == True
    assert db_mock.add.called


@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.redis.from_url')
@patch('src.worker.tasks.StockMasterService')
@patch('src.worker.tasks.yf.download')
def test_run_historical_price_update_task_update_existing_price(mock_yf_download, mock_stock_master_service_class, mock_redis_from_url, mock_get_db):
    """run_historical_price_update_task 기존 가격 업데이트 케이스 테스트"""
    db_mock = MagicMock()
    mock_get_db.return_value = iter([db_mock])
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client
    
    mock_stock_master_service_instance = MagicMock()
    mock_stock_master_service_class.return_value = mock_stock_master_service_instance
    
    stock = MagicMock(symbol="005930", name="삼성전자", is_delisted=False)
    db_mock.query.return_value.filter.return_value.all.return_value = [stock]
    
    # Existing price
    existing_price = MagicMock()
    db_mock.query.return_value.filter.return_value.first.return_value = existing_price
    
    mock_data = MagicMock()
    mock_data.empty = False
    mock_data.iterrows.return_value = [
        (datetime(2023, 1, 2), {'Open': 100.0, 'High': 105.0, 'Low': 99.0, 'Close': 104.0, 'Volume': 1000}),
    ]
    mock_yf_download.return_value = mock_data
    
    chat_id = 12345
    start_date_str = "2023-01-01"
    end_date_str = "2023-01-07"
    
    tasks.run_historical_price_update_task(chat_id, start_date_str, end_date_str)
    
    # Should update existing price
    assert existing_price.open == 100.0
    assert existing_price.close == 104.0


@patch('src.worker.tasks.get_db')
@patch('src.worker.tasks.redis.from_url')
@patch('src.worker.tasks.StockMasterService')
@patch('src.worker.tasks.yf.download')
def test_run_historical_price_update_task_progress_messages(mock_yf_download, mock_stock_master_service_class, mock_redis_from_url, mock_get_db):
    """run_historical_price_update_task 진행 상황 메시지 테스트"""
    db_mock = MagicMock()
    mock_get_db.return_value = iter([db_mock])
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client
    
    mock_stock_master_service_instance = MagicMock()
    mock_stock_master_service_class.return_value = mock_stock_master_service_instance
    
    # Create 50 stocks to trigger progress message
    stocks = [MagicMock(symbol=f"{i:06d}", name=f"종목{i}", is_delisted=False) for i in range(50)]
    db_mock.query.return_value.filter.return_value.all.return_value = stocks
    db_mock.query.return_value.filter.return_value.first.return_value = None
    
    mock_data = MagicMock()
    mock_data.empty = False
    mock_data.iterrows.return_value = [
        (datetime(2023, 1, 2), {'Open': 100.0, 'High': 105.0, 'Low': 99.0, 'Close': 104.0, 'Volume': 1000}),
    ]
    mock_yf_download.return_value = mock_data
    
    chat_id = 12345
    start_date_str = "2023-01-01"
    end_date_str = "2023-01-07"
    
    tasks.run_historical_price_update_task(chat_id, start_date_str, end_date_str)
    
    # Should publish progress message (at 50 stocks) + completion message
    assert mock_redis_client.publish.call_count == 2
    
    # Check progress message
    first_call_args = mock_redis_client.publish.call_args_list[0][0]
    progress_data = json.loads(first_call_args[1])
    assert "진행 중" in progress_data["text"]
    assert "50" in progress_data["text"]
