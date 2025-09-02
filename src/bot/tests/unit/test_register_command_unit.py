import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import telegram
from telegram import Update, User, Message, Chat
from telegram.ext import CallbackContext
import httpx

# Import the function with the correct name
from src.bot.handlers.register import register_command

@pytest.mark.asyncio
async def test_register_command_unit():
    """Unit test for the register command handler."""
    # 1. Setup Mocks for Telegram objects
    mock_user = User(id=12345, first_name='Test', is_bot=False, username='testuser')
    mock_chat = Chat(id=12345, type='private')
    update = AsyncMock(spec=Update)
    update.effective_user = mock_user
    update.effective_chat = mock_chat
    update.message = AsyncMock(spec=Message)
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=CallbackContext)

    # Mock the httpx.Response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "User registered successfully"}

    # 2. Patch httpx.AsyncClient.put directly
    # This patches the 'put' method on any instance of httpx.AsyncClient
    with patch('httpx.AsyncClient.put') as mock_put:
        mock_put.return_value = mock_response

        # 3. Run the command handler
        await register_command(update, context)

    # 4. Assertions
    # Check if the bot sent the correct reply
    update.message.reply_text.assert_called_once_with(
        "알림 등록이 완료되었습니다. 이제부터 주가 알림을 받을 수 있습니다."
    )

    # Check if the API was called correctly
    mock_put.assert_called_once_with(
        '/api/v1/users/telegram_register',
        json={'telegram_id': '12345', 'is_active': True}
    )