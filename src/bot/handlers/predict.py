import os
import requests
from telegram import Update
from telegram.ext import ContextTypes

API_URL = os.getenv("API_URL", "http://api_service:8000")

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /predict [종목코드] 예: /predict 005930")
        return
    symbol = context.args[0]
    try:
        response = requests.post(f"{API_URL}/predict", json={"symbol": symbol})
        response.raise_for_status()
        data = response.json()
        msg = f"[예측 결과] {symbol}: {data.get('prediction', 'N/A')}\n사유: {data.get('reason', '')}"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"예측 실패: {e}") 