"""Email notification channel implementation with SMTP support."""
import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

from .channel import NotificationChannel

logger = logging.getLogger(__name__)


class EmailChannel(NotificationChannel):
    """이메일 알림 채널 구현체 (Gmail SMTP 지원)"""
    
    def __init__(self):
        # Setup Jinja2 template environment
        template_dir = Path(__file__).parent.parent.parent / "templates" / "email"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        logger.info(f"EmailChannel initialized with template directory: {template_dir}")
    
    async def send(self, recipient: str, message: str, **kwargs) -> bool:
        """
        이메일로 메시지를 전송합니다.
        
        Args:
            recipient (str): 이메일 주소
            message (str): 전송할 메시지 본문
            **kwargs: 추가 옵션
                - subject (str): 이메일 제목 (기본값: "StockEye Notification")
                - template (str): 템플릿 이름 (기본값: "notification.html")
                - template_vars (dict): 템플릿 변수
        
        Returns:
            bool: 전송 성공 여부
        """
        # Import here to avoid circular dependency
        from src.common.config.email_config import email_config
        
        if not email_config.is_configured:
            logger.warning("SMTP not configured. Skipping email send. Set SMTP_USERNAME and SMTP_PASSWORD environment variables.")
            return False
        
        try:
            subject = kwargs.get("subject", "StockEye Notification")
            template_name = kwargs.get("template", "notification.html")
            template_vars = kwargs.get("template_vars", {})
            
            # Render HTML email
            template = self.env.get_template(template_name)
            html_content = template.render(
                subject=subject,
                message=message,
                **template_vars
            )
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{email_config.sender_name} <{email_config.sender_email}>"
            msg['To'] = recipient
            
            # Add plain text and HTML parts
            msg.attach(MIMEText(message, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Determine TLS settings
            use_tls = email_config.smtp_use_tls
            start_tls = False
            
            # Port 587 typically uses STARTTLS, not implicit TLS
            if email_config.smtp_port == 587:
                use_tls = False
                start_tls = True
            
            # Send via SMTP
            await aiosmtplib.send(
                msg,
                hostname=email_config.smtp_host,
                port=email_config.smtp_port,
                username=email_config.smtp_username,
                password=email_config.smtp_password,
                use_tls=use_tls,
                start_tls=start_tls,
            )
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}", exc_info=True)
            return False
