import os
import requests
from telegram import Update
from telegram.ext import ContextTypes

API_URL = os.getenv("API_URL", "http://api_service:8000")

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(f"{API_URL}/health")
        response.raise_for_status()
        data = response.json()
        await update.message.reply_text(f"서비스 상태: {data.get('status', 'unknown')}")
    except Exception as e:
        await update.message.reply_text(f"헬스체크 실패: {e}")

async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(f"{API_URL}/admin_stats")
        response.raise_for_status()
        data = response.json()
        msg = (
            f"[서비스 통계]\n"
            f"사용자 수: {data.get('user_count', 0)}\n"
            f"모의 거래 수: {data.get('trade_count', 0)}\n"
            f"예측 이력 수: {data.get('prediction_count', 0)}"
        )
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"통계 조회 실패: {e}") 