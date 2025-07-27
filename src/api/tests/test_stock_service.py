import pytest
from unittest.mock import patch, MagicMock
import logging
from src.api.services.stock_service import StockService
from src.common.exceptions import DartApiError
from datetime import date, timedelta, datetime

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

@patch('src.api.services.stock_service.datetime')
def test_update_daily_prices_continues_on_db_error(mock_dt, stock_service, caplog):
    """
    _update_prices_for_stocks가 DB 저장 오류 시 중단되지 않고 계속되는지 테스트합니다.
    (datetime.now()를 모킹하여 테스트의 결정성을 확보)
    """
    # GIVEN: datetime.now()가 항상 고정된 날짜를 반환하도록 설정
    fixed_now = datetime(2023, 10, 27)
    mock_dt.now.return_value = fixed_now
    
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

    mock_db.add.side_effect = db_add_side_effect
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # WHEN
    with caplog.at_level(logging.ERROR):
        result = stock_service._update_prices_for_stocks(mock_db, stocks)

    # THEN
    assert result['success'] is True
    assert result['updated_count'] == 60  # 2개 정상 종목 * 30일
    assert result['errors'] == ['오류종목']
    assert mock_db.add.call_count == 61 # 정상 60회 + 오류 시도 1회
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()
    assert "일별시세 갱신 중 '오류종목' 처리에서 오류 발생" in caplog.text 