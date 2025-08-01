from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import os

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    HELP_TEXT_USER = (
        "[StocksEye 봇 도움말]\n"
        "\n"
        "**계정 관리**\n"
        "- /register : 알림 수신 동의 (텔레그램 알림 활성화)\n"
        "- /unregister : 알림 수신 동의 해제 (텔레그램 알림 비활성화)\n"
        "\n"
        "**주식 정보 조회**\n"
        "- /symbols : 전체 주식 종목 목록 조회\n"
        "- /symbols_search [키워드] : 키워드로 주식 종목 검색 (예: /symbols_search 삼성)\n"
        "- /symbol_info [종목코드] : 특정 종목 상세 정보 조회 (예: /symbol_info 005930)\n"
        "\n"
        "**주가 예측**\n"
        "- /predict [종목코드] : 특정 종목의 주가 등락 예측 (예: /predict 005930)\n"
        "\n"
        "**관심 종목**\n"
        "- /watchlist_add [종목코드] : 관심 종목 추가 (예: /watchlist_add 005930)\n"
        "- /watchlist_remove [종목코드] : 관심 종목 삭제 (예: /watchlist_remove 005930)\n"
        "- /watchlist_get : 나의 관심 종목 목록 조회\n"
        "\n"
        "**가격 알림**\n"
        "- /alert_add [종목코드 또는 종목명] : 종목 검색 후 가격/공시 알림 설정 (예: /alert_add 삼성전자)\n"
        "- /set_price [종목코드] [가격] [이상|이하] : 특정 종목 가격 알림 설정 (예: /set_price 005930 75000 이상)\n"
        "- /alert_list : 내 알림 목록 조회\n"
        "- /alert_remove [알림 번호] : 알림 삭제 (알림 목록에서 확인)\n"
        "\n"
        "**모의 거래**\n"
        "- /trade_simulate [buy|sell] [종목코드] [수량] [가격] : 모의 거래 기록 (예: /trade_simulate buy 005930 10 75000)\n"
        "- /trade_history : 나의 모의 거래 내역 조회\n"
        "\n"
        "**기타**\n"
        "- /start : 봇 시작 메시지\n"
        "- /help : 이 도움말 메시지\n"
        "\n"
        "**자연어 질의 예시:**\n"
        "- \"삼성전자 얼마야?\"\n"
        "- \"005930 예측해줘\"\n"
        "- \"카카오 오를까?\"\n"
    )

    HELP_TEXT_ADMIN = HELP_TEXT_USER + "\n\n[관리자 전용]\n관리자 명령어는 /admin 을 입력하세요."

    user_id = str(update.effective_user.id)
    admin_id = os.getenv("TELEGRAM_ADMIN_ID", "")
    if user_id == admin_id:
        await update.message.reply_text(HELP_TEXT_ADMIN)
    else:
        await update.message.reply_text(HELP_TEXT_USER)

def get_help_handler():
    return CommandHandler("help", help_command) 