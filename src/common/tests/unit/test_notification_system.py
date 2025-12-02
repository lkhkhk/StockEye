"""
알림 시스템 고도화에 따른 단위 테스트

이 파일은 NotificationService, TelegramChannel, EmailChannel을 테스트합니다.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

from src.common.services.notify_service import NotificationService, send_telegram_message
from src.common.services.notification.telegram_channel import TelegramChannel
from src.common.services.notification.email_channel import EmailChannel

@pytest.fixture
def mock_telegram_bot():
    """Telegram Bot의 Mock 객체를 생성합니다."""
    with patch('src.common.services.notification.telegram_channel.Bot') as mock_bot_class:
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        yield mock_bot

@pytest.fixture
def notification_service():
    return NotificationService()

class TestTelegramChannel:
    """TelegramChannel 테스트"""

    @pytest.mark.asyncio
    async def test_send_success(self, mock_telegram_bot, monkeypatch):
        """텔레그램 메시지 전송 성공 테스트"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        channel = TelegramChannel()
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_telegram_bot.send_message.return_value = mock_message

        result = await channel.send(recipient="12345", message="Test Message")

        assert result is True
        mock_telegram_bot.send_message.assert_called_once_with(chat_id=12345, text="Test Message")

    @pytest.mark.asyncio
    async def test_send_no_token(self, mock_telegram_bot, monkeypatch):
        """토큰 없을 때 전송 실패 테스트"""
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        channel = TelegramChannel()

        result = await channel.send(recipient="12345", message="Test Message")

        assert result is False
        mock_telegram_bot.send_message.assert_not_called()

class TestEmailChannel:
    """EmailChannel 테스트"""

    @pytest.mark.asyncio
    @patch('src.common.config.email_config.email_config')
    async def test_send_success(self, mock_config):
        """이메일 전송 성공 테스트 (SMTP 미설정 시 False 반환)"""
        # EmailChannel은 SMTP가 설정되지 않으면 False를 반환
        mock_config.is_configured = False
        channel = EmailChannel()

        result = await channel.send(recipient="test@example.com", message="Test Message")

        # SMTP 미설정 시 False 반환
        assert result is False

class TestNotificationService:
    """NotificationService 테스트"""

    @pytest.mark.asyncio
    async def test_send_message_telegram(self, notification_service, mock_telegram_bot, monkeypatch):
        """서비스를 통한 텔레그램 전송 테스트"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_telegram_bot.send_message.return_value = mock_message

        result = await notification_service.send_message(recipient="12345", message="Test", channel_name="telegram")

        assert result is True
        mock_telegram_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.config.email_config.email_config')
    async def test_send_message_email(self, mock_config, notification_service):
        """이메일 채널로 메시지 전송 테스트"""
        # SMTP 미설정 시 False 반환
        mock_config.is_configured = False

        result = await notification_service.send_message(
            recipient="test@example.com",
            message="Test Email",
            channel_name="email"
        )

        # SMTP 미설정 시 False
        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_unknown_channel(self, notification_service):
        """알 수 없는 채널 전송 시도 테스트"""
        result = await notification_service.send_message(recipient="123", message="Test", channel_name="sms")

        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast(self, notification_service, mock_telegram_bot, monkeypatch):
        """브로드캐스트 테스트"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_telegram_bot.send_message.return_value = mock_message

        recipients = [
            {'id': '12345', 'channel': 'telegram'},
            {'id': 'test@example.com', 'channel': 'email'}
        ]

        await notification_service.broadcast(recipients, "Broadcast Message")

        mock_telegram_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_with_preferences(self, notification_service, mock_telegram_bot, monkeypatch):
        """설정 기반 브로드캐스트 테스트"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_telegram_bot.send_message.return_value = mock_message

        # EmailChannel Mocking (이미 NotificationService 생성 시 Mock이 아님, 여기서 patch 필요하거나 EmailChannel이 로그만 찍으므로 괜찮음)
        # 하지만 호출 여부 확인을 위해 spy 또는 mock 필요. 
        # 여기서는 NotificationService의 channels를 mock으로 교체하는 것이 더 확실함.
        
        mock_email_channel = AsyncMock()
        notification_service.channels['email'] = mock_email_channel

        recipients = [
            {
                'targets': {'telegram': '12345', 'email': 'test@example.com'},
                'preferences': {'telegram': True, 'email': False} # 이메일은 꺼짐
            },
            {
                'targets': {'telegram': '67890', 'email': 'user2@example.com'},
                'preferences': {'telegram': False, 'email': True} # 텔레그램은 꺼짐
            }
        ]

        await notification_service.broadcast(recipients, "Broadcast Message", subject="StockEye Notification")

        # 첫 번째 사용자: 텔레그램만 발송
        mock_telegram_bot.send_message.assert_called_once_with(chat_id=12345, text="Broadcast Message")
        
        # 두 번째 사용자: 이메일만 발송
        mock_email_channel.send.assert_called_once_with('user2@example.com', "Broadcast Message", subject="StockEye Notification") # subject는 기본값? send 호출 시 kwargs 확인 필요


class TestBackwardCompatibility:
    """하위 호환성 테스트"""

    @pytest.mark.asyncio
    async def test_send_telegram_message_function(self, mock_telegram_bot, monkeypatch):
        """기존 send_telegram_message 함수 테스트"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_telegram_bot.send_message.return_value = mock_message

        await send_telegram_message(chat_id=12345, text="Legacy Test")

        mock_telegram_bot.send_message.assert_called_once_with(chat_id=12345, text="Legacy Test")
