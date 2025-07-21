import logging
from telegram import Bot
import os
import asyncio

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

def send_telegram_message(chat_id: int, text: str):
    logger.info(f"Attempting to send message to chat_id: {chat_id}")
    try:
        # 비동기 함수를 동기 코드에서 실행하기 위해 asyncio.run() 사용
        message = asyncio.run(bot.send_message(chat_id=chat_id, text=text))
        if message:
            logger.info(f"Successfully sent message to chat_id: {chat_id}. Message ID: {message.message_id}")
        else:
            logger.warning(f"Message sent to chat_id: {chat_id}, but no message object was returned.")
    except Exception as e:
        logger.error(f"[텔레그램 알림 전송 실패] chat_id: {chat_id}, error: {e}", exc_info=True) 