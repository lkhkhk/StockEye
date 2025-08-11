import pytest
from unittest.mock import AsyncMock, patch
from src.bot.handlers.start import start_command, START_TEXT_USER, START_TEXT_ADMIN

@pytest.mark.asyncio
async def test_start_command_for_regular_user():
    """
    일반 사용자가 /start 명령어를 입력했을 때, 일반 사용자용 메시지를 수신하는지 테스트합니다.
    """
    # Given
    update = AsyncMock()
    context = AsyncMock()
    update.effective_user.id = 12345
    
    # When
    with patch('src.bot.handlers.start.ADMIN_ID', "99999"): # 관리자 ID를 다른 값으로 설정
        await start_command(update, context)

    # Then
    update.message.reply_text.assert_awaited_once_with(START_TEXT_USER)


@pytest.mark.asyncio
async def test_start_command_for_admin_user():
    """
    관리자 사용자가 /start 명령어를 입력했을 때, 관리자용 메시지를 수신하는지 테스트합니다.
    """
    # Given
    update = AsyncMock()
    context = AsyncMock()
    admin_id = "12345"
    update.effective_user.id = int(admin_id)

    # When
    with patch('src.bot.handlers.start.ADMIN_ID', admin_id): # 관리자 ID를 테스트 ID와 동일하게 설정
        await start_command(update, context)

    # Then
    update.message.reply_text.assert_awaited_once_with(START_TEXT_ADMIN)
