from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import requests
import os

def parse_alert_args(args):
    # 예시: /alert_add 삼성전자 70000 이상
    if len(args) != 3:
        return None, None, None
    symbol = args[0]
    try:
        price = float(args[1])
    except ValueError:
        return None, None, None
    cond = args[2]
    if cond in ["이상", "gte"]:
        condition = "gte"
    elif cond in ["이하", "lte"]:
        condition = "lte"
    else:
        return None, None, None
    return symbol, price, condition

async def alert_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    symbol, price, condition = parse_alert_args(args)
    if not symbol or not price or not condition:
        await update.message.reply_text("사용법: /alert_add [종목코드] [가격] [이상|이하]")
        return
    # API 연동
    api_url = os.getenv("API_URL", "http://api_service:8000")
    # 사용자 인증 및 telegram_id 등록 필요 (여기서는 간단히 user_id=1 가정)
    payload = {"symbol": symbol, "target_price": price, "condition": condition}
    # 실제 서비스에서는 JWT 토큰 인증 필요
    try:
        resp = requests.post(f"{api_url}/alerts/", json=payload, timeout=5)
        if resp.status_code == 200:
            await update.message.reply_text(f"가격 알림 등록 완료: {symbol} {price} {args[2]}")
        else:
            await update.message.reply_text(f"알림 등록 실패: {resp.text}")
    except Exception as e:
        await update.message.reply_text(f"API 요청 실패: {e}")

async def alert_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_url = os.getenv("API_URL", "http://api_service:8000")
    try:
        resp = requests.get(f"{api_url}/alerts/", timeout=5)
        if resp.status_code == 200:
            alerts = resp.json()
            if not alerts:
                await update.message.reply_text("등록된 가격 알림이 없습니다.")
                return
            msg = "[내 가격 알림 목록]\n"
            for a in alerts:
                cond = "이상" if a["condition"] == "gte" else "이하"
                msg += f"ID:{a['id']} {a['symbol']} {a['target_price']} {cond} {'(활성)' if a['is_active'] else '(비활성)'}\n"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"알림 목록 조회 실패: {resp.text}")
    except Exception as e:
        await update.message.reply_text(f"API 요청 실패: {e}")

async def alert_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("사용법: /alert_remove [알림ID]")
        return
    alert_id = context.args[0]
    api_url = os.getenv("API_URL", "http://api_service:8000")
    try:
        resp = requests.delete(f"{api_url}/alerts/{alert_id}", timeout=5)
        if resp.status_code == 200:
            await update.message.reply_text(f"알림 ID {alert_id} 삭제 완료")
        else:
            await update.message.reply_text(f"알림 삭제 실패: {resp.text}")
    except Exception as e:
        await update.message.reply_text(f"API 요청 실패: {e}")

def get_handler():
    return CommandHandler("alert_add", alert_add)

def get_list_handler():
    return CommandHandler("alert_list", alert_list)

def get_remove_handler():
    return CommandHandler("alert_remove", alert_remove) 