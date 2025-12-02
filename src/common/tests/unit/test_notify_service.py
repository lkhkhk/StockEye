import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.common.services.notify_service import send_telegram_message
import os

@pytest.mark.asyncio
@patch('src.common.services.notification.telegram_channel.Bot')
@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token"})
async def test_send_telegram_message_success(mock_bot_class):
    """텔레그램 메시지가 성공적으로 전송되는 경우를 테스트합니다."""
    # Given
    chat_id = 12345
    message_text = "Test message"
    
    mock_bot_instance = AsyncMock()
    mock_bot_class.return_value = mock_bot_instance
    mock_message = MagicMock()
    mock_message.message_id = 999
    mock_bot_instance.send_message.return_value = mock_message

    # When
    await send_telegram_message(chat_id, message_text)

    # Then
    mock_bot_instance.send_message.assert_awaited_once_with(chat_id=chat_id, text=message_text)

@pytest.mark.asyncio
@patch('src.common.services.notification.telegram_channel.Bot')
@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token"})
async def test_send_telegram_message_failure(mock_bot_class, caplog):
    """텔레그램 API 에러 발생 시, 함수가 예외를 잘 처리하는지 테스트합니다."""
    # Given
    chat_id = 12345
    message_text = "Test message"
    
    mock_bot_instance = AsyncMock()
    mock_bot_class.return_value = mock_bot_instance
    mock_bot_instance.send_message.side_effect = Exception("Telegram API Error")

    # When
    await send_telegram_message(chat_id, message_text)

    # Then
    assert "[텔레그램 알림 전송 실패]" in caplog.text

@pytest.mark.asyncio
@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""})
async def test_send_telegram_message_no_token(caplog):
    """TELEGRAM_BOT_TOKEN이 설정되지 않았을 경우를 테스트합니다."""
    # Given
    chat_id = 12345
    message_text = "Test message"

    # When
    await send_telegram_message(chat_id, message_text)

    # Then
    assert "TELEGRAM_BOT_TOKEN is not set" in caplog.text

@pytest.mark.asyncio
@patch('src.common.services.notification.telegram_channel.Bot')
@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token"})
@pytest.mark.parametrize("message_text", ["", " \t\n"])
async def test_send_telegram_message_empty_message(mock_bot_class, message_text, caplog):
    """메시지가 비어있거나 공백일 경우를 테스트합니다."""
    # Given
    chat_id = 12345
    
    mock_bot_instance = AsyncMock()
    mock_bot_class.return_value = mock_bot_instance

    # When
    await send_telegram_message(chat_id, message_text)

    # Then
    mock_bot_instance.send_message.assert_not_awaited()
    assert "Attempted to send an empty or whitespace-only message" in caplog.text

@pytest.mark.asyncio
@patch('src.common.services.notification.telegram_channel.Bot')
@patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token"})
async def test_send_telegram_message_no_message_object_returned(mock_bot_class, caplog):
    """send_message가 None을 반환하는 경우를 테스트합니다."""
    # Given
    chat_id = 12345
    message_text = "Test message"
    
    mock_bot_instance = AsyncMock()
    mock_bot_class.return_value = mock_bot_instance
    mock_bot_instance.send_message.return_value = None

    # When
    await send_telegram_message(chat_id, message_text)

    # Then
    assert "no message object was returned" in caplog.text
