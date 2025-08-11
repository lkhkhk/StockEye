import pytest
from unittest.mock import patch, AsyncMock
from src.common.notify_service import send_telegram_message
import httpx

@pytest.mark.asyncio
@patch('src.common.notify_service.http_client')
async def test_send_telegram_message_success(mock_http_client):
    """Test that send_telegram_message successfully sends a message."""
    # 1. Setup
    chat_id = "12345"
    message = "Test message"
    
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    
    # Configure the mock client's post method
    mock_http_client.post.return_value = mock_response

    # 2. Execute
    await send_telegram_message(chat_id, message)

    # 3. Assert
    mock_http_client.post.assert_awaited_once()
    
    # Check the URL and data passed to post
    args, kwargs = mock_http_client.post.call_args
    assert f"sendMessage" in args[0]
    assert kwargs['json'] == {'chat_id': chat_id, 'text': message}


@pytest.mark.asyncio
@patch('src.common.notify_service.http_client')
async def test_send_telegram_message_failure(mock_http_client):
    """Test that send_telegram_message handles API errors gracefully."""
    # 1. Setup
    chat_id = "12345"
    message = "Test message"

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 500
    # Configure raise_for_status to raise an exception
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=AsyncMock(), response=mock_response
    )
    
    mock_http_client.post.return_value = mock_response

    # 2. Execute & Assert
    # We expect this to run without raising an exception in the caller
    await send_telegram_message(chat_id, message)

    # 3. Assert
    mock_http_client.post.assert_awaited_once()
    # The function should catch the exception and log it, not re-raise it.
    # So, the main assertion is that the call completes without error.
