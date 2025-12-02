"""Unit tests for EmailChannel with SMTP functionality."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from src.common.services.notification.email_channel import EmailChannel


class TestEmailChannel:
    """EmailChannel 테스트"""
    
    @pytest.mark.asyncio
    @patch('src.common.services.notification.email_channel.aiosmtplib.send')
    @patch('src.common.config.email_config.email_config')
    async def test_send_email_success(self, mock_config, mock_smtp_send):
        """이메일 전송 성공 테스트"""
        # GIVEN
        mock_config.is_configured = True
        mock_config.smtp_host = "smtp.gmail.com"
        mock_config.smtp_port = 587
        mock_config.smtp_username = "test@example.com"
        mock_config.smtp_password = "password"
        mock_config.smtp_use_tls = True
        mock_config.sender_email = "noreply@stockeye.com"
        mock_config.sender_name = "StockEye"
        
        mock_smtp_send.return_value = None  # Successful send
        
        channel = EmailChannel()
        
        # WHEN
        result = await channel.send(
            recipient="user@example.com",
            message="Test message",
            subject="Test Subject"
        )
        
        # THEN
        assert result is True
        mock_smtp_send.assert_called_once()
        
        # Verify call arguments
        call_args = mock_smtp_send.call_args
        assert call_args.kwargs['hostname'] == "smtp.gmail.com"
        assert call_args.kwargs['port'] == 587
        assert call_args.kwargs['use_tls'] is False
        assert call_args.kwargs['start_tls'] is True
    
    @pytest.mark.asyncio
    @patch('src.common.config.email_config.email_config')
    async def test_send_email_smtp_not_configured(self, mock_config):
        """SMTP 미설정 시 테스트"""
        # GIVEN
        mock_config.is_configured = False
        
        channel = EmailChannel()
        
        # WHEN
        result = await channel.send(
            recipient="user@example.com",
            message="Test message"
        )
        
        # THEN
        assert result is False
    
    @pytest.mark.asyncio
    @patch('src.common.services.notification.email_channel.aiosmtplib.send')
    @patch('src.common.config.email_config.email_config')
    async def test_send_email_with_template(self, mock_config, mock_smtp_send):
        """템플릿을 사용한 이메일 전송 테스트"""
        # GIVEN
        mock_config.is_configured = True
        mock_config.smtp_host = "smtp.gmail.com"
        mock_config.smtp_port = 587
        mock_config.smtp_username = "test@example.com"
        mock_config.smtp_password = "password"
        mock_config.smtp_use_tls = True
        mock_config.sender_email = "noreply@stockeye.com"
        mock_config.sender_name = "StockEye"
        
        mock_smtp_send.return_value = None
        
        channel = EmailChannel()
        
        # WHEN
        result = await channel.send(
            recipient="user@example.com",
            message="Price alert triggered",
            subject="Price Alert",
            template="price_alert.html",
            template_vars={
                "symbol": "005930",
                "current_price": "70000",
                "target_price": "70000",
                "condition": "gte"
            }
        )
        
        # THEN
        assert result is True
        mock_smtp_send.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.common.services.notification.email_channel.aiosmtplib.send')
    @patch('src.common.config.email_config.email_config')
    async def test_send_email_smtp_error(self, mock_config, mock_smtp_send):
        """SMTP 에러 처리 테스트"""
        # GIVEN
        mock_config.is_configured = True
        mock_config.smtp_host = "smtp.gmail.com"
        mock_config.smtp_port = 587
        mock_config.smtp_username = "test@example.com"
        mock_config.smtp_password = "password"
        mock_config.smtp_use_tls = True
        mock_config.sender_email = "noreply@stockeye.com"
        mock_config.sender_name = "StockEye"
        
        mock_smtp_send.side_effect = Exception("SMTP connection failed")
        
        channel = EmailChannel()
        
        # WHEN
        result = await channel.send(
            recipient="user@example.com",
            message="Test message"
        )
        
        # THEN
        assert result is False
        mock_smtp_send.assert_called_once()
