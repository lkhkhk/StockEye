"""Email configuration module for SMTP settings."""
import os
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class EmailConfig(BaseModel):
    """Email configuration settings for SMTP"""
    
    smtp_host: str = Field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.gmail.com"))
    smtp_port: int = Field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_username: str = Field(default_factory=lambda: os.getenv("SMTP_USERNAME", ""))
    smtp_password: str = Field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_use_tls: bool = Field(default_factory=lambda: os.getenv("SMTP_USE_TLS", "true").lower() == "true")
    sender_email: str = Field(default_factory=lambda: os.getenv("SENDER_EMAIL", "noreply@stockeye.com"))
    sender_name: str = Field(default_factory=lambda: os.getenv("SENDER_NAME", "StockEye"))
    
    @property
    def is_configured(self) -> bool:
        """Check if SMTP is properly configured"""
        return bool(self.smtp_username and self.smtp_password)


# Singleton instance
email_config = EmailConfig()
