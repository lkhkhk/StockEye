import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock, call
from src.worker.main import update_stock_master_job, update_daily_price_job, check_disclosures_job, check_price_alerts_job
from src.common.models.price_alert import PriceAlert
from src.common.models.user import User

@pytest.mark.asyncio
async def test_update_stock_master_job():
    """종목마스터 정보 갱신 잡"""
    with patch('src.worker.main.get_db') as mock_get_db, \
         patch('src.worker.main.StockService') as mock_stock_service_class:

        # Mock setup
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        mock_stock_service_instance = AsyncMock()
        mock_stock_service_class.return_value = mock_stock_service_instance

        # Run the job
        await update_stock_master_job()

        # Assertions
        mock_get_db.assert_called_once()
        mock_stock_service_class.assert_called_once()
        mock_stock_service_instance.update_stock_master.assert_awaited_once_with(mock_db)

@pytest.mark.asyncio
async def test_update_daily_price_job():
    """일별시세 갱신 잡"""
    with patch('src.worker.main.get_db') as mock_get_db, \
         patch('src.worker.main.StockService') as mock_stock_service_class:

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        mock_stock_service_instance = AsyncMock()
        mock_stock_service_class.return_value = mock_stock_service_instance

        await update_daily_price_job()

        mock_get_db.assert_called_once()
        mock_stock_service_class.assert_called_once()
        mock_stock_service_instance.update_daily_prices.assert_awaited_once_with(mock_db) # Corrected method name

@pytest.mark.asyncio
async def test_check_disclosures_job():
    """최신 공시 확인 및 알림 잡"""
    with patch('src.worker.main.get_db') as mock_get_db, \
         patch('src.worker.main.StockService') as mock_stock_service_class:

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        mock_stock_service_instance = AsyncMock()
        mock_stock_service_class.return_value = mock_stock_service_instance

        await check_disclosures_job()

        mock_get_db.assert_called_once()
        mock_stock_service_class.assert_called_once()
        mock_stock_service_instance.check_and_notify_new_disclosures.assert_awaited_once_with(mock_db)

@pytest.mark.asyncio

async def test_check_price_alerts_job_triggered():
    """
    check_price_alerts_job이 가격 조건 도달 시 알림을 Redis에 발행하는지 테스트
    """
    # --- Mock Setup ---
    
    mock_db = MagicMock()
    
    # Mock PriceAlertService
    mock_alert_service_instance = MagicMock()
    active_alerts = [
        PriceAlert(id=1, user_id=1, symbol='005930', condition='gte', target_price=70000, is_active=True, repeat_interval=None),
        PriceAlert(id=2, user_id=2, symbol='000660', condition='lte', target_price=120000, is_active=True, repeat_interval='daily')
    ]
    mock_alert_service_instance.get_all_active_alerts.return_value = active_alerts

    # Mock StockService
    mock_stock_service_instance = MagicMock()
    def get_current_price_side_effect(symbol, db):
        if symbol == '005930':
            return {"current_price": 75000}
        if symbol == '000660':
            return {"current_price": 110000}
        return {"current_price": None}
    mock_stock_service_instance.get_current_price_and_change.side_effect = get_current_price_side_effect

    # Mock User
    mock_user1 = MagicMock(id=1, telegram_id='12345')
    mock_user2 = MagicMock(id=2, telegram_id='67890')

    # Mock DB query for User
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
            
            if user_id == 1:
                mock_filter_result.first.return_value = mock_user1
            elif user_id == 2:
                mock_filter_result.first.return_value = mock_user2
            else:
                mock_filter_result.first.return_value = None
            return mock_filter_result
        
        mock_query = MagicMock()
        mock_query.filter.side_effect = filter_side_effect
        return mock_query

    mock_db.query.side_effect = mock_query_side_effect

    mock_redis_client_instance = AsyncMock()
    mock_redis_client_instance.publish = AsyncMock()

    with (
          patch('src.worker.main.get_db', return_value=iter([mock_db])),
          patch('src.worker.main.PriceAlertService', return_value=mock_alert_service_instance),
          patch('src.worker.main.StockService', return_value=mock_stock_service_instance),
          patch('src.worker.main.redis.from_url', return_value=mock_redis_client_instance)
      ):
        await check_price_alerts_job()

        # --- Assertions ---
        # Verify services were called correctly
        mock_alert_service_instance.get_all_active_alerts.assert_called_once_with(mock_db)
        assert mock_stock_service_instance.get_current_price_and_change.call_count == 2
        
        # Verify Redis publish calls
        
        
        # Check the content of the published messages
        call1_args = mock_redis_client_instance.publish.await_args_list[0]
        call2_args = mock_redis_client_instance.publish.await_args_list[1]

        # Order of calls is not guaranteed, so we check both possibilities
        expected_msg1_dict = {"chat_id": "12345", "text": "🔔 가격 알림: 005930\n현재가 75000원이 목표가 70000(gte)에 도달했습니다."}
        expected_msg2_dict = {"chat_id": "67890", "text": "🔔 가격 알림: 000660\n현재가 110000원이 목표가 120000(lte)에 도달했습니다."}
        expected_msg1 = json.dumps(expected_msg1_dict, ensure_ascii=False)
        expected_msg2 = json.dumps(expected_msg2_dict, ensure_ascii=False)

        assert call1_args.args[0] == 'notifications'
        assert call2_args.args[0] == 'notifications'
        
        # The order of alerts processing is not guaranteed, so we check if both expected messages were published
        published_messages = {call1_args.args[1], call2_args.args[1]}
        assert expected_msg1 in published_messages
        assert expected_msg2 in published_messages

        # Verify that the non-repeating alert was deactivated
        assert active_alerts[0].is_active is False
        mock_db.add.assert_called_once_with(active_alerts[0])
        mock_db.commit.assert_called()

        # Verify that the repeating alert was NOT deactivated
        assert active_alerts[1].is_active is True
        
        # Check that commit was called at least once
        assert mock_db.commit.call_count >= 1