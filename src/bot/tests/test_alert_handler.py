import pytest
from unittest.mock import AsyncMock, patch
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.handlers.alert import set_price_alert, alert_add, alert_list, alert_remove

@pytest.mark.asyncio
async def test_set_price_alert_success():
    """유효한 입력으로 가격 알림 설정 성공 테스트"""
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    update.message.reply_text = AsyncMock()

    # Mock update.effective_user
    update.effective_user.id = 123
    update.effective_user.username = "testuser"
    update.effective_user.first_name = "Test"
    update.effective_user.last_name = "User"

    # Mock context.args
    context.args = ["042660", "75000", "이상"]

    # Mock session.post response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={"message": "Alert set successfully"})

    with patch('src.bot.handlers.alert.session.post', new=AsyncMock(return_value=mock_response)) as mock_post:
        await set_price_alert(update, context)

        # Check if session.post was called with correct arguments
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0].endswith("/bot/alert/price")
        assert kwargs['json']['symbol'] == "042660"
        assert kwargs['json']['target_price'] == 75000.0
        assert kwargs['json']['condition'] == "gte"
        assert kwargs['json']['telegram_user_id'] == 123
        assert kwargs['json']['repeat_interval'] is None # 기본값 확인

        # Check if reply_text was called with success message
        update.message.reply_text.assert_called_once_with("✅ '042660'의 가격 알림을 '75,000.0원 이상'(으)로 설정했습니다.")

@pytest.mark.asyncio
async def test_set_price_alert_invalid_args():
    """잘못된 인자 입력 시 오류 메시지 테스트"""
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    update.message.reply_text = AsyncMock()

    context.args = ["042660", "abc", "이상"] # Invalid price

    with patch('src.bot.handlers.alert.session.post') as mock_post:
        await set_price_alert(update, context)

        # session.post should not be called
        mock_post.assert_not_called()

        # Check if reply_text was called with error message
        update.message.reply_text.assert_called_once_with("입력이 잘못되었습니다. 가격은 숫자여야 하며, 조건은 '이상' 또는 '이하'여야 합니다.")

@pytest.mark.asyncio
async def test_set_price_alert_api_failure():
    """API 호출 실패 시 오류 메시지 테스트"""
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    update.message.reply_text = AsyncMock()

    update.effective_user.id = 123
    update.effective_user.username = "testuser"
    update.effective_user.first_name = "Test"
    update.effective_user.last_name = "User"

    context.args = ["042660", "75000", "이상"]

    # Mock session.post to return a non-200 status code
    mock_response = AsyncMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"

    with patch('src.bot.handlers.alert.session.post', new=AsyncMock(return_value=mock_response)) as mock_post:
        await set_price_alert(update, context)

        mock_post.assert_called_once()
        update.message.reply_text.assert_called_once_with("❌ 가격 알림 설정 실패: 400 - Bad Request")

@pytest.mark.asyncio
async def test_set_price_alert_with_repeat_interval():
    """repeat_interval을 포함하여 가격 알림 설정 성공 테스트"""
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    update.message.reply_text = AsyncMock()

    update.effective_user.id = 124
    update.effective_user.username = "testuser_repeat"
    update.effective_user.first_name = "TestRepeat"
    update.effective_user.last_name = "UserRepeat"

    context.args = ["042660", "75000", "이상"]
    # repeat_interval을 context.args에 직접 전달하는 대신, 함수 인자로 전달되는 경우를 가정
    # 실제 봇에서는 alert_set_repeat_callback에서 이 함수를 호출할 때 repeat_interval을 전달할 수 있음
    # 여기서는 테스트를 위해 직접 인자로 전달
    repeat_interval_value = "weekly"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={"message": "Alert set successfully"})

    with patch('src.bot.handlers.alert.session.post', new=AsyncMock(return_value=mock_response)) as mock_post:
        await set_price_alert(update, context, repeat_interval=repeat_interval_value)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0].endswith("/bot/alert/price")
        assert kwargs['json']['symbol'] == "042660"
        assert kwargs['json']['target_price'] == 75000.0
        assert kwargs['json']['condition'] == "gte"
        assert kwargs['json']['telegram_user_id'] == 124
        assert kwargs['json']['repeat_interval'] == repeat_interval_value

        update.message.reply_text.assert_called_once_with("✅ '042660'의 가격 알림을 '75,000.0원 이상'(으)로 설정했습니다.")

@pytest.mark.asyncio
async def test_alert_add_single_result():
    """단일 종목 검색 결과에 대한 alert_add 테스트"""
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    update.message.reply_text = AsyncMock()
    update.callback_query = AsyncMock()

    context.args = ["삼성전자"]

    mock_search_response = AsyncMock()
    mock_search_response.status_code = 200
    mock_search_response.json = AsyncMock(return_value=[
        {"symbol": "005930", "name": "삼성전자"}
    ])

    with patch('src.bot.handlers.alert.session.get', new=AsyncMock(return_value=mock_search_response)) as mock_get:
        await alert_add(update, context)

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0].endswith("/symbols/search")
        assert kwargs['params']['query'] == "삼성전자"

        update.message.reply_text.assert_called_once()
        call_args, call_kwargs = update.message.reply_text.call_args
        assert "삼성전자(005930)'에 대한 알림을 설정합니다." in call_args[0]
        assert isinstance(call_kwargs['reply_markup'], InlineKeyboardMarkup)

@pytest.mark.asyncio
async def test_alert_add_multiple_results():
    """다중 종목 검색 결과에 대한 alert_add 테스트"""
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    update.message.reply_text = AsyncMock()
    update.callback_query = AsyncMock()

    context.args = ["카카오"]

    mock_search_response = AsyncMock()
    mock_search_response.status_code = 200
    mock_search_response.json = AsyncMock(return_value=[
        {"symbol": "035720", "name": "카카오"},
        {"symbol": "035420", "name": "카카오게임즈"}
    ])

    with patch('src.bot.handlers.alert.session.get', new=AsyncMock(return_value=mock_search_response)) as mock_get:
        await alert_add(update, context)

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0].endswith("/symbols/search")
        assert kwargs['params']['query'] == "카카오"

        update.message.reply_text.assert_called_once()
        call_args, call_kwargs = update.message.reply_text.call_args
        assert "여러 종목이 검색되었습니다." in call_args[0]
        assert isinstance(call_kwargs['reply_markup'], InlineKeyboardMarkup)
        assert len(call_kwargs['reply_markup'].inline_keyboard) == 2

@pytest.mark.asyncio
async def test_alert_add_no_result():
    """종목 검색 결과 없음 테스트"""
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    update.message.reply_text = AsyncMock()
    update.callback_query = AsyncMock()

    context.args = ["없는종목"]

    mock_search_response = AsyncMock()
    mock_search_response.status_code = 200
    mock_search_response.json = AsyncMock(return_value=[])

    with patch('src.bot.handlers.alert.session.get', new=AsyncMock(return_value=mock_search_response)) as mock_get:
        await alert_add(update, context)

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0].endswith("/symbols/search")
        assert kwargs['params']['query'] == "없는종목"

        update.message.reply_text.assert_called_once_with("'없는종목'에 해당하는 종목을 찾을 수 없습니다.")

@pytest.mark.asyncio
async def test_alert_list_success():
    """알림 목록 조회 성공 테스트"""
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    update.message.reply_text = AsyncMock()
    context.user_data = {} # user_data 초기화

    mock_alerts_response = AsyncMock()
    mock_alerts_response.status_code = 200
    mock_alerts_response.json = AsyncMock(return_value=[
        {
            "id": 1,
            "symbol": "005930",
            "name": "삼성전자",
            "target_price": 75000.0,
            "condition": "gte",
            "notify_on_disclosure": True,
            "repeat_interval": "daily",
            "is_active": True
        },
        {
            "id": 2,
            "symbol": "035720",
            "name": "카카오",
            "target_price": None,
            "condition": None,
            "notify_on_disclosure": True,
            "repeat_interval": "안 함",
            "is_active": True
        }
    ])

    mock_price_response_samsung = AsyncMock()
    mock_price_response_samsung.status_code = 200
    mock_price_response_samsung.json.return_value = {
        "current_price": 76000,
        "change": 1000,
        "change_rate": 1.33
    }

    mock_price_response_kakao = AsyncMock()
    mock_price_response_kakao.status_code = 200
    mock_price_response_kakao.json.return_value = {
        "current_price": 50000,
        "change": -500,
        "change_rate": -0.99
    }

    with patch('src.bot.handlers.alert.session.get') as mock_get:
        mock_get.side_effect = [
            mock_alerts_response, # 첫 번째 호출: /alerts/
            mock_price_response_samsung, # 두 번째 호출: /symbols/005930/current_price_and_change
            mock_price_response_kakao # 세 번째 호출: /symbols/035720/current_price_and_change
        ]
        await alert_list(update, context)

        update.message.reply_text.assert_called_once()
        call_args, _ = update.message.reply_text.call_args
        expected_message_part1 = "- 1. 005930 (삼성전자): 75,000.0원 이상 / 공시ON / 반복: daily (활성)"
        expected_message_part2 = "  현재가: 76,000원 (+1,000원, +1.33%)"
        expected_message_part3 = "- 2. 035720 (카카오): 가격 미설정 / 공시ON / 반복: 안 함 (활성)"
        expected_message_part4 = "  현재가: 50,000원 (-500원, -0.99%)"

        assert expected_message_part1 in call_args[0]
        assert expected_message_part2 in call_args[0]
        assert expected_message_part3 in call_args[0]
        assert expected_message_part4 in call_args[0]
        assert context.user_data['alert_map'] == {'1': 1, '2': 2}

@pytest.mark.asyncio
async def test_alert_list_no_alerts():
    """등록된 알림이 없을 때 테스트"""
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    update.message.reply_text = AsyncMock()

    mock_alerts_response = AsyncMock()
    mock_alerts_response.status_code = 200
    mock_alerts_response.json = AsyncMock(return_value=[])

    with patch('src.bot.handlers.alert.session.get', new=AsyncMock(return_value=mock_alerts_response)) as mock_get:
        await alert_list(update, context)

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0].endswith("/alerts/")

        update.message.reply_text.assert_called_once_with("등록된 알림이 없습니다.")

@pytest.mark.asyncio
async def test_alert_remove_success():
    """알림 삭제 성공 테스트"""
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    update.message.reply_text = AsyncMock()
    context.user_data = {'alert_map': {'1': 100}} # Mock alert_map

    context.args = ["1"]

    mock_delete_response = AsyncMock()
    mock_delete_response.status_code = 200
    mock_delete_response.json = AsyncMock(return_value={"message": "Alert deleted successfully"})

    with patch('src.bot.handlers.alert.session.delete', new=AsyncMock(return_value=mock_delete_response)) as mock_delete:
        await alert_remove(update, context)

        mock_delete.assert_called_once()
        args, kwargs = mock_delete.call_args
        assert args[0].endswith("/alerts/100")

        update.message.reply_text.assert_called_once_with("알림 번호 1 (ID: 100) 삭제 완료")
        assert 'alert_map' not in context.user_data # alert_map이 삭제되었는지 확인

@pytest.mark.asyncio
async def test_alert_remove_invalid_args():
    """알림 삭제 시 잘못된 인자 테스트"""
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    update.message.reply_text = AsyncMock()

    context.args = ["abc"]

    with patch('src.bot.handlers.alert.session.delete') as mock_delete:
        await alert_remove(update, context)

        mock_delete.assert_not_called()
        update.message.reply_text.assert_called_once_with("사용법: /alert_remove [알림 번호]")

@pytest.mark.asyncio
async def test_alert_remove_api_failure():
    """알림 삭제 API 호출 실패 테스트"""
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    update.message.reply_text = AsyncMock()
    context.user_data = {'alert_map': {'1': 100}} # Mock alert_map

    context.args = ["1"]

    mock_delete_response = AsyncMock()
    mock_delete_response.status_code = 404
    mock_delete_response.text = "Not Found"

    with patch('src.bot.handlers.alert.session.delete', new=AsyncMock(return_value=mock_delete_response)) as mock_delete:
        await alert_remove(update, context)

        mock_delete.assert_called_once()
        args, kwargs = mock_delete.call_args
        assert args[0].endswith("/alerts/100")

        update.message.reply_text.assert_called_once_with("알림 삭제 실패: Not Found")