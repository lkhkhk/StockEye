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
    """테스트를 위한 Update 및 CallbackContext 모의 객체를 제공합니다."""
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.CallbackContext 객체
    # AsyncMock: CallbackContext 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=CallbackContext)
    context.user_data = {}

    # MOCK: httpx.Response 객체
    # mock_register_response는 API 호출의 응답을 모의합니다.
    mock_register_response = AsyncMock(spec=httpx.Response)
    mock_register_response.status_code = 200
    # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
    mock_register_response.raise_for_status = MagicMock()
    # json() 메서드는 비동기적으로 호출될 수 있으므로, 반환값을 직접 설정합니다.
    mock_register_response.json.return_value = {"message": "User registered successfully"}

    # MOCK: src.common.utils.http_client.get_retry_client
    # get_retry_client 함수를 모의하여 실제 HTTP 요청을 보내지 않도록 합니다.
    with patch('src.common.utils.http_client.get_retry_client') as mock_get_client_decorator:
        # AsyncMock: httpx.AsyncClient 객체를 모의합니다. 비동기적으로 동작합니다.
        mock_client_decorator = AsyncMock(spec=httpx.AsyncClient)
        # mock_client_decorator.put (AsyncMock) 호출 시 mock_register_response를 반환하도록 설정합니다.
        mock_client_decorator.put.return_value = mock_register_response
        # __aenter__는 비동기 컨텍스트 매니저 진입 시 호출되는 메서드입니다.
        # 이 메서드가 mock_client_decorator를 반환하도록 설정하여, `async with client:` 구문에서
        # `client` 변수가 mock_client_decorator를 참조하게 합니다.
        mock_get_client_decorator.return_value.__aenter__.return_value = mock_client_decorator
        yield update, context

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_set_price_alert') # MOCK: _api_set_price_alert 함수
async def test_set_price_alert_success(mock_api_call, mock_update_context):
    """가격 알림 설정 성공 테스트."""
    update, context = mock_update_context
    context.args = ["005930", "80000", "이상"]

    # MOCK: httpx.Response 객체
    # mock_response는 API 호출의 응답을 모의합니다.
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
    mock_response.raise_for_status = MagicMock() 
    # mock_api_call (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_api_call.return_value = mock_response

    await set_price_alert(update, context)

    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once_with("✅ '005930'의 가격 알림을 80000.0원 이상으로 설정했습니다.")

@pytest.mark.asyncio
async def test_set_price_alert_invalid_args(mock_update_context):
    """유효하지 않은 인자에 대한 오류 메시지 테스트."""
    update, context = mock_update_context
    context.args = ["005930", "abc"]

    await set_price_alert(update, context)

    # update.message.reply_text (AsyncMock)가 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once()
    assert "사용법" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_search_stocks') # MOCK: _api_search_stocks 함수
async def test_alert_add_multiple_results(mock_api_call, mock_update_context):
    """여러 검색 결과가 있는 경우 알림 추가 테스트."""
    update, context = mock_update_context
    context.args = ["카카오"]
    
    # MOCK: httpx.Response 객체
    # mock_response는 API 호출의 응답을 모의합니다.
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
    mock_response.raise_for_status = MagicMock()
    # json() 메서드는 비동기적으로 호출될 수 있으므로, 반환값을 직접 설정합니다.
    mock_response.json.return_value = [
        {"symbol": "035720", "name": "카카오"},
        {"symbol": "035420", "name": "카카오게임즈"}
    ]
    # mock_api_call (AsyncMock) 호출 시 mock_response.json.return_value를 반환하도록 설정합니다.
    mock_api_call.return_value = mock_response.json.return_value 

    await alert_add(update, context)

    # update.message.reply_text (AsyncMock)가 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once()
    # reply_markup이 사용될 때 텍스트가 kwargs에 있는지 확인합니다.
    assert "어떤 종목을 추가" in update.message.reply_text.call_args.kwargs['text'] 
    assert isinstance(update.message.reply_text.call_args.kwargs['reply_markup'], InlineKeyboardMarkup)

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_get_alerts') # MOCK: _api_get_alerts 함수
async def test_alert_list_success(mock_api_call, mock_update_context):
    """알림 목록 성공적인 조회 테스트."""
    update, context = mock_update_context

    # mock_api_call (AsyncMock) 호출 시 모의 알림 목록을 반환하도록 설정합니다.
    mock_api_call.return_value = [
        {"id": 1, "symbol": "005930", "name": "삼성전자", "target_price": 80000.0, "condition": "gte", "is_active": True, "repeat_interval": "daily"}
    ]

    await alert_list(update, context)

    # update.message.reply_text (AsyncMock)가 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once()
    # 텍스트의 위치 인자를 올바르게 접근하여 예상되는 문자열이 포함되어 있는지 확인합니다.
    sent_text = update.message.reply_text.call_args[0][0]
    assert "삼성전자" in sent_text
    assert "80000.0원 이상" in sent_text

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_delete_alert') # MOCK: _api_delete_alert 함수
async def test_alert_remove_success(mock_api_call, mock_update_context):
    """알림 성공적인 제거 테스트."""
    update, context = mock_update_context
    context.user_data['alert_map'] = {'1': 101}
    context.args = ["1"]

    # MOCK: httpx.Response 객체
    # mock_response는 API 호출의 응답을 모의합니다.
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
    mock_response.raise_for_status = MagicMock()
    # mock_api_call (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_api_call.return_value = mock_response

    await alert_remove(update, context)

    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once_with("알림 1번이 삭제되었습니다.")