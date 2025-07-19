import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from dotenv import load_dotenv
from handlers.history import history_command
from handlers.help import help_command
from handlers.admin import health_command, admin_stats_command
from handlers.predict import predict_command
from handlers.watchlist import watchlist_add_command, watchlist_remove_command, watchlist_get_command
from handlers.trade import trade_simulate_command, trade_history_command
from handlers.symbols import symbols_command, symbols_search_command, symbol_info_command
from handlers.natural import natural_message_handler

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

HELP_MSG = (
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
    "/health - 서비스 헬스체크\n"
    "/admin_stats - 전체 통계 조회\n"
    "\n메시지로 종목코드만 입력해도 예측 결과를 받을 수 있습니다."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("안녕하세요! 텔레그램 봇이 정상 동작합니다.\n\n" + HELP_MSG)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"메시지 수신: {update.message.text}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("health", health_command))
    app.add_handler(CommandHandler("admin_stats", admin_stats_command))
    app.add_handler(CommandHandler("predict", predict_command))
    app.add_handler(CommandHandler("watchlist_add", watchlist_add_command))
    app.add_handler(CommandHandler("watchlist_remove", watchlist_remove_command))
    app.add_handler(CommandHandler("watchlist_get", watchlist_get_command))
    app.add_handler(CommandHandler("trade_simulate", trade_simulate_command))
    app.add_handler(CommandHandler("trade_history", trade_history_command))
    app.add_handler(CommandHandler("symbols", symbols_command))
    app.add_handler(CommandHandler("symbols_search", symbols_search_command))
    app.add_handler(CommandHandler("symbol_info", symbol_info_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, natural_message_handler))
    print("텔레그램 봇이 시작되었습니다. 메시지를 기다리는 중...")
    app.run_polling() 