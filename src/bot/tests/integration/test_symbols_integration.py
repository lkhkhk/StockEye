import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, User, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from src.bot.handlers.symbols import symbols_command, symbols_pagination_callback, symbols_search_command, symbols_search_pagination_callback, symbol_info_command, symbol_info_callback
from src.bot.handlers.symbols import _api_get_symbols, _api_search_symbols, _api_get_symbol_by_code # Import internal API helpers for mocking

# --- Constants ---
API_URL = "http://stockeye-api:8000/api/v1"

# --- Fixtures ---

@pytest.fixture
def mock_update_context():
    """테스트를 위한 Update 및 Context 모의 객체를 제공합니다."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.from_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return update, context

# --- Integration Tests for symbols_command ---

@pytest.mark.asyncio
async def test_symbols_command_success_integration():
    """
    Test that the symbols command successfully fetches and displays symbols.
    This is an integration test, so it calls the real API.
    """
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.from_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.args = []

    # Mock the internal API calls to control the response
    with patch('src.bot.handlers.symbols._api_get_symbols', new_callable=AsyncMock) as mock_api_get_symbols:
        mock_api_get_symbols.return_value = {
            "items": [
                {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"},
                {"symbol": "000660", "name": "SK하이닉스", "market": "KOSPI"}
            ],
            "total_count": 2
        }

        await symbols_command(update, context)

        mock_api_get_symbols.assert_awaited_once_with(10, 0) # Assuming PAGE_SIZE is 10
        update.message.reply_text.assert_awaited_once()
        sent_text = update.message.reply_text.call_args[0][0]
        assert "[종목 목록]" in sent_text
        assert "총 2개" in sent_text
        assert "005930 삼성전자 (KOSPI)" in sent_text

@pytest.mark.asyncio
async def test_symbols_command_no_symbols_found():
    """
    Test that the symbols command handles cases where no symbols are found.
    """
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.from_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.args = []

    mock_response_json = {"items": [], "total_count": 0}

    with patch('src.bot.handlers.symbols._api_get_symbols', new_callable=AsyncMock) as mock_api_get_symbols:
        mock_api_get_symbols.return_value = mock_response_json

        await symbols_command(update, context)

        update.message.reply_text.assert_called_once_with(
            "등록된 종목이 없습니다.", reply_markup=None
        )

@pytest.mark.asyncio
async def test_symbols_command_api_error_integration():
    """
    Test that the symbols command handles API errors gracefully.
    """
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.from_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.args = []

    with patch('src.bot.handlers.symbols._api_get_symbols', new_callable=AsyncMock) as mock_api_get_symbols:
        mock_api_get_symbols.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=httpx.Request("GET", API_URL),
            response=httpx.Response(500, request=httpx.Request("GET", API_URL))
        )

        await symbols_command(update, context)

        mock_api_get_symbols.assert_awaited_once_with(10, 0) # Assuming PAGE_SIZE is 10
        update.message.reply_text.assert_awaited_once_with("종목 목록 조회 실패: API 응답 코드 500")
