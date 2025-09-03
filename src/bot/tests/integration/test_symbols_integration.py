import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes
from src.bot.handlers.symbols import symbols_command, symbols_pagination_callback, symbol_info_callback, symbols_search_command

@pytest.mark.asyncio
async def test_symbols_command_success():
    """
    Test that the symbols command successfully retrieves and displays stock symbols.
    """
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.from_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.message.reply_text = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.args = []

    mock_response_json = {
        "items": [
            {"symbol": "005930", "name": "삼성전자"},
            {"symbol": "035420", "name": "NAVER"}
        ],
        "total_count": 2
    }

    with patch('src.bot.handlers.symbols._api_get_symbols', new_callable=AsyncMock) as mock_api_get_symbols:
        mock_api_get_symbols.return_value = mock_response_json

        await symbols_command(update, context)

        # Assert that reply_text was called
        update.message.reply_text.assert_called_once()
        
        # Get the arguments from the call
        call_args, call_kwargs = update.message.reply_text.call_args
        
        # Assert the message content
        assert "[종목 목록]" in call_args[0]
        assert "삼성전자" in call_args[0]
        assert "NAVER" in call_args[0]

@pytest.mark.asyncio
async def test_symbols_command_api_failure():
    """
    Test that the symbols command handles API failures gracefully.
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
        mock_api_get_symbols.side_effect = Exception("API Error")

        await symbols_command(update, context)

        update.message.reply_text.assert_called_once_with(
            "종목 목록 조회 실패: 알 수 없는 오류가 발생했습니다."
        )

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
            "등록된 종목이 없습니다.", None
        )