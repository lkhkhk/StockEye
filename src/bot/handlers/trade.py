import os
import requests
from telegram import Update
from telegram.ext import ContextTypes
from src.common.http_client import session

API_URL = os.getenv("API_URL", "http://api_service:8000")

async def trade_simulate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 4:
        await update.message.reply_text("사용법: /trade_simulate [buy/sell] [종목코드] [가격] [수량] 예: /trade_simulate buy 005930 10000 10")
        return
    trade_type, symbol, price, quantity = context.args
    user_id = update.effective_user.id
    try:
        payload = {
            "user_id": user_id,
            "symbol": symbol,
            "trade_type": trade_type,
            "price": float(price),
            "quantity": int(quantity)
        }
        response = await session.post(f"{API_URL}/trade/simulate", json=payload, timeout=10)
        if response.ok:
            await update.message.reply_text(response.json().get("message", "모의 거래 기록 완료"))
        else:
            await update.message.reply_text(f"모의 거래 기록 실패: API 응답 코드 {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"모의 거래 기록 실패: {e}")

async def trade_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        response = await session.get(f"{API_URL}/trade/history/{user_id}", timeout=10)
        if response.ok:
            data = response.json()
            trades = data.get("trades", [])
            if not trades:
                await update.message.reply_text("모의 거래 기록이 없습니다.")
                return
            msg = "[모의 거래 이력]\n"
            for t in trades:
                msg += f"{t['trade_time']} | {t['trade_type']} | {t['symbol']} | {t['price']} | {t['quantity']}\n"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"모의 거래 이력 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: {response.status_code})")
    except Exception as e:
        await update.message.reply_text(f"모의 거래 이력 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.") 