import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.bot.handlers.start import start_command as start
from src.bot.handlers.help import help_command
from src.bot.handlers.register import register
# ... 다른 핸들러들도 여기에 추가 ...

@pytest.fixture
def mock_update():
    """Create a mock Update object."""
    update = MagicMock(spec=Update)
    update.message = AsyncMock()
    update.effective_chat = MagicMock()
    update.effective_chat.id = 12345
    return update

@pytest.fixture
def mock_context():
    """Create a mock ContextTypes.DEFAULT_TYPE object."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    context.args = []
    return context

@pytest.mark.asyncio
async def test_e2e_start_command(mock_update, mock_context):
    """Test the /start command E2E flow."""
    # 1. Setup
    mock_update.message.text = "/start"

    # 2. Execute
    await start(mock_update, mock_context)

    # 3. Assert
    mock_update.message.reply_text.assert_called_once()
    assert "안녕하세요! StocksEye 봇입니다." in mock_update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_e2e_help_command(mock_update, mock_context):
    """Test the /help command E2E flow."""
    # 1. Setup
    mock_update.message.text = "/help"

    # 2. Execute
    await help_command(mock_update, mock_context)

    # 3. Assert
    mock_update.message.reply_text.assert_called_once()
    assert "[StocksEye 봇 도움말]" in mock_update.message.reply_text.call_args[0][0]

# 여기에 다른 명령어들에 대한 E2E 테스트 케이스를 추가합니다.

@pytest.mark.asyncio
@patch('src.common.http_client.session.put')
async def test_e2e_register_command_success(mock_put, mock_update, mock_context):
    """Test the /register command E2E flow for a successful registration."""
    # 1. Setup
    mock_update.message.text = "/register"
    mock_update.effective_user = MagicMock()
    mock_update.effective_user.id = 12345
    mock_update.effective_user.first_name = "Test"
    mock_update.effective_user.last_name = "User"
    mock_update.effective_user.username = "testuser"
    mock_update.effective_chat.id = 12345

    # Mock the API response for successful registration
    mock_api_response = MagicMock()
    mock_api_response.status_code = 200
    mock_api_response.json.return_value = {"message": "User registered successfully"}
    mock_put.return_value = mock_api_response

    # 2. Execute
    await register(mock_update, mock_context)

    # 3. Assert
    # Check if the API was called correctly
    mock_put.assert_called_once()
    called_url = mock_put.call_args[0][0]
    called_json = mock_put.call_args[1]['json']
    assert called_url.endswith("/users/telegram_register")
    assert called_json['telegram_id'] == '12345'
    assert called_json['is_active'] is True

    # Check the bot's response to the user
    mock_update.message.reply_text.assert_called_once_with("알림 수신 동의가 완료되었습니다. (텔레그램 알림 ON)")

