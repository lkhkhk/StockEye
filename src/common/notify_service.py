import logging
from telegram import Bot
import os

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

def send_telegram_message(chat_id: int, text: str):
    try:
        bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.error(f"[텔레그램 알림 전송 실패] {e}", exc_info=True) 