import pytest
from unittest.mock import MagicMock, patch, ANY
import pandas as pd
from src.common.services.market_data_service import MarketDataService
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice
from datetime import datetime, timedelta
import logging

@pytest.fixture
def market_data_service():
    """MarketDataService 인스턴스를 생성하는 pytest fixture"""
    return MarketDataService()

def test_get_current_price_and_change_success(market_data_service):
    """
    get_current_price_and_change: 가격 정보가 2개 있어 등락률 계산에 성공하는 경우
    """
    # Given
    mock_db_session = MagicMock()
    symbol = "005930"
    prices = [
        DailyPrice(symbol=symbol, date=datetime.now().date(), close=75000),
        DailyPrice(symbol=symbol, date=(datetime.now() - timedelta(days=1)).date(), close=70000)
    ]
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = prices

    # When
    result = market_data_service.get_current_price_and_change(symbol, mock_db_session)

    # Then
    assert result["current_price"] == 75000
    assert result["change"] == 5000
    assert result["change_rate"] == (5000 / 70000) * 100

def test_get_current_price_and_change_one_price(market_data_service):
    """
    get_current_price_and_change: 가격 정보가 1개만 있어 등락률 계산에 실패하는 경우
    """
    # Given
    mock_db_session = MagicMock()
    symbol = "005930"
    prices = [DailyPrice(symbol=symbol, date=datetime.now().date(), close=75000)]
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = prices

    # When
    result = market_data_service.get_current_price_and_change(symbol, mock_db_session)

    # Then
    assert result["current_price"] == 75000
    assert result["change"] is None
    assert result["change_rate"] is None

def test_get_current_price_and_change_no_price(market_data_service):
    """
    get_current_price_and_change: 가격 정보가 전혀 없는 경우
    """
    # Given
    mock_db_session = MagicMock()
    symbol = "005930"
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    # When
    result = market_data_service.get_current_price_and_change(symbol, mock_db_session)

    # Then
    assert result["current_price"] is None
    assert result["change"] is None
    assert result["change_rate"] is None

def test_get_daily_prices_success(market_data_service):
    """
    get_daily_prices: DB에서 특정 기간의 가격 정보들을 성공적으로 조회하는 경우
    """
    # Given
    mock_db_session = MagicMock()
    symbol = "005930"
    days = 5
    expected_prices = [
        DailyPrice(symbol=symbol, date=(datetime.now() - timedelta(days=i)).date(), close=75000 - i*100) for i in range(days)
    ]
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = expected_prices

    # When
    result = market_data_service.get_daily_prices(symbol, mock_db_session, days=days)

    # Then
    assert result == expected_prices
    assert len(result) == days
    mock_db_session.query.assert_called_once_with(DailyPrice)


def test_get_daily_prices_no_data(market_data_service):
    """
    get_daily_prices: 해당 기간에 가격 정보가 없어 빈 리스트를 반환하는 경우
    """
    # Given
    mock_db_session = MagicMock()
    symbol = "005930"
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    # When
    result = market_data_service.get_daily_prices(symbol, mock_db_session)

    # Then
    assert result == []
    mock_db_session.query.assert_called_once_with(DailyPrice)

@pytest.mark.asyncio
@patch('src.common.services.market_data_service.yf.download')
async def test_update_daily_prices_success(mock_yf_download, market_data_service):
    """
    update_daily_prices: yfinance에서 성공적으로 데이터를 가져와 DB에 저장하는 경우
    """
    # Given
    mock_db_session = MagicMock()
    mock_stocks = [StockMaster(symbol='005930', name='삼성전자')]
    mock_db_session.query.return_value.offset.return_value.limit.return_value.all.side_effect = [mock_stocks, []]

    mock_data = {
        'Open': [100], 'High': [110], 'Low': [90], 'Close': [105], 'Volume': [1000]
    }
    mock_df = pd.DataFrame(mock_data, index=[pd.to_datetime('2023-01-01')])
    mock_yf_download.return_value = mock_df

    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # When
    result = await market_data_service.update_daily_prices(mock_db_session)

    # Then
    assert result['success'] is True
    assert result['updated_count'] == 1
    assert len(result['errors']) == 0
    mock_yf_download.assert_called_once_with('005930.KS', start=ANY, end=ANY)
    mock_db_session.bulk_save_objects.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
@patch('src.common.services.market_data_service.yf.download')
async def test_update_daily_prices_yfinance_exception(mock_yf_download, market_data_service):
    """
    update_daily_prices: yfinance 호출 시 예외가 발생하여 해당 종목을 건너뛰는 경우
    """
    # Given
    mock_db_session = MagicMock()
    mock_stocks = [StockMaster(symbol='005930', name='삼성전자')]
    mock_db_session.query.return_value.offset.return_value.limit.return_value.all.side_effect = [mock_stocks, []]
    
    mock_yf_download.side_effect = Exception("yfinance error")

    # When
    result = await market_data_service.update_daily_prices(mock_db_session)

    # Then
    assert result['success'] is True
    assert result['updated_count'] == 0
    assert result['errors'] == ['005930']
    mock_db_session.bulk_save_objects.assert_not_called()

@pytest.mark.asyncio
@patch('src.common.services.market_data_service.yf.download')
async def test_update_daily_prices_yfinance_empty(mock_yf_download, market_data_service):
    """
    update_daily_prices: yfinance가 비어있는 데이터프레임을 반환하는 경우
    """
    # Given
    mock_db_session = MagicMock()
    mock_stocks = [StockMaster(symbol='005930', name='삼성전자')]
    mock_db_session.query.return_value.offset.return_value.limit.return_value.all.side_effect = [mock_stocks, []]
    
    mock_yf_download.return_value = pd.DataFrame()

    # When
    result = await market_data_service.update_daily_prices(mock_db_session)

    # Then
    assert result['success'] is True
    assert result['updated_count'] == 0
    assert '005930' in result['errors']
    mock_db_session.bulk_save_objects.assert_not_called()

@pytest.mark.asyncio
@patch('src.common.services.market_data_service.yf.download')
async def test_update_daily_prices_no_prices_to_add_rollback(mock_yf_download, market_data_service):
    """
    update_daily_prices: prices_to_add가 비어있어 db.rollback()이 호출되는 경우
    """
    # Given
    mock_db_session = MagicMock()
    mock_stocks = [StockMaster(symbol='005930', name='삼성전자')]
    mock_db_session.query.return_value.offset.return_value.limit.return_value.all.side_effect = [mock_stocks, []]
    
    # yfinance가 데이터를 반환하지만, 모든 가격이 이미 존재한다고 가정하여 prices_to_add가 비어있도록 함
    mock_data = {
        'Open': [100], 'High': [110], 'Low': [90], 'Close': [105], 'Volume': [1000]
    }
    mock_df = pd.DataFrame(mock_data, index=[pd.to_datetime('2023-01-01')])
    mock_yf_download.return_value = mock_df

    # 모든 가격이 이미 존재한다고 가정
    mock_db_session.query.return_value.filter.return_value.first.return_value = DailyPrice() 

    # When
    result = await market_data_service.update_daily_prices(mock_db_session)

    # Then
    assert result['success'] is True
    assert result['updated_count'] == 0
    assert len(result['errors']) == 0
    mock_db_session.bulk_save_objects.assert_not_called()
    mock_db_session.rollback.assert_called_once()

def test_get_current_price_and_change_previous_close_zero(market_data_service):
    """
    get_current_price_and_change: 전일 종가가 0일 때 change_rate가 0.0으로 계산되는지 테스트
    """
    # Given
    mock_db_session = MagicMock()
    symbol = "005930"
    prices = [
        DailyPrice(symbol=symbol, date=datetime.now().date(), close=75000),
        DailyPrice(symbol=symbol, date=(datetime.now() - timedelta(days=1)).date(), close=0)
    ]
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = prices

    # When
    result = market_data_service.get_current_price_and_change(symbol, mock_db_session)

    # Then
    assert result["current_price"] == 75000
    assert result["change"] == 75000
    assert result["change_rate"] == 0.0

@pytest.mark.asyncio
async def test_update_daily_prices_main_exception(market_data_service, caplog):
    """
    update_daily_prices: 메인 try 블록에서 예외가 발생하여 전체 작업이 실패하는 경우
    """
    # Given
    mock_db_session = MagicMock()
    error_message = "Main exception"
    mock_db_session.query.side_effect = Exception(error_message)

    # When
    result = await market_data_service.update_daily_prices(mock_db_session)

    # Then
    assert result['success'] is False
    assert error_message in result['error']
    mock_db_session.rollback.assert_called_once()
    assert "일별시세 갱신 작업 전체 실패" in caplog.text