import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.handlers.register import register_command, unregister_command

@pytest.mark.asyncio
@patch('src.bot.handlers.register.get_retry_client') # MOCK: get_retry_client 함수
async def test_register_command_success(mock_get_retry_client):
    """/register 명령어 성공 테스트"""
    # Given
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_chat.id = 12345
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    # MOCK: httpx.Response 객체
    # MagicMock: HTTP 응답 객체를 모의합니다. 동기적으로 동작합니다.
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    # raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
    mock_response.raise_for_status.return_value = None

    # MOCK: httpx.AsyncClient 객체
    # AsyncMock: httpx.AsyncClient 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    # mock_client.put (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_client.put.return_value = mock_response
    # mock_get_retry_client (AsyncMock) 호출 시 mock_client를 반환하도록 설정합니다.
    mock_get_retry_client.return_value.__aenter__.return_value = mock_client

    # When
    await register_command(update, context)

    # Then
    # mock_client.put (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    mock_client.put.assert_awaited_once_with(
        "/api/v1/users/telegram_register",
        json={"telegram_id": "12345", "is_active": True}
    )
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once_with("알림 등록이 완료되었습니다. 이제부터 주가 알림을 받을 수 있습니다.")

@pytest.mark.asyncio
@patch('src.bot.handlers.register.get_retry_client') # MOCK: get_retry_client 함수
async def test_unregister_command_success(mock_get_retry_client):
    """/unregister 명령어 성공 테스트"""
    # Given
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_chat.id = 12345
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    # MOCK: httpx.Response 객체
    # MagicMock: HTTP 응답 객체를 모의합니다. 동기적으로 동작합니다.
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    # raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
    mock_response.raise_for_status.return_value = None

    # MOCK: httpx.AsyncClient 객체
    # AsyncMock: httpx.AsyncClient 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    # mock_client.put (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_client.put.return_value = mock_response
    # mock_get_retry_client (AsyncMock) 호출 시 mock_client를 반환하도록 설정합니다.
    mock_get_retry_client.return_value.__aenter__.return_value = mock_client

    # When
    await unregister_command(update, context)

    # Then
    # mock_client.put (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    mock_client.put.assert_awaited_once_with(
        "/api/v1/users/telegram_register",
        json={"telegram_id": "12345", "is_active": False}
    )
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once_with("알림을 비활성화했습니다. 더 이상 주가 알림을 받지 않습니다.")

@pytest.mark.asyncio
@patch('src.bot.handlers.register.get_retry_client') # MOCK: get_retry_client 함수
async def test_register_command_api_error(mock_get_retry_client):
    """/register 명령어 API 오류 테스트"""
    # Given
    # MOCK: telegram.Update 객체
    # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
    update = AsyncMock(spec=Update)
    update.effective_chat.id = 12345
    # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
    update.message.reply_text = AsyncMock()
    # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
    # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    # MOCK: httpx.Response 객체
    # MagicMock: HTTP 응답 객체를 모의합니다. 동기적으로 동작합니다.
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 400
    # json() 메서드는 비동기적으로 호출될 수 있으므로, 반환값을 직접 설정합니다.
    mock_response.json.return_value = {"detail": "User already registered"}
    # raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=mock_response
    )

    # MOCK: httpx.AsyncClient 객체
    # AsyncMock: httpx.AsyncClient 객체를 모의합니다. 비동기적으로 동작합니다.
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    # mock_client.put (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
    mock_client.put.return_value = mock_response
    # mock_get_retry_client (AsyncMock) 호출 시 mock_client를 반환하도록 설정합니다.
    mock_get_retry_client.return_value.__aenter__.return_value = mock_client

    # When
    await register_command(update, context)

    # Then
    # update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
    update.message.reply_text.assert_awaited_once_with("등록 중 오류가 발생했습니다: User already registered")