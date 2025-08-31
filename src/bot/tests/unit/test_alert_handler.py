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
    update = AsyncMock(spec=Update)
    update.effective_user.id = 123
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=CallbackContext)
    context.user_data = {}
    yield update, context

@pytest.mark.asyncio
@patch('src.common.utils.http_client.get_retry_client')
@patch('src.bot.handlers.alert._api_set_price_alert')
async def test_set_price_alert_success(mock_api_set_alert, mock_get_client, mock_update_context):
    """가격 알림 설정 성공 테스트."""
    update, context = mock_update_context
    context.args = ["005930", "80000", "이상"]

    mock_register_response = AsyncMock(spec=httpx.Response)
    mock_register_response.status_code = 200
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.put.return_value = mock_register_response
    mock_get_client.return_value.__aenter__.return_value = mock_client

    mock_api_response = AsyncMock(spec=httpx.Response)
    mock_api_response.status_code = 200
    mock_api_response.raise_for_status = MagicMock()
    mock_api_set_alert.return_value = mock_api_response

    await set_price_alert(update, context)

    update.message.reply_text.assert_awaited_once_with("✅ '005930'의 가격 알림을 80000.0원 이상으로 설정했습니다.")

@pytest.mark.asyncio
@patch('src.common.utils.http_client.get_retry_client')
async def test_set_price_alert_invalid_args(mock_get_client, mock_update_context):
    """유효하지 않은 인자에 대한 오류 메시지 테스트."""
    update, context = mock_update_context
    context.args = ["005930", "abc"]

    mock_register_response = AsyncMock(spec=httpx.Response)
    mock_register_response.status_code = 200
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.put.return_value = mock_register_response
    mock_get_client.return_value.__aenter__.return_value = mock_client

    await set_price_alert(update, context)

    update.message.reply_text.assert_awaited_once()
    assert "사용법" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
@patch('src.common.utils.http_client.get_retry_client')
@patch('src.bot.handlers.alert._api_search_stocks')
async def test_alert_add_multiple_results(mock_api_search, mock_get_client, mock_update_context):
    """여러 검색 결과가 있는 경우 알림 추가 테스트."""
    update, context = mock_update_context
    context.args = ["카카오"]

    mock_register_response = AsyncMock(spec=httpx.Response)
    mock_register_response.status_code = 200
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.put.return_value = mock_register_response
    mock_get_client.return_value.__aenter__.return_value = mock_client
    
    mock_api_search.return_value = [
        {"symbol": "035720", "name": "카카오"},
        {"symbol": "035420", "name": "카카오게임즈"}
    ]

    await alert_add(update, context)

    update.message.reply_text.assert_awaited_once()
    assert "어떤 종목을 추가" in update.message.reply_text.call_args.kwargs['text']
    assert isinstance(update.message.reply_text.call_args.kwargs['reply_markup'], InlineKeyboardMarkup)

@pytest.mark.asyncio
@patch('src.common.utils.http_client.get_retry_client')
@patch('src.bot.handlers.alert._api_get_alerts')
async def test_alert_list_success(mock_api_get_alerts, mock_get_client, mock_update_context):
    """알림 목록 성공적인 조회 테스트."""
    update, context = mock_update_context

    mock_register_response = AsyncMock(spec=httpx.Response)
    mock_register_response.status_code = 200
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.put.return_value = mock_register_response
    mock_get_client.return_value.__aenter__.return_value = mock_client

    mock_api_get_alerts.return_value = [
        {"id": 1, "symbol": "005930", "target_price": 80000.0, "condition": "gte", "is_active": True, "repeat_interval": "daily", "stock_name": "삼성전자"}
    ]

    await alert_list(update, context)

    update.message.reply_text.assert_awaited_once()
    sent_text = update.message.reply_text.call_args.kwargs['text']
    assert "삼성전자" in sent_text
    assert "80000.0원 이상" in sent_text

@pytest.mark.asyncio
@patch('src.common.utils.http_client.get_retry_client')
@patch('src.bot.handlers.alert._api_delete_alert')
async def test_alert_remove_success(mock_api_delete, mock_get_client, mock_update_context):
    """알림 성공적인 제거 테스트."""
    update, context = mock_update_context
    context.user_data['alert_map'] = {'1': 101}
    context.args = ["1"]

    mock_register_response = AsyncMock(spec=httpx.Response)
    mock_register_response.status_code = 200
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.put.return_value = mock_register_response
    mock_get_client.return_value.__aenter__.return_value = mock_client

    mock_api_response = AsyncMock(spec=httpx.Response)
    mock_api_response.status_code = 200
    mock_api_response.raise_for_status = MagicMock()
    mock_api_delete.return_value = mock_api_response

    await alert_remove(update, context)

    update.message.reply_text.assert_awaited_once_with("알림 1번이 삭제되었습니다.")
