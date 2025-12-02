import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackContext
import httpx # Add this import

from src.bot.handlers import symbols # Import the symbols module to access PAGE_SIZE
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
    """테스트를 위한 Update 및 CallbackContext 모의 객체를 제공합니다."""
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    # AsyncMock: callback_query 객체를 모의합니다. 비동기적으로 동작합니다.
    update.callback_query = AsyncMock()
    # AsyncMock: answer 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.callback_query.answer = AsyncMock()
    # AsyncMock: edit_message_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.callback_query.edit_message_text = AsyncMock()
    # MOCK: telegram.ext.CallbackContext 객체
    # AsyncMock: CallbackContext 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=CallbackContext)
    context.user_data = {}
    return update, context

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbols') # MOCK: _api_get_symbols 함수
async def test_symbols_command_success(mock_api_call, mock_update_context):
    """/symbols 명령어 성공 테스트 (인자 없음)."""
    update, context = mock_update_context
    context.args = []
    # mock_api_call (AsyncMock) 호출 시 모의 종목 목록을 반환하도록 설정합니다.
    mock_api_call.return_value = {
        "items": [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"},
            {"symbol": "000660", "name": "SK하이닉스", "market": "KOSPI"}
        ],
        "total_count": 2
    }

    await symbols_command(update, context)

    # mock_api_call (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다.
    mock_api_call.assert_awaited_once_with(symbols.PAGE_SIZE, 0)
    # update.message.reply_text (AsyncMock)가 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once()
    sent_text = update.message.reply_text.call_args[0][0]
    assert "[종목 목록]" in sent_text
    assert "총 2개" in sent_text

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbols') # MOCK: _api_get_symbols 함수
async def test_symbols_command_no_symbols(mock_api_call, mock_update_context):
    """종목이 반환되지 않을 때 /symbols 명령어 테스트."""
    update, context = mock_update_context
    context.args = []
    # mock_api_call (AsyncMock) 호출 시 빈 목록을 반환하도록 설정합니다.
    mock_api_call.return_value = {"items": [], "total_count": 0}

    await symbols_command(update, context)

    # mock_api_call (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다。
    mock_api_call.assert_awaited_once_with(symbols.PAGE_SIZE, 0)
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다。
    update.message.reply_text.assert_awaited_once_with("등록된 종목이 없습니다.", reply_markup=None)

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbols', side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock(status_code=500))) # MOCK: _api_get_symbols 함수
async def test_symbols_command_api_error(mock_api_call, mock_update_context):
    """API가 오류를 반환할 때 /symbols 명령어 테스트."""
    update, context = mock_update_context
    context.args = []

    await symbols_command(update, context)

    # mock_api_call (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다。
    mock_api_call.assert_awaited_once_with(symbols.PAGE_SIZE, 0)
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다。
    update.message.reply_text.assert_awaited_once_with("종목 목록 조회 실패: API 응답 코드 500")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols') # MOCK: _api_search_symbols 함수
async def test_symbols_search_command_success(mock_api_call, mock_update_context):
    """검색 쿼리가 있는 /symbols 명령어 성공 테스트."""
    update, context = mock_update_context
    update.message.text = "/symbols 삼성"
    context.args = ["삼성"]
    # mock_api_call (AsyncMock) 호출 시 모의 종목 목록을 반환하도록 설정합니다.
    mock_api_call.return_value = {
        "items": [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"}
        ],
        "total_count": 1
    }

    await symbols_search_command(update, context)

    # mock_api_call (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다。
    mock_api_call.assert_awaited_once_with("삼성", symbols.PAGE_SIZE, 0)
    # update.message.reply_text (AsyncMock)가 한 번 호출되었는지 확인합니다。
    update.message.reply_text.assert_awaited_once()
    sent_text = update.message.reply_text.call_args[0][0]
    assert "'삼성' 검색 결과" in sent_text
    assert "총 1개" in sent_text

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols') # MOCK: _api_search_symbols 함수
async def test_symbols_search_command_no_query(mock_api_call, mock_update_context):
    """검색 쿼리가 없지만 쿼리 문자열이 없는 /symbols 명령어 테스트."""
    update, context = mock_update_context
    update.message.text = "/symbols_search" # Changed to reflect direct call to symbols_search_command
    context.args = [] # No query provided

    # mock_api_call (AsyncMock) 호출 시 빈 목록을 반환하도록 설정합니다.
    mock_api_call.return_value = {"items": [], "total_count": 0} # Mock expected empty result

    await symbols_search_command(update, context)

    # mock_api_call (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다.
    mock_api_call.assert_awaited_once_with("", symbols.PAGE_SIZE, 0) # Expect it to be called with empty query
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다。
    update.message.reply_text.assert_awaited_once_with("검색 결과가 없습니다.", reply_markup=None)

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols') # MOCK: _api_search_symbols 함수
async def test_symbols_search_command_no_results(mock_api_call, mock_update_context):
    """검색 쿼리가 결과가 없는 /symbols 명령어 테스트."""
    update, context = mock_update_context
    context.args = ["없는종목"]
    # mock_api_call (AsyncMock) 호출 시 빈 목록을 반환하도록 설정합니다。
    mock_api_call.return_value = {"items": [], "total_count": 0}

    await symbols_search_command(update, context)

    # mock_api_call (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다。
    mock_api_call.assert_awaited_once_with("없는종목", symbols.PAGE_SIZE, 0)
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다。
    update.message.reply_text.assert_awaited_once_with("검색 결과가 없습니다.", reply_markup=None)

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols', side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock(status_code=500))) # MOCK: _api_search_symbols 함수
async def test_symbols_search_command_api_error(mock_api_call, mock_update_context):
    """API가 오류를 반환할 때 검색 쿼리가 있는 /symbols 명령어 테스트."""
    update, context = mock_update_context
    context.args = ["삼성"]

    await symbols_search_command(update, context)

    # mock_api_call (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다。
    mock_api_call.assert_awaited_once_with("삼성", symbols.PAGE_SIZE, 0)
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다。
    update.message.reply_text.assert_awaited_once_with("종목 검색 실패: API 응답 코드 500")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbol_by_code') # MOCK: _api_get_symbol_by_code 함수
@patch('src.bot.handlers.symbols._api_search_symbols') # MOCK: _api_search_symbols 함수
async def test_symbol_info_command_success(mock_api_search_call, mock_api_get_by_code_call, mock_update_context):
    """/symbol_info 명령어 성공 테스트."""
    update, context = mock_update_context
    update.message.text = "/symbol_info 005930"
    context.args = ["005930"]
    
    # _api_get_symbol_by_code가 성공적으로 반환하도록 설정
    mock_api_get_by_code_call.return_value = {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"}

    await symbol_info_command(update, context)

    # _api_get_symbol_by_code가 올바른 인자로 한 번 호출되었는지 확인합니다.
    mock_api_get_by_code_call.assert_awaited_once_with("005930")
    # _api_search_symbols는 호출되지 않아야 합니다.
    mock_api_search_call.assert_not_awaited()
    
    # update.message.reply_text (AsyncMock)가 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once()
    sent_text = update.message.reply_text.call_args[0][0]
    assert "[종목 상세]" in sent_text
    assert "코드: 005930" in sent_text

@pytest.mark.asyncio
async def test_symbol_info_command_no_symbol(mock_update_context):
    """심볼이 제공되지 않을 때 /symbol_info 명령어 테스트."""
    update, context = mock_update_context
    context.args = []

    await symbol_info_command(update, context)

    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once_with("사용법: /symbol_info [종목코드 또는 종목명] 예: /symbol_info 005930 또는 /symbol_info 삼성전자")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbol_by_code', side_effect=httpx.HTTPStatusError("Not Found", request=MagicMock(), response=MagicMock(status_code=404)))
@patch('src.bot.handlers.symbols._api_search_symbols') # MOCK: _api_search_symbols 함수
async def test_symbol_info_command_not_found(mock_api_search_call, mock_api_get_by_code_call, mock_update_context):
    """심볼을 찾을 수 없을 때 /symbol_info 명령어 테스트."""
    update, context = mock_update_context
    context.args = ["없는종목"]
    
    # _api_search_symbols가 빈 목록을 반환하도록 설정
    mock_api_search_call.return_value = {"items": [], "total_count": 0}

    await symbol_info_command(update, context)

    # _api_get_symbol_by_code가 먼저 호출되었는지 확인
    mock_api_get_by_code_call.assert_awaited_once_with("없는종목")
    # _api_search_symbols가 올바른 인자로 호출되었는지 확인
    mock_api_search_call.assert_awaited_once_with("없는종목", symbols.PAGE_SIZE, 0)
    
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once_with("해당 종목을 찾을 수 없습니다.")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbol_by_code', side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock(status_code=500)))
@patch('src.bot.handlers.symbols._api_search_symbols') # MOCK: _api_search_symbols 함수
async def test_symbol_info_command_api_error(mock_api_search_call, mock_api_get_by_code_call, mock_update_context):
    """API가 오류를 반환할 때 /symbol_info 명령어 테스트."""
    update, context = mock_update_context
    context.args = ["005930"]

    await symbol_info_command(update, context)

    # _api_get_symbol_by_code가 먼저 호출되었는지 확인
    mock_api_get_by_code_call.assert_awaited_once_with("005930")
    # _api_search_symbols는 호출되지 않아야 합니다.
    mock_api_search_call.assert_not_awaited()
    
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다。
    update.message.reply_text.assert_awaited_once_with("종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: 500)")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbols') # MOCK: _api_get_symbols 함수
async def test_symbols_pagination_callback_success(mock_api_call, mock_update_context):
    """심볼 페이지네이션 콜백 성공 테스트."""
    update, context = mock_update_context
    update.callback_query.data = "symbols_page_10"
    # mock_api_call (AsyncMock) 호출 시 모의 종목 목록을 반환하도록 설정합니다.
    mock_api_call.return_value = {
        "items": [
            {"symbol": "000001", "name": "종목1"}
        ],
        "total_count": 20
    }

    await symbols_pagination_callback(update, context)

    # mock_api_call (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다.
    mock_api_call.assert_awaited_once_with(symbols.PAGE_SIZE, 10)
    # update.callback_query.edit_message_text (AsyncMock)가 한 번 호출되었는지 확인합니다。
    update.callback_query.edit_message_text.assert_awaited_once()
    sent_text = update.callback_query.edit_message_text.call_args[0][0]
    assert "[종목 목록]" in sent_text
    assert "페이지: 2/2" in sent_text

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_get_symbols', side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock(status_code=500))) # MOCK: _api_get_symbols 함수
async def test_symbols_pagination_callback_api_error(mock_api_call, mock_update_context):
    """API가 오류를 반환할 때 심볼 페이지네이션 콜백 테스트."""
    update, context = mock_update_context
    update.callback_query.data = "symbols_page_10"

    await symbols_pagination_callback(update, context)

    # mock_api_call (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다.
    mock_api_call.assert_awaited_once_with(symbols.PAGE_SIZE, 10)
    # update.callback_query.edit_message_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다。
    update.callback_query.edit_message_text.assert_awaited_once_with("페이지 이동 실패: API 응답 코드 500")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols') # MOCK: _api_search_symbols 함수
async def test_symbols_search_pagination_callback_success(mock_api_call, mock_update_context):
    """심볼 검색 페이지네이션 콜백 성공 테스트."""
    update, context = mock_update_context
    update.callback_query.data = "symbols_search_page:삼성:10"
    # mock_api_call (AsyncMock) 호출 시 모의 종목 목록을 반환하도록 설정합니다.
    mock_api_call.return_value = {
        "items": [
            {"symbol": "005930", "name": "삼성전자"}
        ],
        "total_count": 20
    }

    await symbols_search_pagination_callback(update, context)

    # mock_api_call (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다.
    mock_api_call.assert_awaited_once_with("삼성", symbols.PAGE_SIZE, 10)
    # update.callback_query.edit_message_text (AsyncMock)가 한 번 호출되었는지 확인합니다。
    update.callback_query.edit_message_text.assert_awaited_once()
    sent_text = update.callback_query.edit_message_text.call_args[0][0]
    assert "'삼성' 검색 결과" in sent_text
    assert "페이지: 2/2" in sent_text

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols._api_search_symbols', side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock(status_code=500))) # MOCK: _api_search_symbols 함수
async def test_symbols_search_pagination_callback_api_error(mock_api_call, mock_update_context):
    """API가 오류를 반환할 때 심볼 검색 페이지네이션 콜백 테스트."""
    update, context = mock_update_context
    update.callback_query.data = "symbols_search_page:삼성:10"

    await symbols_search_pagination_callback(update, context)

    # mock_api_call (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다。
    mock_api_call.assert_awaited_once_with("삼성", symbols.PAGE_SIZE, 10)
    # update.callback_query.edit_message_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다。
    update.callback_query.edit_message_text.assert_awaited_once_with("검색 페이지 이동 실패: API 응답 코드 500")

@pytest.mark.asyncio
@patch('src.bot.handlers.symbols.symbols_search_command') # MOCK: symbols_search_command 함수
async def test_symbol_info_callback_calls_symbols_search_command(mock_symbols_search_command, mock_update_context):
    """symbol_info_callback이 symbols_search_command를 올바르게 호출하는지 테스트."""
    update, context = mock_update_context
    update.callback_query.data = "symbol_info_005930"
    
    await symbol_info_callback(update, context)

    # symbols_search_command가 올바른 인자로 한 번 호출되었는지 확인합니다.
    mock_symbols_search_command.assert_awaited_once_with(update, context)
    # context.args가 올바르게 설정되었는지 확인합니다.
    assert context.args == ["005930"]
    # update.callback_query.answer (AsyncMock)가 한 번 호출되었는지 확인합니다.
    update.callback_query.answer.assert_awaited_once()
