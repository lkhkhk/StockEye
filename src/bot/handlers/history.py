import os
import requests
from telegram import Update
from telegram.ext import ContextTypes
from src.common.http_client import session

API_HOST = os.getenv("API_HOST", "localhost")
API_URL = f"http://{API_HOST}:8000"

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        response = session.get(f"{API_URL}/prediction/history/{user_id}", timeout=10)
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
        await update.message.reply_text(f"예측 이력 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.") 