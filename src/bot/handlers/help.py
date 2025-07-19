from telegram import Update
from telegram.ext import ContextTypes

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "사용 가능한 명령어:\n"
        "/start - 봇 시작\n"
        "/help - 명령어/사용법 안내\n"
        "/predict [종목코드] - 특정 종목 예측 (예: /predict 005930)\n"
        "/history - 예측 이력 조회\n"
        "/watchlist_add [종목코드] - 관심 종목 추가 (예: /watchlist_add 005930)\n"
        "/watchlist_remove [종목코드] - 관심 종목 제거 (예: /watchlist_remove 005930)\n"
        "/watchlist_get - 관심 종목 목록 조회\n"
        "/trade_simulate [buy/sell] [종목코드] [가격] [수량] - 모의 거래 기록 (예: /trade_simulate buy 005930 10000 10)\n"
        "/trade_history - 모의 거래 기록 조회\n"
        "\n메시지로 종목코드만 입력해도 예측 결과를 받을 수 있습니다."
    )
    await update.message.reply_text(msg) 