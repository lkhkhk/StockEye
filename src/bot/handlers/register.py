from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import requests
import os

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_url = os.getenv("API_URL", "http://api_service:8000")
    telegram_id = str(update.effective_chat.id)
    # 알림 수신 동의 (is_active=True)
    payload = {"telegram_id": telegram_id, "is_active": True}
    # 인증 없이 telegram_id만 등록 (실제 서비스에서는 인증 필요)
    try:
        resp = requests.put(f"{api_url}/users/telegram_register", json=payload, timeout=5)
        if resp.status_code == 200:
            await update.message.reply_text("알림 수신 동의가 완료되었습니다. (텔레그램 알림 ON)")
        else:
            await update.message.reply_text(f"알림 동의 실패: {resp.text}")
    except Exception as e:
        await update.message.reply_text(f"API 요청 실패: {e}")

async def unregister(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_url = os.getenv("API_URL", "http://api_service:8000")
    telegram_id = str(update.effective_chat.id)
    # 알림 수신 해제 (is_active=False)
    payload = {"telegram_id": telegram_id, "is_active": False}
    try:
        resp = requests.put(f"{api_url}/users/telegram_register", json=payload, timeout=5)
        if resp.status_code == 200:
            await update.message.reply_text("알림 수신 동의가 해제되었습니다. (텔레그램 알림 OFF)")
        else:
            await update.message.reply_text(f"알림 해제 실패: {resp.text}")
    except Exception as e:
        await update.message.reply_text(f"API 요청 실패: {e}")

def get_register_handler():
    return CommandHandler("register", register)

def get_unregister_handler():
    return CommandHandler("unregister", unregister) 