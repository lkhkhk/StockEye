import pytest
import requests
from unittest.mock import AsyncMock, patch, Mock, ANY
from telegram import Update
from telegram.ext import ContextTypes, filters
from src.bot.handlers.symbols import symbols_command, symbols_search_command, symbol_info_command, symbols_pagination_callback, symbol_info_callback, symbols_search_pagination_callback
import re

@pytest.mark.asyncio
async def test_symbols_command_success():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {'symbols_offset': 0}
    context.args = []

    mock_json_method = Mock(return_value={
        "items": [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"},
            {"symbol": "000660", "name": "SK하이닉스", "market": "KOSPI"}
        ],
        "total_count": 2
    })
    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = mock_json_method
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.symbols.session.get', return_value=mock_response) as mock_get:
        await symbols_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/symbols/?limit=10&offset=0",
            timeout=10
        )
        update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_symbols_command_no_symbols():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {'symbols_offset': 0}
    context.args = []

    mock_json_method = Mock(return_value={"items": [], "total_count": 0})
    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = mock_json_method
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.symbols.session.get', return_value=mock_response) as mock_get:
        await symbols_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/symbols/?limit=10&offset=0",
            timeout=10
        )
        update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_symbols_command_api_error():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {'symbols_offset': 0}
    context.args = []

    mock_response = AsyncMock(status_code=500, ok=False)

    with patch('src.bot.handlers.symbols.session.get', return_value=mock_response) as mock_get:
        await symbols_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/symbols/?limit=10&offset=0",
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "종목 목록 조회 실패: API 응답 코드 500"
        )

@pytest.mark.asyncio
async def test_symbols_search_command_success():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["삼성"]
    context.user_data = {f'symbols_search_offset_{context.args[0]}': 0}

    mock_json_method = Mock(return_value={
        "items": [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"}
        ],
        "total_count": 1
    })
    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = mock_json_method
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.symbols.session.get', return_value=mock_response) as mock_get:
        await symbols_search_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/symbols/search",
            params={"query": "삼성", "limit": 10, "offset": 0},
            timeout=10
        )
        update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_symbols_search_command_no_query():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.user_data = {f'symbols_search_offset_': 0}

    mock_json_method = Mock(return_value={"items": [], "total_count": 0})
    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = mock_json_method
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.symbols.session.get', return_value=mock_response) as mock_get:
        await symbols_search_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/symbols/search",
            params={"query": "", "limit": 10, "offset": 0},
            timeout=10
        )
        update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_symbols_search_command_no_results():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["없는종목"]
    context.user_data = {f'symbols_search_offset_{context.args[0]}': 0}

    mock_json_method = Mock(return_value={"items": [], "total_count": 0})
    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = mock_json_method
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.symbols.session.get', return_value=mock_response) as mock_get:
        await symbols_search_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/symbols/search",
            params={"query": "없는종목", "limit": 10, "offset": 0},
            timeout=10
        )
        update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_symbols_search_command_api_error():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["삼성"]
    context.user_data = {f'symbols_search_offset_{context.args[0]}': 0}

    mock_response = AsyncMock(status_code=500, ok=False)

    with patch('src.bot.handlers.symbols.session.get', return_value=mock_response) as mock_get:
        await symbols_search_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/symbols/search",
            params={"query": "삼성", "limit": 10, "offset": 0},
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "종목 검색 실패: API 응답 코드 500"
        )

@pytest.mark.asyncio
async def test_symbol_info_command_success():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_json_method = Mock(return_value={
        "items": [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"}
        ],
        "total_count": 1
    })
    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = mock_json_method
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.symbols.session.get', return_value=mock_response) as mock_get:
        await symbol_info_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/symbols/search",
            params={"query": "005930", "limit": 5000, "offset": 0},
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "[종목 상세]\n코드: 005930\n이름: 삼성전자\n시장: KOSPI"
        )

@pytest.mark.asyncio
async def test_symbol_info_command_no_symbol():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []

    with patch('src.bot.handlers.symbols.session.get') as mock_get:
        await symbol_info_command(update, context)

        mock_get.assert_not_called()
        update.message.reply_text.assert_called_once_with(
            "사용법: /symbol_info [종목코드 또는 종목명] 예: /symbol_info 005930 또는 /symbol_info 삼성전자"
        )

@pytest.mark.asyncio
async def test_symbol_info_command_not_found():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["없는종목"]

    mock_json_method = Mock(return_value={"items": [], "total_count": 0})
    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = mock_json_method
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.symbols.session.get', return_value=mock_response) as mock_get:
        await symbol_info_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/symbols/search",
            params={"query": "없는종목", "limit": 5000, "offset": 0},
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "해당 종목을 찾을 수 없습니다."
        )

@pytest.mark.asyncio
async def test_symbol_info_command_api_error():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_response = AsyncMock(status_code=500, ok=False)

    with patch('src.bot.handlers.symbols.session.get', return_value=mock_response) as mock_get:
        await symbol_info_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/symbols/search",
            params={"query": "005930", "limit": 5000, "offset": 0},
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: 500)"
        )

@pytest.mark.asyncio
async def test_symbols_command_with_query():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["한화"] # Simulate /symbols 한화
    context.user_data = {f'symbols_search_offset_{context.args[0]}': 0}

    mock_json_method = Mock(return_value={
        "items": [
            {"symbol": "000880", "name": "한화", "market": "KOSPI"},
            {"symbol": "000730", "name": "한화생명", "market": "KOSPI"}
        ],
        "total_count": 2
    })
    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = mock_json_method
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.symbols.session.get', return_value=mock_response) as mock_get:
        await symbols_command(update, context)

        # symbols_command가 symbols/search 엔드포인트를 올바른 쿼리로 호출하는지 확인
        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/symbols/search",
            params={"query": "한화", "limit": 10, "offset": 0},
            timeout=10
        )
        # 봇이 사용자에게 올바른 검색 결과를 응답하는지 확인
        update.message.reply_text.assert_called_once()
