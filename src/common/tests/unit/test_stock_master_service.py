import pytest
from unittest.mock import MagicMock, patch, AsyncMock, ANY
from src.common.services.stock_master_service import StockMasterService
from src.common.models.stock_master import StockMaster
from src.common.utils.exceptions import DartApiError
from datetime import datetime
import logging

@pytest.fixture
def stock_master_service():
    """StockMasterService 인스턴스를 생성하는 pytest fixture"""
    return StockMasterService()

def test_get_stock_by_symbol_found(stock_master_service):
    """
    get_stock_by_symbol: DB에서 종목을 성공적으로 찾았을 때, 해당 StockMaster 객체를 반환하는지 테스트
    """
    # Given
    mock_db_session = MagicMock()
    symbol_to_find = "005930"
    expected_stock = StockMaster(symbol=symbol_to_find, name="삼성전자")

    mock_db_session.query.return_value.filter.return_value.first.return_value = expected_stock

    # When
    result = stock_master_service.get_stock_by_symbol(symbol_to_find, mock_db_session)

    # Then
    assert result == expected_stock
    assert result.name == "삼성전자"
    mock_db_session.query.assert_called_once_with(StockMaster)
    mock_db_session.query.return_value.filter.assert_called_once()


def test_get_stock_by_symbol_not_found(stock_master_service):
    """
    get_stock_by_symbol: DB에서 종목을 찾지 못했을 때, None을 반환하는지 테스트
    """
    # Given
    mock_db_session = MagicMock()
    symbol_to_find = "999999" # 존재하지 않는 심볼

    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # When
    result = stock_master_service.get_stock_by_symbol(symbol_to_find, mock_db_session)

    # Then
    assert result is None
    mock_db_session.query.assert_called_once_with(StockMaster)
    mock_db_session.query.return_value.filter.assert_called_once()

def test_get_stock_by_name_found(stock_master_service):
    """
    get_stock_by_name: DB에서 이름으로 종목을 성공적으로 찾았을 때, 해당 StockMaster 객체를 반환하는지 테스트
    """
    # Given
    mock_db_session = MagicMock()
    name_to_find = "삼성전자"
    expected_stock = StockMaster(symbol="005930", name=name_to_find)

    mock_db_session.query.return_value.filter.return_value.first.return_value = expected_stock

    # When
    result = stock_master_service.get_stock_by_name(name_to_find, mock_db_session)

    # Then
    assert result == expected_stock
    assert result.symbol == "005930"
    mock_db_session.query.assert_called_once_with(StockMaster)
    mock_db_session.query.return_value.filter.assert_called_once()

def test_get_stock_by_name_not_found(stock_master_service):
    """
    get_stock_by_name: DB에서 이름으로 종목을 찾지 못했을 때, None을 반환하는지 테스트
    """
    # Given
    mock_db_session = MagicMock()
    name_to_find = "없는회사"

    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # When
    result = stock_master_service.get_stock_by_name(name_to_find, mock_db_session)

    # Then
    assert result is None
    mock_db_session.query.assert_called_once_with(StockMaster)
    mock_db_session.query.return_value.filter.assert_called_once()

def test_search_stocks_found(stock_master_service):
    """
    search_stocks: DB에서 키워드로 종목들을 성공적으로 찾았을 때, 객체 리스트를 반환하는지 테스트
    """
    # Given
    mock_db_session = MagicMock()
    keyword = "삼성"
    expected_stocks = [
        StockMaster(symbol="005930", name="삼성전자"),
        StockMaster(symbol="006400", name="삼성SDI"),
    ]

    mock_db_session.query.return_value.filter.return_value.limit.return_value.all.return_value = expected_stocks

    # When
    result = stock_master_service.search_stocks(keyword, mock_db_session)

    # Then
    assert result == expected_stocks
    assert len(result) == 2
    mock_db_session.query.assert_called_once_with(StockMaster)
    mock_db_session.query.return_value.filter.assert_called_once()
    mock_db_session.query.return_value.filter.return_value.limit.assert_called_once_with(10)

def test_search_stocks_not_found(stock_master_service):
    """
    search_stocks: DB에서 키워드로 종목을 찾지 못했을 때, 빈 리스트를 반환하는지 테스트
    """
    # Given
    mock_db_session = MagicMock()
    keyword = "없는회사"

    mock_db_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []

    # When
    result = stock_master_service.search_stocks(keyword, mock_db_session)

    # Then
    assert result == []
    mock_db_session.query.assert_called_once_with(StockMaster)
    mock_db_session.query.return_value.filter.assert_called_once()
    mock_db_session.query.return_value.filter.return_value.limit.assert_called_once_with(10)

@pytest.mark.asyncio
@patch('src.common.services.stock_master_service.dart_get_all_stocks')
async def test_update_stock_master_update_existing(mock_dart_get_all_stocks, stock_master_service):
    """
    update_stock_master: DART API로 기존 종목 정보를 성공적으로 업데이트하는 경우
    """
    # Given
    mock_db_session = MagicMock()
    existing_stock = StockMaster(symbol="005930", name="삼성전자 구이름", corp_code="123")
    mock_db_session.query.return_value.filter.return_value.first.return_value = existing_stock

    dart_data = [{"symbol": "005930", "name": "삼성전자 새이름", "corp_code": "123"}]
    mock_dart_get_all_stocks.return_value = dart_data

    # When
    result = await stock_master_service.update_stock_master(mock_db_session)

    # Then
    assert result["success"] is True
    assert result["updated_count"] == 1
    assert existing_stock.name == "삼성전자 새이름"
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
@patch('src.common.services.stock_master_service.dart_get_all_stocks')
async def test_update_stock_master_add_new(mock_dart_get_all_stocks, stock_master_service):
    """
    update_stock_master: DART API로 새 종목 정보를 성공적으로 추가하는 경우
    """
    # Given
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    dart_data = [{"symbol": "000660", "name": "SK하이닉스", "corp_code": "456"}]
    mock_dart_get_all_stocks.return_value = dart_data

    # When
    result = await stock_master_service.update_stock_master(mock_db_session)

    # Then
    assert result["success"] is True
    assert result["updated_count"] == 1
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
@patch('src.common.services.stock_master_service.dart_get_all_stocks', new_callable=AsyncMock)
async def test_update_stock_master_dart_api_error(mock_dart_get_all_stocks, stock_master_service):
    """
    update_stock_master: DART API 호출 시 예외가 발생하는 경우
    """
    # Given
    mock_db_session = MagicMock()
    error_message = "API Error"
    mock_dart_get_all_stocks.side_effect = DartApiError(error_message)

    # When
    result = await stock_master_service.update_stock_master(mock_db_session)
    
    # Then
    assert result["success"] is False
    assert result["error"] == error_message
    mock_db_session.rollback.assert_not_called()

@pytest.mark.asyncio
@patch('src.common.services.stock_master_service.dart_get_all_stocks')
async def test_update_stock_master_update_existing_datetime(mock_dart_get_all_stocks, stock_master_service):
    """
    update_stock_master: 기존 종목 업데이트 시 updated_at이 갱신되는지 확인
    """
    # Given
    mock_db_session = MagicMock()
    initial_updated_at = datetime(2023, 1, 1, 10, 0, 0)
    existing_stock = StockMaster(symbol="005930", name="삼성전자 구이름", corp_code="123", updated_at=initial_updated_at)
    mock_db_session.query.return_value.filter.return_value.first.return_value = existing_stock

    dart_data = [{"symbol": "005930", "name": "삼성전자 새이름", "corp_code": "123"}]
    mock_dart_get_all_stocks.return_value = dart_data

    # When
    result = await stock_master_service.update_stock_master(mock_db_session)

    # Then
    assert result["success"] is True
    assert existing_stock.updated_at > initial_updated_at
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
@patch('src.common.services.stock_master_service.dart_get_all_stocks')
async def test_update_stock_master_add_new_datetime(mock_dart_get_all_stocks, stock_master_service):
    """
    update_stock_master: 새 종목 추가 시 created_at과 updated_at이 설정되는지 확인
    """
    # Given
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    dart_data = [{"symbol": "000660", "name": "SK하이닉스", "corp_code": "456"}]
    mock_dart_get_all_stocks.return_value = dart_data

    # When
    result = await stock_master_service.update_stock_master(mock_db_session)

    # Then
    assert result["success"] is True
    mock_db_session.add.assert_called_once()
    added_stock = mock_db_session.add.call_args[0][0]
    assert isinstance(added_stock.created_at, datetime)
    assert isinstance(added_stock.updated_at, datetime)
    assert added_stock.created_at <= datetime.now()
    assert added_stock.updated_at <= datetime.now()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_update_stock_master_general_exception(stock_master_service):
    """
    update_stock_master: 일반 예외 발생 시 롤백 처리 확인
    """
    # Given
    mock_db_session = MagicMock()
    mock_db_session.commit.side_effect = Exception("DB commit error")

    # When
    result = await stock_master_service.update_stock_master(mock_db_session, use_dart=False)

    # Then
    assert result["success"] is False
    assert "DB commit error" in result["error"]
    mock_db_session.rollback.assert_called_once()

def test_get_stock_by_symbol_logging(stock_master_service, caplog):
    """
    get_stock_by_symbol: 로깅이 올바르게 동작하는지 테스트
    """
    # Given
    mock_db_session = MagicMock()
    symbol_found = "005930"
    symbol_not_found = "999999"
    expected_stock = StockMaster(symbol=symbol_found, name="삼성전자")
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [expected_stock, None]

    # When & Then
    with caplog.at_level(logging.DEBUG):
        stock_master_service.get_stock_by_symbol(symbol_found, mock_db_session)
        assert f"종목 발견: 삼성전자 ({symbol_found})" in caplog.text
        caplog.clear()
        stock_master_service.get_stock_by_symbol(symbol_not_found, mock_db_session)
        assert f"종목 없음: {symbol_not_found}" in caplog.text

def test_get_stock_by_name_logging(stock_master_service, caplog):
    """
    get_stock_by_name: 로깅이 올바르게 동작하는지 테스트
    """
    # Given
    mock_db_session = MagicMock()
    name_found = "삼성전자"
    name_not_found = "없는회사"
    expected_stock = StockMaster(symbol="005930", name=name_found)
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [expected_stock, None]

    # When & Then
    with caplog.at_level(logging.DEBUG):
        stock_master_service.get_stock_by_name(name_found, mock_db_session)
        assert f"종목 발견: 삼성전자 (005930)" in caplog.text
        caplog.clear()
        stock_master_service.get_stock_by_name(name_not_found, mock_db_session)
        assert f"종목 없음: {name_not_found}" in caplog.text

@pytest.mark.asyncio
@patch('src.common.services.stock_master_service.dart_get_all_stocks', new_callable=AsyncMock)
async def test_update_stock_master_dart_api_error_logging(mock_dart_get_all_stocks, stock_master_service, caplog):
    """
    update_stock_master: DART API 호출 시 예외가 발생할 때 로깅이 올바르게 동작하는지 테스트
    """
    # Given
    mock_db_session = MagicMock()
    error_message = "API Error"
    mock_dart_get_all_stocks.side_effect = DartApiError(error_message)

    # When
    with caplog.at_level(logging.ERROR):
        result = await stock_master_service.update_stock_master(mock_db_session)
    
    # Then
    assert result["success"] is False
    assert result["error"] == error_message
    assert "DART API 연동 실패" in caplog.text
