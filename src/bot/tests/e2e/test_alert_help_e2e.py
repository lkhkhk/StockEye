import pytest
from unittest.mock import AsyncMock

from telegram import Update, Message
from telegram.ext import ContextTypes

from src.bot.handlers.alert import alert_command

@pytest.mark.asyncio
async def test_alert_command_sends_help_message_e2e():
    """
    E2E test to verify that the /alert command without arguments
    returns the correct, updated help message.
    """
    # 1. Setup Mocks
    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)

    mock_message = AsyncMock(spec=Message)
    mock_message.reply_text = AsyncMock()
    update.message = mock_message
    
    # Simulate a user calling /alert with no arguments
    context.args = []

    # 2. Execute the handler
    await alert_command(update, context)

    # 3. Verify the response
    update.message.reply_text.assert_called_once()
    sent_text = update.message.reply_text.call_args.kwargs['text']

    # The expected new help message
    expected_text = (
        "🔔 **알림 관리**\n\n"
        "다양한 조건으로 주식 알림을 설정하고 관리합니다.\n\n"
        "**명령어 목록:**\n"
        "- `/alert add [종목명]`: 특정 종목에 대한 가격 또는 공시 알림을 새로 추가합니다.\n"
        "  (예: `/alert add 삼성전자`)\n"
        "- `/alert list`: 내가 등록한 모든 알림의 목록과 활성 상태를 확인합니다.\n"
        "- `/alert delete [번호]`: 목록의 특정 알림을 삭제합니다.\n"
        "- `/alert pause [번호]`: 특정 알림을 일시적으로 중지합니다.\n"
        "- `/alert resume [번호]`: 중지된 알림을 다시 시작합니다."
    )

    assert sent_text == expected_text
