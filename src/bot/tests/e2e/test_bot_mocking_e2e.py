import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import telegram
from telegram import Update, User, Message, Chat
from telegram.ext import CallbackContext

# Import the function with the correct name
from src.bot.handlers.register import register_command

@pytest.mark.asyncio
async def test_register_e2e():
    """E2E test for the register command with mocking."""
    # 1. Setup Mocks
    # Mock Telegram objects
    mock_user = User(id=12345, first_name='Test', is_bot=False, username='testuser')
    mock_chat = Chat(id=12345, type='private')
    mock_message = Message(message_id=1, date=None, chat=mock_chat, from_user=mock_user, text='/register')
    update = Update(update_id=1, message=mock_message)
    context = MagicMock(spec=CallbackContext)

    # Mock the httpx.AsyncClient
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "User registered successfully"}

    mock_async_client = AsyncMock()
    mock_async_client.put.return_value = mock_response

    # 2. Patch the client factory
    with patch('src.common.http_client.get_retry_client') as mock_get_client:
        # The context manager `get_retry_client` should return our mock client
        mock_get_client.return_value.__aenter__.return_value = mock_async_client

        # 3. Run the command handler
        # Use the correct function name
        await register_command(update, context)

    # 4. Assertions
    # Check if the bot sent the correct reply
    context.bot.send_message.assert_called_once_with(
        chat_id=12345,
        text="[알림 동의] 처리되었습니다."
    )

    # Check if the API was called correctly
    mock_async_client.put.assert_called_once_with(
        'http://stockeye-api:8000/api/v1/users/telegram_register',
        json={'telegram_id': '12345', 'is_active': True}
    )