import pytest
from unittest.mock import AsyncMock, patch, Mock
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.handlers.trade import trade_simulate_command, trade_history_command

@pytest.mark.asyncio
@patch('src.common.utils.http_client.httpx.AsyncClient.post') # MOCK: httpx.AsyncClient.post 메서드
async def test_trade_simulate_command_success(mock_post):
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["buy", "005930", "10000", "10"]

    # MOCK: httpx.Response 객체
    # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_response = AsyncMock(status_code=200)
    # json() 메서드는 비동기적으로 호출될 수 있으므로, 반환값을 직접 설정합니다.
    mock_response.json.return_value = {"message": "모의 거래 기록 완료"}
    # mock_post (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_post.return_value = mock_response

    await trade_simulate_command(update, context)

    # mock_post (AsyncMock)가 한 번 호출되었는지 확인합니다.
    mock_post.assert_called_once()
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with("모의 거래 기록 완료")

@pytest.mark.asyncio
async def test_trade_simulate_command_invalid_args():
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["buy", "005930", "10000"]

    await trade_simulate_command(update, context)

    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with(
        "사용법: /trade_simulate [buy/sell] [종목코드] [가격] [수량] 예: /trade_simulate buy 005930 10000 10"
    )

@pytest.mark.asyncio
@patch('src.common.utils.http_client.httpx.AsyncClient.post') # MOCK: httpx.AsyncClient.post 메서드
async def test_trade_simulate_command_api_error(mock_post):
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["buy", "005930", "10000", "10"]

    # MOCK: httpx.Response 객체
    # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_response = AsyncMock(status_code=500)
    # mock_post (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_post.return_value = mock_response

    await trade_simulate_command(update, context)

    # mock_post (AsyncMock)가 한 번 호출되었는지 확인합니다.
    mock_post.assert_called_once()
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with(
        "모의 거래 기록 실패: API 응답 코드 500"
    )

@pytest.mark.asyncio
@patch('src.common.utils.http_client.httpx.AsyncClient.get') # MOCK: httpx.AsyncClient.get 메서드
async def test_trade_history_command_success(mock_get):
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
    mock_response.json.return_value = {"trades": [
        {"trade_time": "2023-01-01T10:00:00", "trade_type": "buy", "symbol": "005930", "price": 10000, "quantity": 10},
        {"trade_time": "2023-01-02T11:00:00", "trade_type": "sell", "symbol": "005930", "price": 10500, "quantity": 5}
    ]}
    # mock_get (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_get.return_value = mock_response

    await trade_history_command(update, context)

    # mock_get (AsyncMock)가 한 번 호출되었는지 확인합니다.
    mock_get.assert_called_once()
    expected_msg = "[모의 거래 이력]\n"
    expected_msg += "2023-01-01T10:00:00 | buy | 005930 | 10000 | 10\n"
    expected_msg += "2023-01-02T11:00:00 | sell | 005930 | 10500 | 5\n"
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with(expected_msg)

@pytest.mark.asyncio
@patch('src.common.utils.http_client.httpx.AsyncClient.get') # MOCK: httpx.AsyncClient.get 메서드
async def test_trade_history_command_no_history(mock_get):
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
    mock_response.json.return_value = {"trades": []}
    # mock_get (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_get.return_value = mock_response

    await trade_history_command(update, context)

    # mock_get (AsyncMock)가 한 번 호출되었는지 확인합니다.
    mock_get.assert_called_once()
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with("모의 거래 기록이 없습니다.")

@pytest.mark.asyncio
@patch('src.common.utils.http_client.httpx.AsyncClient.get') # MOCK: httpx.AsyncClient.get 메서드
async def test_trade_history_command_api_error(mock_get):
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

    await trade_history_command(update, context)

    # mock_get (AsyncMock)가 한 번 호출되었는지 확인합니다.
    mock_get.assert_called_once()
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_called_once_with(
        "모의 거래 이력 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: 500)"
    )