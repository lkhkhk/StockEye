from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import os

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    HELP_TEXT_USER = (
        "[StocksBot 도움말]\n"
        "\n"
        "- /register : 알림 수신 동의(ON, 텔레그램 알림 활성화)\n"
        "- /unregister : 알림 수신 동의 해제(OFF, 텔레그램 알림 비활성화)\n"
        "- /alert_add [종목코드 또는 종목명] : 종목 검색 후 가격/공시 알림 설정 (예: /alert_add 삼성전자)\n"
        "- /set_price [종목코드] [가격] [이상|이하] : 특정 종목 가격 알림 설정 (예: /set_price 005930 75000 이상)\n"
        "- /alert_list : 내 알림 목록 조회\n"
        "- /alert_remove [알림 번호] : 알림 삭제 (알림 목록에서 확인)\n"
        "\n"
        "예시: /register\n"
        "예시: /alert_add 삼성전자\n"
        "예시: /set_price 005930 75000 이상\n"
        "\n"
        "기타 명령어: /start, /help"
    )

    HELP_TEXT_ADMIN = HELP_TEXT_USER + "\n\n[관리자 전용 명령어 안내]\n- /admin : 관리자 명령어 전체 안내"

    user_id = str(update.effective_user.id)
    admin_id = os.getenv("TELEGRAM_ADMIN_ID", "")
    if user_id == admin_id:
        await update.message.reply_text(HELP_TEXT_ADMIN)
    else:
        await update.message.reply_text(HELP_TEXT_USER)

def get_help_handler():
    return CommandHandler("help", help_command) 