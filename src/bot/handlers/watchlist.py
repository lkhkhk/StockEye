import os
import requests
from telegram import Update
from telegram.ext import ContextTypes
from src.common.http_client import session

API_HOST = os.getenv("API_HOST", "localhost")
API_URL = f"http://{API_HOST}:8000"

async def watchlist_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /watchlist_add [종목코드] 예: /watchlist_add 005930")
        return
    symbol = context.args[0]
    user_id = update.effective_user.id
    try:
        response = await session.post(f"{API_URL}/watchlist/add", json={"user_id": user_id, "symbol": symbol}, timeout=10)
        if response.status_code < 400:
            await update.message.reply_text(response.json().get("message", "관심종목 추가 완료"))
        else:
            await update.message.reply_text(f"관심종목 추가 실패: API 응답 코드 {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"관심종목 추가 실패: {e}")

async def watchlist_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /watchlist_remove [종목코드] 예: /watchlist_remove 005930")
        return
    symbol = context.args[0]
    user_id = update.effective_user.id
    try:
        response = await session.post(f"{API_URL}/watchlist/remove", json={"user_id": user_id, "symbol": symbol}, timeout=10)
        if response.status_code < 400:
            await update.message.reply_text(response.json().get("message", "관심종목 제거 완료"))
        else:
            await update.message.reply_text(f"관심종목 제거 실패: API 응답 코드 {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"관심종목 제거 실패: {e}")

async def watchlist_get_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        response = await session.get(f"{API_URL}/watchlist/get/{user_id}", timeout=10)
        if response.status_code < 400:
            data = response.json()
            watchlist = data.get("watchlist", [])
            if not watchlist:
                await update.message.reply_text("관심종목이 없습니다.")
                return
            msg = "[관심종목 목록]\n" + "\n".join(watchlist)
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"관심종목 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: {response.status_code})")
    except Exception as e:
        await update.message.reply_text(f"관심종목 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.") 