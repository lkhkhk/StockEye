import pytest
from unittest.mock import AsyncMock, patch, call

from telegram import Update, Message
from telegram.ext import ContextTypes

from src.bot.handlers.alert import list_alerts, pause_alert, resume_alert

@pytest.fixture
def mock_update_context():
    """Provides a mock Update and Context object for tests."""
    update = AsyncMock(spec=Update)
    
    mock_message = AsyncMock(spec=Message)
    mock_message.reply_text = AsyncMock()
    update.message = mock_message
    update.effective_message = mock_message
    
    update.effective_chat = AsyncMock()
    update.effective_chat.edit_message_text = AsyncMock()
    
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {'auth_token': 'test_token', 'alert_map': {}}
    
    return update, context

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_get_price_alerts')
@patch('src.bot.handlers.alert._api_get_disclosure_alerts')
@patch('src.bot.handlers.alert._api_search_stocks')
async def test_list_alerts_mixed_and_missing_name(mock_search_stocks, mock_get_disclosure_alerts, mock_get_price_alerts, mock_update_context):
    """
    Tests listing alerts with a mix of valid stock_names, missing stock_names (None),
    and disclosure alerts to ensure all names are fetched and displayed correctly.
    """
    update, context = mock_update_context
    
    mock_get_price_alerts.return_value = [
        # Case 1: stock_name is provided and valid
        {'id': 1, 'symbol': '005930', 'stock_name': '삼성전자', 'target_price': 80000, 'condition': 'gte', 'is_active': True},
        # Case 2: stock_name is None, should be fetched via _api_search_stocks
        {'id': 2, 'symbol': '000660', 'stock_name': None, 'change_percent': 5, 'change_type': 'up', 'is_active': False}
    ]
    mock_get_disclosure_alerts.return_value = [
        # Case 3: Disclosure alert, name must be fetched
        {'id': 3, 'symbol': '035720', 'is_active': True}
    ]

    # Mock the search API to return names for symbols that need fetching
    def search_side_effect(symbol, auth_token):
        if symbol == '000660':
            return {'items': [{'name': 'SK하이닉스'}]}
        if symbol == '035720':
            return {'items': [{'name': '카카오'}]}
        return {'items': []}
    
    mock_search_stocks.side_effect = search_side_effect

    await list_alerts(update, context)

    # Verify that search was called only for the symbols that needed it
    mock_search_stocks.assert_has_calls([
        call('000660', 'test_token'),
        call('035720', 'test_token')
    ], any_order=True)
    assert mock_search_stocks.call_count == 2

    # Verify the final output message
    reply_text = update.effective_message.reply_text.call_args.kwargs['text']
    
    assert "🔔 **나의 알림 목록**" in reply_text
    assert "1. 삼성전자 (005930) - 80,000원 이상 (활성)" in reply_text
    assert "2. SK하이닉스 (000660) - 5% 상승 시 (비활성)" in reply_text
    assert "3. 카카오 (035720) (활성)" in reply_text

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_update_price_alert_status')
@patch('src.bot.handlers.alert.list_alerts')
async def test_pause_alert_active(mock_list_alerts, mock_update_status, mock_update_context):
    """Tests pausing an active alert."""
    update, context = mock_update_context
    context.args = ['pause', '1']
    context.user_data['alert_map'] = {'1': {'id': 101, 'type': 'price', 'is_active': True}}
    
    await pause_alert(update, context)
    
    mock_update_status.assert_called_once_with(101, False, 'test_token')
    update.message.reply_text.assert_called_once_with("✅ 가격 알림 1번이 일시정지되었습니다.")
    mock_list_alerts.assert_called_once()

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_update_price_alert_status')
@patch('src.bot.handlers.alert.list_alerts')
async def test_pause_alert_inactive(mock_list_alerts, mock_update_status, mock_update_context):
    """Tests pausing an already inactive alert."""
    update, context = mock_update_context
    context.args = ['pause', '1']
    context.user_data['alert_map'] = {'1': {'id': 101, 'type': 'price', 'is_active': False}}
    
    await pause_alert(update, context)
    
    mock_update_status.assert_not_called()
    update.message.reply_text.assert_called_once_with("ℹ️ 가격 알림 1번은 이미 일시정지 상태입니다.")
    mock_list_alerts.assert_called_once()

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_update_price_alert_status')
@patch('src.bot.handlers.alert.list_alerts')
async def test_resume_alert_inactive(mock_list_alerts, mock_update_status, mock_update_context):
    """Tests resuming an inactive alert."""
    update, context = mock_update_context
    context.args = ['resume', '1']
    context.user_data['alert_map'] = {'1': {'id': 101, 'type': 'price', 'is_active': False}}
    
    await resume_alert(update, context)
    
    mock_update_status.assert_called_once_with(101, True, 'test_token')
    update.message.reply_text.assert_called_once_with("✅ 가격 알림 1번이 재개되었습니다.")
    mock_list_alerts.assert_called_once()

@pytest.mark.asyncio
@patch('src.bot.handlers.alert._api_update_price_alert_status')
@patch('src.bot.handlers.alert.list_alerts')
async def test_resume_alert_active(mock_list_alerts, mock_update_status, mock_update_context):
    """Tests resuming an already active alert."""
    update, context = mock_update_context
    context.args = ['resume', '1']
    context.user_data['alert_map'] = {'1': {'id': 101, 'type': 'price', 'is_active': True}}
    
    await resume_alert(update, context)
    
    mock_update_status.assert_not_called()
    update.message.reply_text.assert_called_once_with("ℹ️ 가격 알림 1번은 이미 활성 상태입니다.")
    mock_list_alerts.assert_called_once()