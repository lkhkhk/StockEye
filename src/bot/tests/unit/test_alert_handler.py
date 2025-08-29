import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext
import httpx

from src.bot.handlers.alert import (
    set_price_alert,
    alert_add,
    alert_list,
    alert_remove
)

@pytest.fixture
def mock_update_context():
    """Provides a mock Update and CallbackContext for tests."""
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=CallbackContext)
    context.user_data = {}

    # Mock the API call inside ensure_user_registered decorator
    mock_register_response = AsyncMock(spec=httpx.Response)
    mock_register_response.status_code = 200
    mock_register_response.raise_for_status = MagicMock()
    mock_register_response.json.return_value = {"message": "User registered successfully"}

    # Patch get_retry_client globally for the decorator's API call
    # This patch needs to be outside the test function, or managed carefully.
    # A better long-term solution might be a separate fixture for decorator patching.
    with patch('src.common.http_client.get_retry_client') as mock_get_client_decorator:
        mock_client_decorator = AsyncMock(spec=httpx.AsyncClient)
        mock_client_decorator.put.return_value = mock_register_response
        mock_get_client_decorator.return_value.__aenter__.return_value = mock_client_decorator
        yield update, context

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_set_price_alert') # Patch the internal helper
async def test_set_price_alert_success(mock_api_call, mock_update_context):
    """Test successful price alert setting with robust mocking."""
    update, context = mock_update_context
    context.args = ["005930", "80000", "이상"]

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock() # Mock the method that gets called
    mock_api_call.return_value = mock_response

    await set_price_alert(update, context)

    update.message.reply_text.assert_awaited_once_with("✅ '005930'의 가격 알림을 80000.0원 이상으로 설정했습니다.")

@pytest.mark.asyncio
async def test_set_price_alert_invalid_args(mock_update_context):
    """Test error message for invalid arguments."""
    update, context = mock_update_context
    context.args = ["005930", "abc"]

    await set_price_alert(update, context)

    update.message.reply_text.assert_awaited_once()
    assert "사용법" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_search_stocks')
async def test_alert_add_multiple_results(mock_api_call, mock_update_context):
    """Test alert_add with multiple search results."""
    update, context = mock_update_context
    context.args = ["카카오"]
    
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [
        {"symbol": "035720", "name": "카카오"},
        {"symbol": "035420", "name": "카카오게임즈"}
    ]
    mock_api_call.return_value = mock_response.json.return_value # FIX 2: Return the list directly

    await alert_add(update, context)

    update.message.reply_text.assert_awaited_once()
    # The text is in kwargs when reply_markup is used
    assert "어떤 종목을 추가" in update.message.reply_text.call_args.kwargs['text'] # FIX 1: Revert to kwargs
    assert isinstance(update.message.reply_text.call_args.kwargs['reply_markup'], InlineKeyboardMarkup)

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_get_alerts')
async def test_alert_list_success(mock_api_call, mock_update_context):
    """Test successful alert list retrieval."""
    update, context = mock_update_context

    # _api_get_alerts should return a list directly, not an AsyncMock of a response
    mock_api_call.return_value = [
        {"id": 1, "symbol": "005930", "name": "삼성전자", "target_price": 80000.0, "condition": "gte", "is_active": True, "repeat_interval": "daily"}
    ]

    await alert_list(update, context)

    update.message.reply_text.assert_awaited_once()
    # Correctly access the positional argument for the text
    sent_text = update.message.reply_text.call_args.kwargs['text'] # Changed to kwargs
    assert "삼성전자" in sent_text
    assert "80000.0원 이상" in sent_text

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_delete_alert')
async def test_alert_remove_success(mock_api_call, mock_update_context):
    """Test successful alert removal."""
    update, context = mock_update_context
    context.user_data['alert_map'] = {'1': 101}
    context.args = ["1"]

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_api_call.return_value = mock_response

    await alert_remove(update, context)

    update.message.reply_text.assert_awaited_once_with("알림 1번이 삭제되었습니다.")
