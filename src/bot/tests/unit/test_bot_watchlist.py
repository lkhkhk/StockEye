import pytest
from unittest.mock import AsyncMock, patch, Mock
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.handlers.watchlist import watchlist_add_command, watchlist_remove_command, watchlist_get_command

@pytest.mark.asyncio
@patch('src.common.utils.http_client.httpx.AsyncClient.post') # MOCK: httpx.AsyncClient.post 메서드
async def test_watchlist_add_command_success(mock_post):
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    # MOCK: httpx.Response 객체
    # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_response = AsyncMock(status_code=200)
    # json() 메서드는 비동기적으로 호출될 수 있으므로, 반환값을 직접 설정합니다.
    mock_response.json.return_value = {"message": "관심종목 추가 완료"}
    # mock_post (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_post.return_value = mock_response

    await watchlist_add_command(update, context)

    # mock_post (AsyncMock)가 한 번 호출되었는지 확인합니다.
    mock_post.assert_called_once()
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with("관심종목 추가 완료")

@pytest.mark.asyncio
async def test_watchlist_add_command_no_symbol():
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []

    await watchlist_add_command(update, context)

    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with(
        "사용법: /watchlist_add [종목코드] 예: /watchlist_add 005930"
    )

@pytest.mark.asyncio
@patch('src.common.utils.http_client.httpx.AsyncClient.post') # MOCK: httpx.AsyncClient.post 메서드
async def test_watchlist_add_command_api_error(mock_post):
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    # MOCK: httpx.Response 객체
    # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_response = AsyncMock(status_code=500)
    # mock_post (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_post.return_value = mock_response

    await watchlist_add_command(update, context)

    # mock_post (AsyncMock)가 한 번 호출되었는지 확인합니다.
    mock_post.assert_called_once()
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with(
        "관심종목 추가 실패: API 응답 코드 500"
    )

@pytest.mark.asyncio
@patch('src.common.utils.http_client.httpx.AsyncClient.delete') # MOCK: httpx.AsyncClient.delete 메서드
async def test_watchlist_remove_command_success(mock_delete):
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    # MOCK: httpx.Response 객체
    # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_response = AsyncMock(status_code=200)
    # json() 메서드는 비동기적으로 호출될 수 있으므로, 반환값을 직접 설정합니다.
    mock_response.json.return_value = {"message": "관심종목 제거 완료"}
    # mock_delete (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_delete.return_value = mock_response

    await watchlist_remove_command(update, context)

    # mock_delete (AsyncMock)가 한 번 호출되었는지 확인합니다.
    mock_delete.assert_called_once()
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with("관심종목 제거 완료")

@pytest.mark.asyncio
async def test_watchlist_remove_command_no_symbol():
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []

    await watchlist_remove_command(update, context)

    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with(
        "사용법: /watchlist_remove [종목코드] 예: /watchlist_remove 005930"
    )

@pytest.mark.asyncio
@patch('src.common.utils.http_client.httpx.AsyncClient.delete') # MOCK: httpx.AsyncClient.delete 메서드
async def test_watchlist_remove_command_api_error(mock_delete):
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    # MOCK: httpx.Response 객체
    # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_response = AsyncMock(status_code=500)
    # mock_delete (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_delete.return_value = mock_response

    await watchlist_remove_command(update, context)

    # mock_delete (AsyncMock)가 한 번 호출되었는지 확인합니다.
    mock_delete.assert_called_once()
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with(
        "관심종목 제거 실패: API 응답 코드 500"
    )

@pytest.mark.asyncio
@patch('src.common.utils.http_client.httpx.AsyncClient.get') # MOCK: httpx.AsyncClient.get 메서드
async def test_watchlist_get_command_success(mock_get):
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    # MOCK: httpx.Response 객체
    # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_response = AsyncMock(status_code=200)
    # json() 메서드는 비동기적으로 호출될 수 있으므로, 반환값을 직접 설정합니다.
    mock_response.json.return_value = {"watchlist": ["005930 삼성전자", "000660 SK하이닉스"]}
    # mock_get (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_get.return_value = mock_response

    await watchlist_get_command(update, context)

    # mock_get (AsyncMock)가 한 번 호출되었는지 확인합니다.
    mock_get.assert_called_once()
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with(
        "[관심종목 목록]\n005930 삼성전자\n000660 SK하이닉스"
    )

@pytest.mark.asyncio
@patch('src.common.utils.http_client.httpx.AsyncClient.get') # MOCK: httpx.AsyncClient.get 메서드
async def test_watchlist_get_command_no_watchlist(mock_get):
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    # MOCK: httpx.Response 객체
    # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_response = AsyncMock(status_code=200)
    # json() 메서드는 비동기적으로 호출될 수 있으므로, 반환값을 직접 설정합니다.
    mock_response.json.return_value = {"watchlist": []}
    # mock_get (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_get.return_value = mock_response

    await watchlist_get_command(update, context)

    # mock_get (AsyncMock)가 한 번 호출되었는지 확인합니다.
    mock_get.assert_called_once()
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with("관심종목이 없습니다.")

@pytest.mark.asyncio
@patch('src.common.utils.http_client.httpx.AsyncClient.get') # MOCK: httpx.AsyncClient.get 메서드
async def test_watchlist_get_command_api_error(mock_get):
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    # MOCK: httpx.Response 객체
    # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_response = AsyncMock(status_code=500)
    # mock_get (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_get.return_value = mock_response

    await watchlist_get_command(update, context)

    # mock_get (AsyncMock)가 한 번 호출되었는지 확인합니다.
    mock_get.assert_called_once()
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with(
        "관심종목 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: 500)"
    )
