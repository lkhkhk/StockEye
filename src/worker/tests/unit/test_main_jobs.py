import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.worker.main import check_price_alerts_job
from src.common.services.price_alert_service import PriceAlertService

# This test seems to be based on an old implementation where the job directly sends telegram messages.
# The new implementation publishes to Redis.
# I will update the imports and patches, but this test might need to be rewritten or deleted.
# For now, I'm focusing on fixing the import errors as part of the refactoring verification.

@pytest.mark.asyncio
@patch('src.worker.main.get_db')
@patch('src.worker.main.redis.from_url') # Assuming redis is used for notifications
@patch('src.worker.main.StockService')
@patch('src.worker.main.PriceAlertService')
async def test_check_price_alerts_job_continues_on_error(mock_get_price_alert_service, mock_get_stock_service, mock_redis_from_url, mock_get_db, caplog):
    """
    check_price_alerts_job이 개별 알림 처리 오류 발생 시 중단되지 않고 계속되는지 테스트
    """
    # GIVEN
    # Mock DB와 Service
    mock_db = MagicMock()
    mock_get_db.return_value = iter([mock_db]) # The job uses a generator
    
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

    # Mock Redis
    mock_redis_client = AsyncMock()
    mock_redis_client.publish = AsyncMock()
    mock_redis_from_url.return_value = mock_redis_client

    # Mock User query
    def mock_query_side_effect(model):
        mock_filter_result = MagicMock()
        def filter_side_effect(criterion):
            mock_filter_result.first.return_value = MagicMock(telegram_id='12345')
            return mock_filter_result
        mock_query = MagicMock()
        mock_query.filter.side_effect = filter_side_effect
        return mock_query
    mock_db.query.side_effect = mock_query_side_effect


    # WHEN
    await check_price_alerts_job()

    # THEN
    # 오류가 발생했음에도 불구하고, 성공해야 할 알림은 전송(publish)되어야 함
    assert mock_redis_client.publish.await_count == 2
    
    # 오류 로그가 올바르게 기록되었는지 확인
    assert "가격 알림 확인 중 '오류종목' 처리 오류" in caplog.text
    assert "현재가 조회 실패" in caplog.text