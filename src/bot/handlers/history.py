import os
import httpx
from telegram import Update
from telegram.ext import ContextTypes
from src.common.utils.http_client import get_retry_client
import logging

logger = logging.getLogger(__name__)

API_HOST = os.getenv("API_HOST", "localhost")
API_URL = f"http://{API_HOST}:8000"

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.debug(f"history_command called for user_id: {user_id}")
    try:
        logger.debug("Attempting to get retry client.")
        async with get_retry_client() as client:
            logger.debug(f"Client obtained. Making GET request to {API_URL}/prediction/history/{user_id}")
            response = await client.get(f"{API_URL}/prediction/history/{user_id}", timeout=10)
            logger.debug(f"Received response. Status code: {response.status_code}")
            response.raise_for_status()
            logger.debug("raise_for_status passed. Attempting to parse JSON.")
            data = response.json()
            logger.debug(f"JSON parsed successfully. Data keys: {data.keys()}")
        
        history = data.get("history", [])
        logger.debug(f"History data: {history}")
        if not history:
            await update.message.reply_text("예측 이력이 없습니다.")
            logger.debug("No history found. Sent 'no history' message.")
            return
        
        msg = "[예측 이력]\n"
        for rec in history:
            msg += f"{rec['created_at']} | {rec['symbol']} | {rec['prediction']}\n"
        await update.message.reply_text(msg)
        logger.debug("History message sent.")
        
    except httpx.RequestError as e:
        logger.error(f"HTTP Request Error in history_command: {e}", exc_info=True)
        await update.message.reply_text(f"서버 통신 중 오류가 발생했습니다: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in history_command: {e}", exc_info=True)
        await update.message.reply_text(f"예측 이력 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.") # Fixed typo
