import pytest
import requests
from unittest.mock import AsyncMock, patch, Mock
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.handlers.register import register, unregister

@pytest.mark.asyncio
async def test_register_success():
    update = AsyncMock(spec=Update)
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = AsyncMock(status_code=200)

    with patch('src.bot.handlers.register.session.put', return_value=mock_response) as mock_put:
        await register(update, context)

        mock_put.assert_called_once_with(
            "http://stockeye-api:8000/users/telegram_register",
            json={"telegram_id": "12345", "is_active": True},
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "알림 수신 동의가 완료되었습니다. (텔레그램 알림 ON)"
        )

@pytest.mark.asyncio
async def test_register_api_error():
    update = AsyncMock(spec=Update)
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = AsyncMock(status_code=500, text="Internal Server Error")

    with patch('src.bot.handlers.register.session.put', return_value=mock_response) as mock_put:
        await register(update, context)

        mock_put.assert_called_once_with(
            "http://stockeye-api:8000/users/telegram_register",
            json={"telegram_id": "12345", "is_active": True},
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "알림 동의 실패: Internal Server Error"
        )

@pytest.mark.asyncio
async def test_unregister_success():
    update = AsyncMock(spec=Update)
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = AsyncMock(status_code=200)

    with patch('src.bot.handlers.register.session.put', return_value=mock_response) as mock_put:
        await unregister(update, context)

        mock_put.assert_called_once_with(
            "http://stockeye-api:8000/users/telegram_register",
            json={"telegram_id": "12345", "is_active": False},
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "알림 수신 동의가 해제되었습니다. (텔레그램 알림 OFF)"
        )

@pytest.mark.asyncio
async def test_unregister_api_error():
    update = AsyncMock(spec=Update)
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_response = AsyncMock(status_code=500, text="Internal Server Error")

    with patch('src.bot.handlers.register.session.put', return_value=mock_response) as mock_put:
        await unregister(update, context)

        mock_put.assert_called_once_with(
            "http://stockeye-api:8000/users/telegram_register",
            json={"telegram_id": "12345", "is_active": False},
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "알림 해제 실패: Internal Server Error"
        )
