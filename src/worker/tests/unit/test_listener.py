import pytest
import json
import redis
import os
from unittest.mock import patch, AsyncMock, MagicMock, call
import asyncio
from src.worker.main import notification_listener

@pytest.mark.asyncio
@patch('src.worker.main.send_telegram_message') # MOCK: send_telegram_message 함수
async def test_notification_listener(mock_send_telegram_message):
    """notification_listener가 Redis 메시지를 수신하고 텔레그램 메시지를 발송하는지 테스트"""
    # MOCK: Redis pubsub 객체
    # AsyncMock: Redis pubsub 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_pubsub = AsyncMock()
    # AsyncMock: subscribe 메서드를 모의합니다. 비동기적으로 동작합니다.
    mock_pubsub.subscribe = AsyncMock()
    # AsyncMock: get_message 메서드를 모의합니다. 비동기적으로 동작합니다.
    # Provide messages, but no None to stop the loop. The task will be cancelled externally.
    mock_pubsub.get_message = AsyncMock(side_effect=[
        {"channel": b'notifications', "data": json.dumps({"chat_id": "12345", "text": "Test message 1"})},
        {"channel": b'notifications', "data": json.dumps({"chat_id": "67890", "text": "Test message 2"})},
    ])

    # MOCK: Redis connection 객체
    # AsyncMock: Redis connection 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_redis_conn = AsyncMock(spec=redis.Redis)
    # MagicMock: pubsub 메서드를 모의합니다. 동기적으로 동작하며 mock_pubsub을 반환합니다.
    # (이전 오류 수정: r.pubsub()은 동기 메서드이므로 MagicMock 사용)
    mock_redis_conn.pubsub = MagicMock(return_value=mock_pubsub)
    # AsyncMock: close 메서드를 모의합니다. 비동기적으로 동작합니다.
    mock_redis_conn.close = AsyncMock()

    # Get the same REDIS_HOST that the application uses
    redis_host = os.getenv("REDIS_HOST", "localhost")

    # MOCK: src.worker.main.redis.from_url 함수
    # from_url 함수를 모의하여 실제 Redis 연결을 방지합니다.
    with patch('src.worker.main.redis.from_url', new_callable=AsyncMock, return_value=mock_redis_conn) as mock_redis_from_url:
        # Create the listener as a task to control its lifecycle
        listener_task = asyncio.create_task(notification_listener())
        
        # Allow some time for messages to be processed
        # 2 messages + 2 sleeps (0.1s each) = 0.2s minimum. Add buffer.
        await asyncio.sleep(0.5)

        # Cancel the task to break the loop
        listener_task.cancel()
        
        # Wait for the task to finish (and handle CancelledError)
        try:
            await listener_task
        except asyncio.CancelledError:
            pass # Expected

        # Assertions
        # mock_redis_from_url (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        mock_redis_from_url.assert_awaited_once_with(f'redis://{redis_host}', decode_responses=True)
        # mock_redis_conn.pubsub (MagicMock)가 한 번 호출되었는지 확인합니다.
        mock_redis_conn.pubsub.assert_called_once()
        # mock_pubsub.subscribe (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        mock_pubsub.subscribe.assert_awaited_once_with('notifications')
        
        # Verify send_telegram_message was called with correct arguments
        # mock_send_telegram_message (AsyncMock)가 올바른 인자로 호출되었는지 확인합니다.
        mock_send_telegram_message.assert_has_calls([
            call("12345", "Test message 1"),
            call("67890", "Test message 2")
        ])
        assert mock_send_telegram_message.await_count == 2

        # Verify that the listener attempts to get messages multiple times
        # It should try to get messages until cancelled, so more than just the messages provided
        assert mock_pubsub.get_message.call_count >= 2 

        # Verify r.close() is called
        # mock_redis_conn.close (AsyncMock)가 한 번 호출되었는지 확인합니다.
        mock_redis_conn.close.assert_awaited_once()