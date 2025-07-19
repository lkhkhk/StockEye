import os
import requests
from telegram import Update
from telegram.ext import ContextTypes

API_URL = os.getenv("API_URL", "http://api_service:8000")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        response = requests.get(f"{API_URL}/prediction/history/{user_id}")
        response.raise_for_status()
        data = response.json()
        history = data.get("history", [])
        if not history:
            await update.message.reply_text("예측 이력이 없습니다.")
            return
        msg = "[예측 이력]\n"
        for rec in history:
            msg += f"{rec['created_at']} | {rec['symbol']} | {rec['prediction']}\n"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"예측 이력 조회 실패: {e}") 