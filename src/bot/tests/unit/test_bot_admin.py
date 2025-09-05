import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update
from telegram.ext import CallbackContext
import httpx
from datetime import datetime

from src.bot.handlers.admin import (
    admin_command,
    admin_show_schedules,
    admin_trigger_job,
    admin_stats,
    admin_only,
    get_auth_token,
    trigger_job_callback,
    admin_update_historical_prices # Import the new function
)

@pytest.fixture
def mock_update_context():
    """테스트를 위한 Update 및 CallbackContext 모의 객체를 제공합니다."""
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_chat = AsyncMock()
    update.effective_chat.id = 12345
    update.effective_user = AsyncMock()
    update.effective_user.id = 12345
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    update.callback_query = AsyncMock()
    # MOCK: telegram.ext.CallbackContext 객체
    # AsyncMock: CallbackContext 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=CallbackContext)
    context.bot = AsyncMock()
    # context.bot.send_message = AsyncMock() # REMOVED: Will be patched per test
    return update, context

class TestAdminOnlyDecorator:
    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.ADMIN_ID', "12345") # MOCK: ADMIN_ID 환경 변수
    async def test_admin_only_decorator_admin_user(self, mock_update_context):
        update, context = mock_update_context
        
        @admin_only
        async def test_func(update: Update, context: CallbackContext):
            return "Admin function executed"

        result = await test_func(update, context)
        assert result == "Admin function executed"
        # context.bot.send_message (AsyncMock)가 호출되지 않았는지 확인합니다.
        context.bot.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.ADMIN_ID', "admin_id") # MOCK: ADMIN_ID 환경 변수
    async def test_admin_only_decorator_non_admin_user(self, mock_update_context):
        update, context = mock_update_context
        update.effective_user.id = 99999

        @admin_only
        async def test_func(update: Update, context: CallbackContext):
            return "Admin function executed"

        result = await test_func(update, context)
        assert result is None
        # context.bot.send_message (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        context.bot.send_message.assert_awaited_once_with(chat_id=update.effective_chat.id, text="관리자 전용 명령어입니다.")


class TestGetAuthToken:
    @pytest.mark.asyncio
    async def test_get_auth_token_success(self):
        # MOCK: BOT_SECRET_KEY, API_V1_URL 환경 변수
        # MOCK: httpx.AsyncClient.post 메서드
        with patch('src.bot.handlers.admin.BOT_SECRET_KEY', 'test_secret_key'), \
             patch('src.bot.handlers.admin.API_V1_URL', 'http://localhost:8000/api/v1'), \
             patch('src.common.utils.http_client.httpx.AsyncClient.post') as mock_post:
            
            # MOCK: httpx.Response 객체
            # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
            mock_response = AsyncMock()
            mock_response.status_code = 200
            # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
            mock_response.raise_for_status = MagicMock()
            # MagicMock: json() 메서드를 모의합니다. 동기적으로 동작합니다.
            mock_response.json = MagicMock(return_value={"access_token": "test_token"})
            # mock_post (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
            mock_post.return_value = mock_response

            token = await get_auth_token(12345)
            assert token == "test_token"
            # mock_post (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
            mock_post.assert_awaited_once_with(
                "http://localhost:8000/api/v1/auth/bot/token",
                headers={"X-Bot-Secret-Key": "test_secret_key"},
                json={"telegram_id": 12345}
            )

    @pytest.mark.asyncio
    async def test_get_auth_token_no_secret_key(self):
        # MOCK: BOT_SECRET_KEY 환경 변수
        # MOCK: httpx.AsyncClient.post 메서드
        with patch('src.bot.handlers.admin.BOT_SECRET_KEY', None), \
             patch('src.common.utils.http_client.httpx.AsyncClient.post') as mock_post:
            token = await get_auth_token(12345)
            assert token is None
            # mock_post (AsyncMock)가 호출되지 않았는지 확인합니다.
            mock_post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_auth_token_http_error(self):
        # MOCK: BOT_SECRET_KEY, API_V1_URL 환경 변수
        # MOCK: httpx.AsyncClient.post 메서드
        with patch('src.bot.handlers.admin.BOT_SECRET_KEY', 'test_secret_key'), \
             patch('src.bot.handlers.admin.API_V1_URL', 'http://localhost:8000/api/v1'), \
             patch('src.common.utils.http_client.httpx.AsyncClient.post') as mock_post:
            # MOCK: httpx.Response 객체
            # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
            mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_response))
            # mock_post (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
            mock_post.return_value = mock_response

            token = await get_auth_token(12345)
            assert token is None
            # mock_post (AsyncMock)가 한 번 호출되었는지 확인합니다.
            mock_post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_auth_token_generic_exception(self):
        # MOCK: BOT_SECRET_KEY 환경 변수
        # MOCK: httpx.AsyncClient.post 메서드
        with patch('src.bot.handlers.admin.BOT_SECRET_KEY', 'test_secret_key'), \
             patch('src.common.utils.http_client.httpx.AsyncClient.post') as mock_post:
            # mock_post (AsyncMock) 호출 시 Exception을 발생시키도록 설정합니다.
            mock_post.side_effect = Exception("Network Error")

            token = await get_auth_token(12345)
            assert token is None
            # mock_post (AsyncMock)가 한 번 호출되었는지 확인합니다.
            mock_post.assert_awaited_once()


@pytest.mark.asyncio
@patch('src.bot.handlers.admin.ADMIN_ID', "12345") # MOCK: ADMIN_ID 환경 변수
async def test_admin_command(mock_update_context):
    update, context = mock_update_context
    await admin_command(update, context)
    # update.message.reply_text (AsyncMock)가 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once()
    assert "[관리자 전용 명령어 안내]" in update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_admin_show_schedules_success(mock_update_context):
    # MOCK: ADMIN_ID 환경 변수
    # MOCK: httpx.AsyncClient.get 메서드
    # MOCK: get_auth_token 함수
    with patch('src.bot.handlers.admin.ADMIN_ID', '12345'), \
         patch('src.common.utils.http_client.httpx.AsyncClient.get') as mock_http_get, \
         patch('src.bot.handlers.admin.get_auth_token', new_callable=AsyncMock, return_value="fake_token") as mock_get_token:

        update, context = mock_update_context
        
        # MOCK: httpx.Response 객체
        # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # MagicMock: json() 메서드를 모의합니다. 동기적으로 동작합니다.
        mock_response.json = MagicMock(return_value= {
            "jobs": [
                {"id": "job1", "name": "Update Master", "next_run_time": "2025-01-01T10:00:00+00:00"
                }
            ]
        })
        # mock_http_get (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
        mock_http_get.return_value = mock_response

        await admin_show_schedules(update, context)

        # mock_get_token (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다.
        mock_get_token.assert_awaited_once_with(update.effective_chat.id)
        # context.bot.send_message (AsyncMock)가 한 번 호출되었는지 확인합니다.
        context.bot.send_message.assert_awaited_once()
        sent_text = context.bot.send_message.call_args[1]['text']
        assert "job1" in sent_text
        assert "Update Master" in sent_text
        assert "2025-01-01 10:00:00" in sent_text


@pytest.mark.asyncio
async def test_admin_trigger_job_success(mock_update_context):
    # MOCK: ADMIN_ID 환경 변수
    # MOCK: httpx.AsyncClient.post 메서드
    # MOCK: get_auth_token 함수
    with patch('src.bot.handlers.admin.ADMIN_ID', '12345'), \
         patch('src.common.utils.http_client.httpx.AsyncClient.post') as mock_http_post, \
         patch('src.bot.handlers.admin.get_auth_token', new_callable=AsyncMock, return_value="fake_token") as mock_get_token:

        update, context = mock_update_context
        update.message.text = '/trigger_job test_job_id'
        
        # MOCK: httpx.Response 객체
        # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # mock_http_post (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
        mock_http_post.return_value = mock_response

        await admin_trigger_job(update, context)

        # mock_get_token (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다가.
        mock_get_token.assert_awaited_once_with(update.effective_chat.id)
        # context.bot.send_message (AsyncMock)가 한 번 호출되었는지 확인합니다가.
        context.bot.send_message.assert_awaited_once()
        sent_text = context.bot.send_message.call_args[1]['text']
        assert "잡 실행 요청 접수" in sent_text
        assert "test_job_id" in sent_text

@pytest.mark.asyncio
async def test_admin_stats_success(mock_update_context):
    # MOCK: ADMIN_ID 환경 변수
    # MOCK: httpx.AsyncClient.get 메서드
    # MOCK: get_auth_token 함수
    with patch('src.bot.handlers.admin.ADMIN_ID', '12345'), \
         patch('src.common.utils.http_client.httpx.AsyncClient.get') as mock_http_get, \
         patch('src.bot.handlers.admin.get_auth_token', new_callable=AsyncMock, return_value="fake_token") as mock_get_token:

        update, context = mock_update_context
        
        # MOCK: httpx.Response 객체
        # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # MagicMock: json() 메서드를 모의합니다. 동기적으로 동작합니다가.
        mock_response.json = MagicMock(return_value= {
            "user_count": 10,
            "trade_count": 50,
            "prediction_count": 100
        })
        # mock_http_get (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
        mock_http_get.return_value = mock_response

        await admin_stats(update, context)
        
        # mock_get_token (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다가.
        mock_get_token.assert_awaited_once_with(update.effective_chat.id)
        # update.message.reply_text (AsyncMock)가 한 번 호출되었는지 확인합니다가.
        update.message.reply_text.assert_awaited_once()
        sent_text = update.message.reply_text.call_args[0][0]
        assert "시스템 통계" in sent_text
        assert "사용자 수: 10명" in sent_text

@pytest.mark.asyncio
@patch('src.bot.handlers.admin.ADMIN_ID', "12345")
@patch('src.bot.handlers.admin.get_auth_token', new_callable=AsyncMock, return_value="fake_token")
@patch('src.common.utils.http_client.httpx.AsyncClient.post')
@patch('src.bot.handlers.admin.API_HOST', "stockeye-api") # Patch API_HOST
async def test_admin_update_historical_prices_specific_stock_success(mock_http_post, mock_get_auth_token, mock_update_context):
    update, context = mock_update_context
    chat_id = update.effective_chat.id

    update.message.text = '/update_historical_prices 005930 2023-01-01 2023-01-07'
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_http_post.return_value = mock_response

    await admin_update_historical_prices(update, context)

    mock_get_auth_token.assert_awaited_with(chat_id)
    context.bot.send_message.assert_any_await(
        chat_id=chat_id, text=f"⏳ 과거 일별 시세 갱신 요청 접수: 005930 (2023-01-01 ~ 2023-01-07). 작업이 완료되면 알림이 전송됩니다.", parse_mode='Markdown'
    )
    context.bot.send_message.assert_any_await(
        chat_id=chat_id, text="✅ 과거 일별 시세 갱신 작업이 성공적으로 트리거되었습니다.", parse_mode='Markdown'
    )
    mock_http_post.assert_awaited_with(
        f"http://stockeye-api:8000/api/v1/admin/update_historical_prices", # Updated URL
        headers={"Authorization": "Bearer fake_token"},
        json={
            "start_date": "2023-01-01",
            "end_date": "2023-01-07",
            "stock_identifier": "005930",
            "chat_id": chat_id
        },
        timeout=30
    )

@pytest.mark.asyncio
@patch('src.bot.handlers.admin.ADMIN_ID', "12345")
@patch('src.bot.handlers.admin.get_auth_token', new_callable=AsyncMock, return_value="fake_token")
@patch('src.common.utils.http_client.httpx.AsyncClient.post')
@patch('src.bot.handlers.admin.API_HOST', "stockeye-api") # Patch API_HOST
async def test_admin_update_historical_prices_all_stocks_success(mock_http_post, mock_get_auth_token, mock_update_context):
    update, context = mock_update_context
    chat_id = update.effective_chat.id

    update.message.text = '/update_historical_prices 2023-01-07'
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_http_post.return_value = mock_response

    await admin_update_historical_prices(update, context)

    mock_get_auth_token.assert_awaited_with(chat_id)
    context.bot.send_message.assert_any_await(
        chat_id=chat_id, text=f"⏳ 과거 일별 시세 갱신 요청 접수: 1990-01-01 ~ 2023-01-07. 작업이 완료되면 알림이 전송됩니다.", parse_mode='Markdown'
    )
    context.bot.send_message.assert_any_await(
        chat_id=chat_id, text="✅ 과거 일별 시세 갱신 작업이 성공적으로 트리거되었습니다.", parse_mode='Markdown'
    )
    mock_http_post.assert_awaited_with(
        f"http://stockeye-api:8000/api/v1/admin/update_historical_prices", # Updated URL
        headers={"Authorization": "Bearer fake_token"},
        json={
            "start_date": "1990-01-01", # Default start date
            "end_date": "2023-01-07",
            "stock_identifier": None,
            "chat_id": chat_id
        },
        timeout=30
    )

@pytest.mark.asyncio
@patch('src.bot.handlers.admin.ADMIN_ID', "12345")
@patch('src.bot.handlers.admin.get_auth_token', new_callable=AsyncMock, return_value="fake_token")
@patch('src.bot.decorators.get_retry_client') # Patch the get_retry_client function
@patch('src.bot.handlers.admin.API_HOST', "stockeye-api") # Patch API_HOST
async def test_admin_update_historical_prices_invalid_date_format(mock_get_retry_client, mock_get_auth_token, mock_update_context):
    update, context = mock_update_context
    chat_id = update.effective_chat.id

    # Create a mock client instance that will be returned by get_retry_client
    mock_client = AsyncMock()
    mock_get_retry_client.return_value = mock_client # This is the key change

    # Configure the mock client's __aenter__ and __aexit__ methods
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False # Indicate no exception handled

    # Mock the put method for telegram_register
    mock_put_response = AsyncMock()
    mock_put_response.status_code = 200
    mock_client.put.return_value = mock_put_response

    # Mock the post method for users/login and admin/update_historical_prices
    def mock_post_side_effect(url, *args, **kwargs):
        if "users/login" in url:
            mock_login_response = AsyncMock()
            mock_login_response.status_code = 200
            mock_login_response.json = AsyncMock(return_value={"access_token": "fake_login_token"})
            return mock_login_response
        elif "admin/update_historical_prices" in url:
            # This should not be called in this test
            raise AssertionError("admin/update_historical_prices should not be called for invalid date format")
        else:
            raise AssertionError(f"Unexpected POST call to {url}")

    mock_client.post.side_effect = mock_post_side_effect

    update.message.text = '/update_historical_prices invalid-date'

    await admin_update_historical_prices(update, context)

    context.bot.send_message.assert_any_await(
        chat_id=chat_id, text="❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해주세요."
    )
    assert mock_client.post.call_count == 1 # Only the users/login call
    mock_client.put.assert_awaited_once() # Check telegram_register call

@pytest.mark.asyncio
@patch('src.bot.handlers.admin.ADMIN_ID', "12345")
@patch('src.bot.handlers.admin.get_auth_token', new_callable=AsyncMock, return_value="fake_token")
@patch('src.common.utils.http_client.httpx.AsyncClient.put')
@patch('src.common.utils.http_client.httpx.AsyncClient.post')
@patch('src.bot.handlers.admin.API_HOST', "stockeye-api")
async def test_admin_update_historical_prices_api_error(mock_http_post, mock_http_put, mock_get_auth_token, mock_update_context):
    update, context = mock_update_context
    chat_id = update.effective_chat.id

    update.message.text = '/update_historical_prices 2023-01-07'

    # Mock for the put call in decorator
    mock_put_response = AsyncMock()
    mock_put_response.status_code = 200
    mock_http_put.return_value = mock_put_response

    # Mock for the login call in decorator
    mock_login_response = AsyncMock()
    mock_login_response.status_code = 200
    mock_login_response.json.return_value = {"access_token": "fake_token"}

    # Mock for the admin call
    mock_admin_response = AsyncMock()
    mock_admin_response.status_code = 400
    mock_admin_response.text = "API Error Detail"
    mock_admin_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "API Error Detail", request=MagicMock(), response=mock_admin_response
    )

    mock_http_post.side_effect = [
        mock_login_response,
        mock_admin_response
    ]

    await admin_update_historical_prices(update, context)

    context.bot.send_message.assert_any_await(
        chat_id=chat_id, text=f"⏳ 과거 일별 시세 갱신 요청 접수: 1990-01-01 ~ 2023-01-07. 작업이 완료되면 알림이 전송됩니다.", parse_mode='Markdown'
    )
    context.bot.send_message.assert_any_await(
        chat_id=chat_id, text=f"❌ 과거 일별 시세 갱신 실패: 400 API Error Detail"
    )
    assert mock_http_post.call_count == 2
    mock_http_put.assert_awaited_once()

@pytest.mark.asyncio
@patch('src.bot.handlers.admin.ADMIN_ID', "12345")
@patch('src.bot.handlers.admin.get_auth_token', new_callable=AsyncMock, return_value=None) # Simulate missing token
@patch('src.common.utils.http_client.httpx.AsyncClient.post')
@patch('src.bot.handlers.admin.API_HOST', "stockeye-api") # Patch API_HOST
async def test_admin_update_historical_prices_missing_token(mock_http_post, mock_get_auth_token, mock_update_context):
    update, context = mock_update_context
    chat_id = update.effective_chat.id

    update.message.text = '/update_historical_prices 2023-01-07'

    await admin_update_historical_prices(update, context)

    context.bot.send_message.assert_any_await(
        chat_id=chat_id, text="❌ 인증 토큰 발급에 실패했습니다."
    )
    mock_http_post.assert_not_awaited()