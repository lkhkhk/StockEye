import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.worker.main import check_price_alerts_job
from src.common.services.price_alert_service import PriceAlertService

# 이 테스트는 잡이 텔레그램 메시지를 직접 보내는 이전 구현을 기반으로 합니다.
# 새 구현은 Redis에 발행합니다.
# 임포트 및 패치를 업데이트하겠지만, 이 테스트는 다시 작성되거나 삭제되어야 할 수 있습니다.
# 현재로서는 리팩토링 검증의 일환으로 임포트 오류 수정에 중점을 둡니다.

@pytest.mark.asyncio
@patch('src.worker.main.get_db') # MOCK: get_db 함수
@patch('src.worker.main.redis.from_url') # MOCK: redis.from_url 함수
@patch('src.worker.main.StockService') # MOCK: StockService 클래스
@patch('src.worker.main.PriceAlertService') # MOCK: PriceAlertService 클래스
async def test_check_price_alerts_job_continues_on_error(mock_get_price_alert_service, mock_get_stock_service, mock_redis_from_url, mock_get_db, caplog):
    """
    check_price_alerts_job이 개별 알림 처리 오류 발생 시 중단되지 않고 계속되는지 테스트
    """
    # GIVEN
    # MagicMock: DB 세션 객체를 모의합니다. 동기적으로 동작합니다.
    mock_db = MagicMock()
    # mock_get_db (MagicMock) 호출 시 mock_db를 반환하는 이터레이터를 반환하도록 설정합니다.
    mock_get_db.return_value = iter([mock_db]) # The job uses a generator
    
    # MOCK: PriceAlert 객체들
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    alert1 = MagicMock(user_id=1, symbol='정상종목', condition='gte', target_price=100)
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    alert2 = MagicMock(user_id=2, symbol='오류종목', condition='gte', target_price=200)
    # MagicMock: PriceAlert 모델의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    alert3 = MagicMock(user_id=3, symbol='정상종목2', condition='lte', target_price=300)

    # MOCK: PriceAlertService 인스턴스
    # MagicMock: PriceAlertService의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_alert_service_instance = MagicMock()
    # mock_get_price_alert_service (MagicMock) 호출 시 mock_alert_service_instance를 반환하도록 설정합니다.
    mock_get_price_alert_service.return_value = mock_alert_service_instance
    # mock_alert_service_instance.get_all_active_alerts (MagicMock) 호출 시 모의 알림 목록을 반환하도록 설정합니다.
    mock_alert_service_instance.get_all_active_alerts.return_value = [alert1, alert2, alert3]

    # MOCK: StockService 인스턴스
    # MagicMock: StockService의 인스턴스를 모의합니다. 동기적으로 동작합니다.
    mock_stock_service_instance = MagicMock()
    # mock_get_stock_service (MagicMock) 호출 시 mock_stock_service_instance를 반환하도록 설정합니다.
    mock_get_stock_service.return_value = mock_stock_service_instance
    # mock_stock_service_instance.get_current_price_and_change (MagicMock) 호출 시 side_effect를 설정합니다.
    def get_current_price_side_effect(symbol, db):
        if symbol == '오류종목':
            raise ValueError("현재가 조회 실패")
        if symbol == '정상종목':
            return {"current_price": 110, "change": 10, "change_rate": 1.0} # alert1 조건 충족
        if symbol == '정상종목2':
            return {"current_price": 290, "change": -10, "change_rate": -1.0} # alert3 조건 충족
        return {"current_price": 0, "change": 0, "change_rate": 0.0}
    mock_stock_service_instance.get_current_price_and_change.side_effect = get_current_price_side_effect

    # MOCK: Redis 클라이언트
    # AsyncMock: Redis 클라이언트 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_redis_client = AsyncMock()
    # AsyncMock: publish 메서드를 모의합니다. 비동기적으로 동작합니다.
    mock_redis_client.publish = AsyncMock()
    # mock_redis_from_url (MagicMock) 호출 시 mock_redis_client를 반환하도록 설정합니다.
    mock_redis_from_url.return_value = mock_redis_client

    # MOCK: User 쿼리
    # mock_db.query 호출 시 side_effect를 설정합니다.
    def mock_query_side_effect(model):
        mock_filter_result = MagicMock()
        def filter_side_effect(criterion):
            # Extract user_id from the criterion (e.g., User.id == 1)
            # This is a simplified parsing, might need more robust logic for complex criteria
            user_id = None
            if hasattr(criterion, 'right') and hasattr(criterion.right, 'value'):
                user_id = criterion.right.value
            elif hasattr(criterion, 'value'): # For simple cases like User.id == 1
                user_id = criterion.value
            
            # MagicMock: first 메서드를 모의합니다. 동기적으로 동작합니다.
            mock_filter_result.first.return_value = MagicMock(telegram_id='12345')
            return mock_filter_result
        # MagicMock: filter 메서드를 모의합니다. 동기적으로 동작합니다.
        mock_query = MagicMock()
        mock_query.filter.side_effect = filter_side_effect
        return mock_query
    mock_db.query.side_effect = mock_query_side_effect


    # WHEN
    await check_price_alerts_job()

    # THEN
    # 오류가 발생했음에도 불구하고, 성공해야 할 알림은 전송(publish)되어야 함
    # mock_redis_client.publish (AsyncMock)가 두 번 호출되었는지 확인합니다.
    assert mock_redis_client.publish.await_count == 2
    
    # 오류 로그가 올바르게 기록되었는지 확인
    assert "가격 알림 확인 중 '오류종목' 처리 오류" in caplog.text
    assert "현재가 조회 실패" in caplog.text