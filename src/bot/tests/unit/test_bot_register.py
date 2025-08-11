import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.handlers.register import register_command, unregister_command

@pytest.mark.asyncio
@patch('src.bot.handlers.register.get_retry_client')
async def test_register_command_success(mock_get_retry_client):
    """/register 명령어 성공 테스트"""
    # Given
    update = AsyncMock(spec=Update)
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.put.return_value = mock_response
    mock_get_retry_client.return_value.__aenter__.return_value = mock_client

    # When
    await register_command(update, context)

    # Then
    mock_client.put.assert_awaited_once_with(
        "/api/v1/users/telegram_register",
        json={"telegram_id": "12345", "is_active": True}
    )
    update.message.reply_text.assert_awaited_once_with("알림 등록이 완료되었습니다. 이제부터 주가 알림을 받을 수 있습니다.")

@pytest.mark.asyncio
@patch('src.bot.handlers.register.get_retry_client')
async def test_unregister_command_success(mock_get_retry_client):
    """/unregister 명령어 성공 테스트"""
    # Given
    update = AsyncMock(spec=Update)
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.put.return_value = mock_response
    mock_get_retry_client.return_value.__aenter__.return_value = mock_client

    # When
    await unregister_command(update, context)

    # Then
    mock_client.put.assert_awaited_once_with(
        "/api/v1/users/telegram_register",
        json={"telegram_id": "12345", "is_active": False}
    )
    update.message.reply_text.assert_awaited_once_with("알림을 비활성화했습니다. 더 이상 주가 알림을 받지 않습니다.")

@pytest.mark.asyncio
@patch('src.bot.handlers.register.get_retry_client')
async def test_register_command_api_error(mock_get_retry_client):
    """/register 명령어 API 오류 테스트"""
    # Given
    update = AsyncMock(spec=Update)
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 400
    mock_response.json.return_value = {"detail": "User already registered"}
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=mock_response
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.put.return_value = mock_response
    mock_get_retry_client.return_value.__aenter__.return_value = mock_client

    # When
    await register_command(update, context)

    # Then
    update.message.reply_text.assert_awaited_once_with("등록 중 오류가 발생했습니다: User already registered")