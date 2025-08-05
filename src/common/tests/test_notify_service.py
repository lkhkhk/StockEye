import pytest
from unittest.mock import patch, MagicMock

from src.common.notify_service import send_telegram_message

@patch('src.common.http_client.get_http_client')
def test_send_telegram_message_success(mock_get_http_client):
    """Test that a Telegram message is sent successfully."""
    # 1. Setup
    mock_http_client = MagicMock()
    mock_get_http_client.return_value = mock_http_client
    
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None # No error
    mock_http_client.post.return_value = mock_response
    
    chat_id = 12345
    message = "Hello, test!"

    # 2. Execute
    send_telegram_message(chat_id, message)

    # 3. Assert
    mock_http_client.post.assert_called_once()
    called_url = mock_http_client.post.call_args[0][0]
    called_json = mock_http_client.post.call_args[1]['json']
    
    assert "/sendMessage" in called_url
    assert called_json['chat_id'] == chat_id
    assert called_json['text'] == message

@patch('src.common.http_client.get_http_client')
def test_send_telegram_message_failure(mock_get_http_client):
    """Test that the function handles API errors gracefully."""
    # 1. Setup
    mock_http_client = MagicMock()
    mock_get_http_client.return_value = mock_http_client
    mock_http_client.post.side_effect = Exception("API Error")

    # 2. Execute & Assert
    # The function should catch the exception and not crash
    try:
        send_telegram_message(12345, "test")
    except Exception as e:
        pytest.fail(f"send_telegram_message raised an unexpected exception: {e}")
