# 이 파일은 src.common.services.notify_service 모듈의 단위 테스트를 포함합니다.
#
# 텔레그램 API와의 실제 네트워크 통신을 방지하기 위해, 모든 테스트는
# `notify_service` 모듈 내의 `bot` 객체를 모의(mock)하여 진행합니다.
# 이를 통해 텔레그램 봇 토큰 없이도 메시지 발송 로직의 정확성을 검증할 수 있습니다.

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.common.services.notify_service import send_telegram_message

@pytest.mark.asyncio
@patch('src.common.services.notify_service.bot', new_callable=MagicMock)
async def test_send_telegram_message_success(mock_bot):
    """텔레그램 메시지가 성공적으로 전송되는 경우를 테스트합니다."""
    # 1. Setup
    chat_id = 12345
    message_text = "Test message"
    
    # MOCK: mock_bot.send_message
    # bot.send_message가 비동기 함수이므로 AsyncMock으로 설정합니다.
    mock_bot.send_message = AsyncMock()
    
    # MOCK: Message 객체
    # send_message 호출 시 반환될 Message 객체를 모의합니다.
    # MagicMock: Message 객체는 동기적으로 동작하므로 MagicMock을 사용합니다.
    mock_message = MagicMock()
    mock_message.message_id = 999
    mock_bot.send_message.return_value = mock_message

    # 2. Execute
    await send_telegram_message(chat_id, message_text)

    # 3. Assert
    # send_message (AsyncMock)가 올바른 인자와 함께 한 번 호출되었는지 확인합니다.
    mock_bot.send_message.assert_awaited_once_with(chat_id=chat_id, text=message_text)


@pytest.mark.asyncio
@patch('src.common.services.notify_service.bot', new_callable=MagicMock)
async def test_send_telegram_message_failure(mock_bot):
    """텔레그램 API 에러 발생 시, 함수가 예외를 잘 처리하는지 테스트합니다."""
    # 1. Setup
    chat_id = 12345
    message_text = "Test message"
    
    # MOCK: mock_bot.send_message
    # send_message (AsyncMock) 호출 시 예외를 발생시키도록 설정합니다.
    mock_bot.send_message = AsyncMock(side_effect=Exception("Telegram API Error"))

    # 2. Execute & Assert
    # 함수 내부에서 예외를 로깅하고 처리하므로, 함수 호출 자체가 예외를 발생시키지 않아야 합니다.
    await send_telegram_message(chat_id, message_text)

    # 3. Assert
    # 예외 상황에서도 send_message (AsyncMock)가 호출되었는지 확인합니다.
    mock_bot.send_message.assert_awaited_once_with(chat_id=chat_id, text=message_text)


@pytest.mark.asyncio
@patch('src.common.services.notify_service.bot', None)
async def test_send_telegram_message_bot_not_configured():
    """TELEGRAM_BOT_TOKEN이 설정되지 않아 bot 객체가 None일 경우를 테스트합니다."""
    # 1. Setup
    chat_id = 12345
    message_text = "Test message"

    # 2. Execute & Assert
    # bot이 None일 경우, 함수는 경고를 로깅하고 조용히 종료되어야 합니다.
    # 별도의 assert가 필요 없으며, 함수가 오류 없이 실행되면 테스트는 통과입니다.
    await send_telegram_message(chat_id, message_text)


@pytest.mark.asyncio
@patch('src.common.services.notify_service.bot', new_callable=MagicMock)
async def test_send_telegram_message_empty_message(mock_bot):
    """빈 메시지를 전송하려 할 때 함수가 적절히 동작하는지 테스트합니다."""
    # 1. Setup
    chat_id = 12345
    message_text = ""
    
    # MOCK: mock_bot.send_message
    # bot.send_message가 비동기 함수이므로 AsyncMock으로 설정합니다.
    mock_bot.send_message = AsyncMock()

    # 2. Execute
    await send_telegram_message(chat_id, message_text)

    # 3. Assert
    # 빈 메시지이므로 send_message (AsyncMock)가 호출되지 않아야 합니다.
    mock_bot.send_message.assert_not_awaited()