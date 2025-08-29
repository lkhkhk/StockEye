import pytest
from unittest.mock import AsyncMock, patch, Mock
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.handlers.watchlist import watchlist_add_command, watchlist_remove_command, watchlist_get_command

@pytest.mark.asyncio
@patch('src.common.http_client.httpx.AsyncClient.post')
async def test_watchlist_add_command_success(mock_post):
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_response = AsyncMock(status_code=200)
    mock_response.json.return_value = {"message": "관심종목 추가 완료"}
    mock_post.return_value = mock_response

    await watchlist_add_command(update, context)

    mock_post.assert_called_once()
    update.message.reply_text.assert_called_once_with("관심종목 추가 완료")

@pytest.mark.asyncio
async def test_watchlist_add_command_no_symbol():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []

    await watchlist_add_command(update, context)

    update.message.reply_text.assert_called_once_with(
        "사용법: /watchlist_add [종목코드] 예: /watchlist_add 005930"
    )

@pytest.mark.asyncio
@patch('src.common.http_client.httpx.AsyncClient.post')
async def test_watchlist_add_command_api_error(mock_post):
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_response = AsyncMock(status_code=500)
    mock_post.return_value = mock_response

    await watchlist_add_command(update, context)

    mock_post.assert_called_once()
    update.message.reply_text.assert_called_once_with(
        "관심종목 추가 실패: API 응답 코드 500"
    )

@pytest.mark.asyncio
@patch('src.common.http_client.httpx.AsyncClient.delete')
async def test_watchlist_remove_command_success(mock_delete):
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_response = AsyncMock(status_code=200)
    mock_response.json.return_value = {"message": "관심종목 제거 완료"}
    mock_delete.return_value = mock_response

    await watchlist_remove_command(update, context)

    mock_delete.assert_called_once()
    update.message.reply_text.assert_called_once_with("관심종목 제거 완료")

@pytest.mark.asyncio
async def test_watchlist_remove_command_no_symbol():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []

    await watchlist_remove_command(update, context)

    update.message.reply_text.assert_called_once_with(
        "사용법: /watchlist_remove [종목코드] 예: /watchlist_remove 005930"
    )

@pytest.mark.asyncio
@patch('src.common.http_client.httpx.AsyncClient.delete')
async def test_watchlist_remove_command_api_error(mock_delete):
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_response = AsyncMock(status_code=500)
    mock_delete.return_value = mock_response

    await watchlist_remove_command(update, context)

    mock_delete.assert_called_once()
    update.message.reply_text.assert_called_once_with(
        "관심종목 제거 실패: API 응답 코드 500"
    )

@pytest.mark.asyncio
@patch('src.common.http_client.httpx.AsyncClient.get')
async def test_watchlist_get_command_success(mock_get):
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = AsyncMock(status_code=200)
    mock_response.json.return_value = {"watchlist": ["005930 삼성전자", "000660 SK하이닉스"]}
    mock_get.return_value = mock_response

    await watchlist_get_command(update, context)

    mock_get.assert_called_once()
    update.message.reply_text.assert_called_once_with(
        "[관심종목 목록]\n005930 삼성전자\n000660 SK하이닉스"
    )

@pytest.mark.asyncio
@patch('src.common.http_client.httpx.AsyncClient.get')
async def test_watchlist_get_command_no_watchlist(mock_get):
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = AsyncMock(status_code=200)
    mock_response.json.return_value = {"watchlist": []}
    mock_get.return_value = mock_response

    await watchlist_get_command(update, context)

    mock_get.assert_called_once()
    update.message.reply_text.assert_called_once_with("관심종목이 없습니다.")

@pytest.mark.asyncio
@patch('src.common.http_client.httpx.AsyncClient.get')
async def test_watchlist_get_command_api_error(mock_get):
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = AsyncMock(status_code=500)
    mock_get.return_value = mock_response

    await watchlist_get_command(update, context)

    mock_get.assert_called_once()
    update.message.reply_text.assert_called_once_with(
        "관심종목 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: 500)"
    )
