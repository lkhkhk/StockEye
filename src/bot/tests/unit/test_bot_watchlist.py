import pytest
import requests
from unittest.mock import AsyncMock, patch, Mock
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.handlers.watchlist import watchlist_add_command, watchlist_remove_command, watchlist_get_command

@pytest.mark.asyncio
async def test_watchlist_add_command_success():
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = Mock(return_value={"message": "관심종목 추가 완료"})
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.watchlist.session.post', return_value=mock_response) as mock_post:
        await watchlist_add_command(update, context)

        mock_post.assert_called_once_with(
            "http://stockseye-api:8000/watchlist/add",
            json={
                "user_id": 123,
                "symbol": "005930"
            },
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "관심종목 추가 완료"
        )

@pytest.mark.asyncio
async def test_watchlist_add_command_no_symbol():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []

    with patch('src.bot.handlers.watchlist.session.post') as mock_post:
        await watchlist_add_command(update, context)

        mock_post.assert_not_called()
        update.message.reply_text.assert_called_once_with(
            "사용법: /watchlist_add [종목코드] 예: /watchlist_add 005930"
        )

@pytest.mark.asyncio
async def test_watchlist_add_command_api_error():
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_response = AsyncMock(status_code=500, ok=False)

    with patch('src.bot.handlers.watchlist.session.post', return_value=mock_response) as mock_post:
        await watchlist_add_command(update, context)

        mock_post.assert_called_once_with(
            "http://stockseye-api:8000/watchlist/add",
            json={
                "user_id": 123,
                "symbol": "005930"
            },
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "관심종목 추가 실패: API 응답 코드 500"
        )

@pytest.mark.asyncio
async def test_watchlist_remove_command_success():
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = Mock(return_value={"message": "관심종목 제거 완료"})
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.watchlist.session.post', return_value=mock_response) as mock_post:
        await watchlist_remove_command(update, context)

        mock_post.assert_called_once_with(
            "http://stockseye-api:8000/watchlist/remove",
            json={
                "user_id": 123,
                "symbol": "005930"
            },
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "관심종목 제거 완료"
        )

@pytest.mark.asyncio
async def test_watchlist_remove_command_no_symbol():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []

    with patch('src.bot.handlers.watchlist.session.post') as mock_post:
        await watchlist_remove_command(update, context)

        mock_post.assert_not_called()
        update.message.reply_text.assert_called_once_with(
            "사용법: /watchlist_remove [종목코드] 예: /watchlist_remove 005930"
        )

@pytest.mark.asyncio
async def test_watchlist_remove_command_api_error():
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_response = AsyncMock(status_code=500, ok=False)

    with patch('src.bot.handlers.watchlist.session.post', return_value=mock_response) as mock_post:
        await watchlist_remove_command(update, context)

        mock_post.assert_called_once_with(
            "http://stockseye-api:8000/watchlist/remove",
            json={
                "user_id": 123,
                "symbol": "005930"
            },
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "관심종목 제거 실패: API 응답 코드 500"
        )

@pytest.mark.asyncio
async def test_watchlist_get_command_success():
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = Mock(return_value={
        "watchlist": ["005930 삼성전자", "000660 SK하이닉스"]
    })
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.watchlist.session.get', return_value=mock_response) as mock_get:
        await watchlist_get_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/watchlist/get/123",
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "[관심종목 목록]\n005930 삼성전자\n000660 SK하이닉스"
        )

@pytest.mark.asyncio
async def test_watchlist_get_command_no_watchlist():
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = Mock(return_value={
        "watchlist": []
    })
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.watchlist.session.get', return_value=mock_response) as mock_get:
        await watchlist_get_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/watchlist/get/123",
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "관심종목이 없습니다."
        )

@pytest.mark.asyncio
async def test_watchlist_get_command_api_error():
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = AsyncMock(status_code=500, ok=False)

    with patch('src.bot.handlers.watchlist.session.get', return_value=mock_response) as mock_get:
        await watchlist_get_command(update, context)

        mock_get.assert_called_once_with(
            "http://stockseye-api:8000/watchlist/get/123",
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "관심종목 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: 500)"
        )
