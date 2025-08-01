from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import os

ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "")

START_TEXT_USER = (
    "안녕하세요! StocksEye 봇입니다.\n"
    "주식 정보 조회, 예측, 알림, 모의 거래 등 다양한 기능을 제공합니다.\n"
    "\n"
    "자세한 사용법과 전체 명령어 목록은 /help 를 입력해주세요."
)

START_TEXT_ADMIN = START_TEXT_USER + "\n\n[관리자 전용]\n관리자 명령어는 /admin 을 입력하세요."

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id == ADMIN_ID:
        await update.message.reply_text(START_TEXT_ADMIN)
    else:
        await update.message.reply_text(START_TEXT_USER)

def get_start_handler():
    return CommandHandler("start", start_command) 