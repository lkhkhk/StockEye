import pytest
from unittest.mock import patch, MagicMock
from src.api.services.stock_service import StockService
from src.common.exceptions import DartApiError
import logging

@pytest.fixture
def stock_service():
    """StockService 인스턴스를 생성하는 pytest fixture."""
    return StockService()

@patch('src.api.services.stock_service.dart_get_all_stocks')
def test_update_stock_master_handles_dart_api_error(mock_dart_get_all_stocks, stock_service):
    """
    update_stock_master가 DART API 오류를 정상적으로 처리하는지 테스트합니다.
    """
    # GIVEN
    error_message = "DART API 사용량 초과"
    mock_dart_get_all_stocks.side_effect = DartApiError(error_message, status_code="020")
    mock_db = MagicMock()

    # WHEN
    result = stock_service.update_stock_master(mock_db)

    # THEN
    assert result['success'] is False
    assert error_message in result['error']
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_called_once()

def test_update_daily_prices_continues_on_db_error_refactored(stock_service, caplog):
    """
    _update_prices_for_stocks가 DB 저장 오류 시 중단되지 않고 계속되는지 테스트합니다.
    (리팩토링된 구조에 맞춰 수정)
    """
    # GIVEN
    mock_stock_normal1 = MagicMock()
    mock_stock_normal1.symbol = '정상종목1'
    mock_stock_error = MagicMock()
    mock_stock_error.symbol = '오류종목'
    mock_stock_normal2 = MagicMock()
    mock_stock_normal2.symbol = '정상종목2'
    stocks = [mock_stock_normal1, mock_stock_error, mock_stock_normal2]
    
    mock_db = MagicMock()
    
    def db_add_side_effect(instance):
        if instance.symbol == '오류종목':
            raise ValueError("DB 저장 실패")
        pass

    mock_db.add.side_effect = db_add_side_effect
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # WHEN
    with caplog.at_level(logging.ERROR):
        result = stock_service._update_prices_for_stocks(mock_db, stocks)

    # THEN
    assert result['success'] is True
    assert result['updated_count'] == 60 # 2개 종목 * 30일
    assert result['errors'] == ['오류종목']
    
    assert mock_db.add.call_count == 60
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()
    
    assert "일별시세 갱신 중 '오류종목' 처리에서 오류 발생" in caplog.text
    assert "DB 저장 실패" in caplog.text 