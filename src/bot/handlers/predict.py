import os
import requests
from telegram import Update
from telegram.ext import ContextTypes
from src.common.http_client import session

API_HOST = os.getenv("API_HOST", "localhost")
API_URL = f"http://{API_HOST}:8000/api/v1"

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /predict [종목코드] 예: /predict 005930")
        return
    symbol = context.args[0]
    user_id = update.effective_user.id
    try:
        response = await session.post(f"{API_URL}/predict", json={"symbol": symbol, "telegram_id": user_id}, timeout=10)
        if response.ok:
            data = response.json()
            msg = f"[예측 결과] {symbol}: {data.get('prediction', 'N/A')}\n사유: {data.get('reason', '')}"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"주가 예측 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: {response.status_code})")
    except Exception as e:
        await update.message.reply_text(f"주가 예측 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")