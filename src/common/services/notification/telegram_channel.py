import logging
import os
from telegram import Bot
from .channel import NotificationChannel

logger = logging.getLogger(__name__)

class TelegramChannel(NotificationChannel):
    """텔레그램 알림 채널 구현체입니다."""

    async def send(self, recipient: str, message: str, **kwargs) -> bool:
        """
        텔레그램으로 메시지를 전송합니다.

        Args:
            recipient (str): 텔레그램 Chat ID (문자열로 전달되지만 내부적으로 정수로 변환 시도)
            message (str): 전송할 메시지
            **kwargs: 추가 옵션

        Returns:
            bool: 전송 성공 여부
        """
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN is not set. Skipping message sending.")
            return False

        if not message or not message.strip():
            logger.warning(f"Attempted to send an empty or whitespace-only message to chat_id: {recipient}. Skipping.")
            return False

        try:
            chat_id = int(recipient)
        except ValueError:
            logger.error(f"Invalid recipient for Telegram channel: {recipient}. Must be convertible to int.")
            return False

        bot = Bot(token=token)
        
        logger.debug(f"Attempting to send message to chat_id: {chat_id}, text: {message[:50]}...")
        try:
            sent_message = await bot.send_message(chat_id=chat_id, text=message)
            if sent_message:
                logger.info(f"Successfully sent message to chat_id: {chat_id}. Message ID: {sent_message.message_id}")
                return True
            else:
                logger.warning(f"Message sent to chat_id: {chat_id}, but no message object was returned.")
                return False
        except Exception as e:
            logger.error(f"[텔레그램 알림 전송 실패] chat_id: {chat_id}, error: {e}", exc_info=True)
            return False
