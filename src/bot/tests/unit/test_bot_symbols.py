import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackContext
import httpx # Add this import

from src.bot.handlers.symbols import (
    symbols_command,
    symbols_pagination_callback,
    symbols_search_command,
    symbols_search_pagination_callback,
    symbol_info_command,
    symbol_info_callback
)

@pytest.fixture
def mock_update_context():
    """Provides a mock Update and CallbackContext for tests."""
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    update.callback_query = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    context = AsyncMock(spec=CallbackContext)
    context.user_data = {}
    return update, context

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbols')
async def test_symbols_command_success(mock_api_call, mock_update_context):
    """Test /symbols command success (no args)."""
    update, context = mock_update_context
    context.args = []
    mock_api_call.return_value = {
        "items": [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"},
            {"symbol": "000660", "name": "SK하이닉스", "market": "KOSPI"}
        ],
        "total_count": 2
    }

    await symbols_command(update, context)

    mock_api_call.assert_awaited_once_with(10, 0)
    update.message.reply_text.assert_awaited_once()
    sent_text = update.message.reply_text.call_args[0][0]
    assert "[종목 목록]" in sent_text
    assert "총 2개" in sent_text

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbols')
async def test_symbols_command_no_symbols(mock_api_call, mock_update_context):
    """Test /symbols command when no symbols are returned."""
    update, context = mock_update_context
    context.args = []
    mock_api_call.return_value = {"items": [], "total_count": 0}

    await symbols_command(update, context)

    mock_api_call.assert_awaited_once_with(10, 0)
    update.message.reply_text.assert_awaited_once_with("등록된 종목이 없습니다.", reply_markup=None)

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbols', side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock(status_code=500)))
async def test_symbols_command_api_error(mock_api_call, mock_update_context):
    """Test /symbols command when API returns an error."""
    update, context = mock_update_context
    context.args = []

    await symbols_command(update, context)

    mock_api_call.assert_awaited_once_with(10, 0)
    update.message.reply_text.assert_awaited_once_with("종목 목록 조회 실패: API 응답 코드 500")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols')
async def test_symbols_search_command_success(mock_api_call, mock_update_context):
    """Test /symbols command with search query success."""
    update, context = mock_update_context
    update.message.text = "/symbols 삼성"
    context.args = ["삼성"]
    mock_api_call.return_value = {
        "items": [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"}
        ],
        "total_count": 1
    }

    await symbols_search_command(update, context)

    mock_api_call.assert_awaited_once_with("삼성", 10, 0)
    update.message.reply_text.assert_awaited_once()
    sent_text = update.message.reply_text.call_args[0][0]
    assert "'삼성' 검색 결과" in sent_text
    assert "총 1개" in sent_text

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols')
async def test_symbols_search_command_no_query(mock_api_call, mock_update_context):
    """Test /symbols command with search query but no query string."""
    update, context = mock_update_context
    update.message.text = "/symbols_search" # Changed to reflect direct call to symbols_search_command
    context.args = [] # No query provided

    mock_api_call.return_value = {"items": [], "total_count": 0} # Mock expected empty result

    await symbols_search_command(update, context)

    mock_api_call.assert_awaited_once_with("", 10, 0) # Expect it to be called with empty query
    update.message.reply_text.assert_awaited_once_with("검색 결과가 없습니다.", reply_markup=None)

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols')
async def test_symbols_search_command_no_results(mock_api_call, mock_update_context):
    """Test /symbols command with search query returning no results."""
    update, context = mock_update_context
    context.args = ["없는종목"]
    mock_api_call.return_value = {"items": [], "total_count": 0}

    await symbols_search_command(update, context)

    mock_api_call.assert_awaited_once_with("없는종목", 10, 0)
    update.message.reply_text.assert_awaited_once_with("검색 결과가 없습니다.", reply_markup=None)

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols', side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock(status_code=500)))
async def test_symbols_search_command_api_error(mock_api_call, mock_update_context):
    """Test /symbols command with search query when API returns an error."""
    update, context = mock_update_context
    context.args = ["삼성"]

    await symbols_search_command(update, context)

    mock_api_call.assert_awaited_once_with("삼성", 10, 0)
    update.message.reply_text.assert_awaited_once_with("종목 검색 실패: API 응답 코드 500")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols')
async def test_symbol_info_command_success(mock_api_call, mock_update_context):
    """Test /symbol_info command success."""
    update, context = mock_update_context
    update.message.text = "/symbol_info 005930"
    context.args = ["005930"]
    mock_api_call.return_value = {
        "items": [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"}
        ],
        "total_count": 1
    }

    await symbol_info_command(update, context)

    mock_api_call.assert_awaited_once_with("005930", 5000, 0)
    update.message.reply_text.assert_awaited_once()
    sent_text = update.message.reply_text.call_args[0][0]
    assert "[종목 상세]" in sent_text
    assert "코드: 005930" in sent_text

@pytest.mark.asyncio
async def test_symbol_info_command_no_symbol(mock_update_context):
    """Test /symbol_info command with no symbol provided."""
    update, context = mock_update_context
    context.args = []

    await symbol_info_command(update, context)

    update.message.reply_text.assert_awaited_once_with("사용법: /symbol_info [종목코드 또는 종목명] 예: /symbol_info 005930 또는 /symbol_info 삼성전자")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols')
async def test_symbol_info_command_not_found(mock_api_call, mock_update_context):
    """Test /symbol_info command when symbol is not found."""
    update, context = mock_update_context
    context.args = ["없는종목"]
    mock_api_call.return_value = {"items": [], "total_count": 0}

    await symbol_info_command(update, context)

    mock_api_call.assert_awaited_once_with("없는종목", 5000, 0)
    update.message.reply_text.assert_awaited_once_with("해당 종목을 찾을 수 없습니다.")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols', side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock(status_code=500)))
async def test_symbol_info_command_api_error(mock_api_call, mock_update_context):
    """Test /symbol_info command when API returns an error."""
    update, context = mock_update_context
    context.args = ["005930"]

    await symbol_info_command(update, context)

    mock_api_call.assert_awaited_once_with("005930", 5000, 0)
    update.message.reply_text.assert_awaited_once_with("종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: 500)")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbols')
async def test_symbols_pagination_callback_success(mock_api_call, mock_update_context):
    """Test symbols pagination callback success."""
    update, context = mock_update_context
    update.callback_query.data = "symbols_page_10"
    mock_api_call.return_value = {
        "items": [
            {"symbol": "000001", "name": "종목1"}
        ],
        "total_count": 20
    }

    await symbols_pagination_callback(update, context)

    mock_api_call.assert_awaited_once_with(10, 10)
    update.callback_query.edit_message_text.assert_awaited_once()
    sent_text = update.callback_query.edit_message_text.call_args[0][0]
    assert "[종목 목록]" in sent_text
    assert "페이지: 2/2" in sent_text

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbols', side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock(status_code=500)))
async def test_symbols_pagination_callback_api_error(mock_api_call, mock_update_context):
    """Test symbols pagination callback when API returns an error."""
    update, context = mock_update_context
    update.callback_query.data = "symbols_page_10"

    await symbols_pagination_callback(update, context)

    mock_api_call.assert_awaited_once_with(10, 10)
    update.callback_query.edit_message_text.assert_awaited_once_with("페이지 이동 실패: API 응답 코드 500")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols')
async def test_symbols_search_pagination_callback_success(mock_api_call, mock_update_context):
    """Test symbols search pagination callback success."""
    update, context = mock_update_context
    update.callback_query.data = "symbols_search_page_삼성_10"
    mock_api_call.return_value = {
        "items": [
            {"symbol": "005930", "name": "삼성전자"}
        ],
        "total_count": 20
    }

    await symbols_search_pagination_callback(update, context)

    mock_api_call.assert_awaited_once_with("삼성", 10, 10)
    update.callback_query.edit_message_text.assert_awaited_once()
    sent_text = update.callback_query.edit_message_text.call_args[0][0]
    assert "'삼성' 검색 결과" in sent_text
    assert "페이지: 2/2" in sent_text

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols', side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock(status_code=500)))
async def test_symbols_search_pagination_callback_api_error(mock_api_call, mock_update_context):
    """Test symbols search pagination callback when API returns an error."""
    update, context = mock_update_context
    update.callback_query.data = "symbols_search_page_삼성_10"

    await symbols_search_pagination_callback(update, context)

    mock_api_call.assert_awaited_once_with("삼성", 10, 10)
    update.callback_query.edit_message_text.assert_awaited_once_with("검색 페이지 이동 실패: API 응답 코드 500")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols')
async def test_symbol_info_callback_calls_symbol_info_command(mock_api_call, mock_update_context):
    """Test that symbol_info_callback correctly calls symbol_info_command."""
    update, context = mock_update_context
    update.callback_query.data = "symbol_info_005930"
    
    # Mock the internal API call that symbol_info_command makes
    mock_api_call.return_value = {
        "items": [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"}
        ],
        "total_count": 1
    }

    await symbol_info_callback(update, context)

    # Verify that symbol_info_command was called with the correct arguments
    mock_api_call.assert_awaited_once_with("005930", 5000, 0)
    update.callback_query.answer.assert_awaited_once()
    update.message.reply_text.assert_awaited_once()
    sent_text = update.message.reply_text.call_args[0][0]
    assert "[종목 상세]" in sent_text
    assert "코드: 005930" in sent_text
