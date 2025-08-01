import pytest
from unittest.mock import patch, MagicMock
from src.api.main import check_price_alerts_job
from src.api.services.price_alert_service import PriceAlertService

@patch('src.api.main.get_db')
@patch('src.api.main.send_telegram_message')
@patch('src.api.main.get_stock_service')
@patch('src.api.main.get_price_alert_service')
def test_check_price_alerts_job_continues_on_error(mock_get_price_alert_service, mock_get_stock_service, mock_send_telegram, mock_get_db, caplog):
    """
    check_price_alerts_job이 개별 알림 처리 오류 발생 시 중단되지 않고 계속되는지 테스트
    """
    # GIVEN
    # Mock DB와 Service
    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db])
    
    # Mock PriceAlert 객체들
    alert1 = MagicMock(user_id=1, symbol='정상종목', condition='gte', target_price=100)
    alert2 = MagicMock(user_id=2, symbol='오류종목', condition='gte', target_price=200)
    alert3 = MagicMock(user_id=3, symbol='정상종목2', condition='lte', target_price=300)

    # Mock PriceAlertService 인스턴스
    mock_alert_service_instance = MagicMock()
    mock_get_price_alert_service.return_value = mock_alert_service_instance
    mock_alert_service_instance.get_all_active_alerts.return_value = [alert1, alert2, alert3]

    # Mock StockService 인스턴스
    mock_stock_service_instance = MagicMock()
    mock_get_stock_service.return_value = mock_stock_service_instance
    def get_current_price_side_effect(symbol, db):
        if symbol == '오류종목':
            raise ValueError("현재가 조회 실패")
        if symbol == '정상종목':
            return {"current_price": 110, "change": 10, "change_rate": 1.0} # alert1 조건 충족
        if symbol == '정상종목2':
            return {"current_price": 290, "change": -10, "change_rate": -1.0} # alert3 조건 충족
        return {"current_price": 0, "change": 0, "change_rate": 0.0}
    mock_stock_service_instance.get_current_price_and_change.side_effect = get_current_price_side_effect

    # WHEN
    check_price_alerts_job()

    # THEN
    # 오류가 발생했음에도 불구하고, 성공해야 할 알림은 전송되어야 함
    assert mock_send_telegram.call_count == 2
    
    # 오류 로그가 올바르게 기록되었는지 확인
    assert "가격 알림 확인 중 '오류종목' 처리 오류" in caplog.text
    assert "현재가 조회 실패" in caplog.text 