import logging
from telegram import Bot
import os
import asyncio

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def send_telegram_message(chat_id: int, text: str):
    logger.debug(f"Attempting to send message to chat_id: {chat_id}, text: {text[:50]}...") # 텍스트는 너무 길 수 있으므로 일부만 로깅
    try:
        message = await bot.send_message(chat_id=chat_id, text=text)
        if message:
            logger.info(f"Successfully sent message to chat_id: {chat_id}. Message ID: {message.message_id}")
        else:
            logger.warning(f"Message sent to chat_id: {chat_id}, but no message object was returned.")
    except Exception as e:
        logger.error(f"[텔레그램 알림 전송 실패] chat_id: {chat_id}, error: {e}", exc_info=True)