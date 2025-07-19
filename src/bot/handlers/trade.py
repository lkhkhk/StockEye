import os
import requests
from telegram import Update
from telegram.ext import ContextTypes

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
        response = requests.post(f"{API_URL}/trade/simulate", json=payload)
        response.raise_for_status()
        await update.message.reply_text(response.json().get("message", "모의 거래 기록 완료"))
    except Exception as e:
        await update.message.reply_text(f"모의 거래 기록 실패: {e}")

async def trade_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        response = requests.get(f"{API_URL}/trade/history/{user_id}")
        response.raise_for_status()
        data = response.json()
        trades = data.get("trades", [])
        if not trades:
            await update.message.reply_text("모의 거래 기록이 없습니다.")
            return
        msg = "[모의 거래 이력]\n"
        for t in trades:
            msg += f"{t['trade_time']} | {t['trade_type']} | {t['symbol']} | {t['price']} | {t['quantity']}\n"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"모의 거래 이력 조회 실패: {e}") 