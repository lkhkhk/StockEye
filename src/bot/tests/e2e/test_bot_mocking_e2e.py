import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import telegram
from telegram import Update, User, Message, Chat
from telegram.ext import CallbackContext
import httpx

# Import the function with the correct name
from src.bot.handlers.register import register_command

@pytest.mark.asyncio
async def test_register_e2e():
    """E2E test for the register command with mocking."""
    # 1. Setup Mocks
    # Mock Telegram objects
    mock_user = User(id=12345, first_name='Test', is_bot=False, username='testuser')
    mock_chat = Chat(id=12345, type='private')
    update = AsyncMock(spec=Update)
    update.effective_user = mock_user
    update.effective_chat = mock_chat
    update.message = AsyncMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=CallbackContext)

    # Mock the httpx.AsyncClient
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "User registered successfully"}

    mock_async_client = AsyncMock()
    mock_async_client.put.return_value = mock_response

    # 2. Patch the client factory
    # 2. Patch the client factory
    with patch('src.common.utils.http_client.get_retry_client') as mock_get_retry_client:
        mock_client_instance = AsyncMock(spec=httpx.AsyncClient)
        mock_client_instance.put.return_value = mock_response
        mock_get_retry_client.return_value.__aenter__.return_value = mock_client_instance

        # 3. Run the command handler
        # Use the correct function name
        await register_command(update, context)

    # 4. Assertions
    # Check if the bot sent the correct reply
    update.message.reply_text.assert_called_once_with(
        "알림 등록이 완료되었습니다. 이제부터 주가 알림을 받을 수 있습니다."
    )

    # Check if the API was called correctly
    mock_async_client.put.assert_called_once_with(
        'http://stockeye-api:8000/api/v1/users/telegram_register',
        json={'telegram_id': '12345', 'is_active': True}
    )