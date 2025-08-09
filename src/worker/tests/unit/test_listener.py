import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from src.worker.main import notification_listener

@pytest.mark.asyncio
@patch('src.worker.main.redis.from_url')
@patch('src.worker.main.send_telegram_message')
async def test_notification_listener(mock_send_telegram_message, mock_redis_from_url):
    """notification_listener가 Redis 메시지를 수신하고 텔레그램 메시지를 발송하는지 테스트"""
    # Mock Redis connection and pubsub
    mock_pubsub = AsyncMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.get_message = AsyncMock(side_effect=[
        {"channel": b'notifications', "data": json.dumps({"chat_id": "12345", "text": "Test message 1"})},
        {"channel": b'notifications', "data": json.dumps({"chat_id": "67890", "text": "Test message 2"})},
        None # To stop the loop after processing messages
    ])

    
    mock_redis_from_url.return_value = AsyncMock()
    mock_redis_from_url.return_value.pubsub.return_value = mock_pubsub

    # Set TELEGRAM_BOT_TOKEN environment variable for the test
    with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token'}):
        await notification_listener()

    # Assertions
    mock_redis_from_url.assert_called_once_with('redis://localhost', decode_responses=True)
    mock_redis_conn.pubsub.assert_called_once()
    mock_pubsub.subscribe.assert_awaited_once_with('notifications')
    
    # Verify send_telegram_message was called with correct arguments
    mock_send_telegram_message.assert_has_calls([
        call("12345", "Test message 1"),
        call("67890", "Test message 2")
    ])
    assert mock_send_telegram_message.await_count == 2

    # Verify that the listener attempts to get messages multiple times
    assert mock_pubsub.get_message.call_count >= 3 # At least 3 calls (2 messages + 1 None to stop)

    # Verify r.close() is called
    mock_redis_from_url.return_value.close.assert_awaited_once()