import os
import logging
import re
from logging.handlers import RotatingFileHandler
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram import Update
from dotenv import load_dotenv
from handlers.history import history_command
from handlers.help import help_command
from handlers.admin import health_command, admin_stats, admin_update_master, admin_update_price, admin_show_schedules, admin_trigger_job, admin_update_disclosure, update_disclosure_callback, test_notify_command
from handlers.predict import predict_command
from handlers.watchlist import watchlist_add_command, watchlist_remove_command, watchlist_get_command
from handlers.symbols import symbols_command, symbols_search_command, symbol_info_command, symbols_pagination_callback, symbol_info_callback, symbols_search_pagination_callback
from handlers.natural import natural_message_handler
from bot.handlers.alert import get_handler, get_list_handler, get_remove_handler, alert_button_callback, set_price_alert, alert_set_repeat_callback
from bot.handlers.register import get_register_handler, get_unregister_handler
from bot.handlers.start import get_start_handler
from bot.handlers.help import get_help_handler
from bot.handlers.admin import get_admin_handler

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
    "/symbols - 전체 종목 목록 조회\n"
    "/symbols_search [키워드] - 종목 검색\n"
    "/symbol_info [종목코드] - 종목 상세 정보\n"
    "\n**관리자 명령어:**\n"
    "/health - 서비스 헬스체크\n"
    "/admin_stats - 전체 통계 조회\n"
    "/update_master - 종목마스터 갱신\n"
    "/update_price - 일별시세 갱신\n"
    "/show_schedules - 스케줄러 상태 조회\n"
    "/trigger_job [job_id] - 특정 잡 수동 실행\n"
    "\n메시지로 종목코드만 입력해도 예측 결과를 받을 수 있습니다."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("안녕하세요! 텔레그램 봇이 정상 동작합니다.\n\n" + HELP_MSG)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"메시지 수신: {update.message.text}")

APP_ENV = os.getenv("APP_ENV", "development")

# 로깅 레벨 설정
if APP_ENV == "production":
    LOGGING_LEVEL = logging.INFO
elif APP_ENV == "test":
    LOGGING_LEVEL = logging.DEBUG # 테스트 환경에서도 상세 로그를 위해 DEBUG 유지
else: # development
    LOGGING_LEVEL = logging.DEBUG

# 로깅 설정 (stdout + 파일)
LOG_DIR = "/logs"
LOG_FILE = os.path.join(LOG_DIR, "bot.log")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=LOGGING_LEVEL, # APP_ENV에 따라 동적으로 설정
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(get_start_handler()) # /start
    app.add_handler(get_help_handler())  # /help
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("health", health_command))
    app.add_handler(CommandHandler("admin_stats", admin_stats))
    app.add_handler(CommandHandler("update_master", admin_update_master))
    app.add_handler(CommandHandler("update_price", admin_update_price))
    app.add_handler(CommandHandler("show_schedules", admin_show_schedules))
    app.add_handler(CommandHandler("trigger_job", admin_trigger_job))
    app.add_handler(CommandHandler("predict", predict_command))
    app.add_handler(CommandHandler("watchlist_add", watchlist_add_command))
    app.add_handler(CommandHandler("watchlist_remove", watchlist_remove_command))
    app.add_handler(CommandHandler("watchlist_get", watchlist_get_command))
    # app.add_handler(CommandHandler("trade_simulate", trade_simulate_command))
    # app.add_handler(CommandHandler("trade_history", trade_history_command))
    app.add_handler(CommandHandler("symbols", symbols_command))
    
    app.add_handler(CommandHandler("symbol_info", symbol_info_command))
    app.add_handler(CallbackQueryHandler(symbols_pagination_callback, pattern="^symbols_page_"))
    app.add_handler(CallbackQueryHandler(symbol_info_callback, pattern="^symbol_info_"))
    app.add_handler(CallbackQueryHandler(symbols_search_pagination_callback, pattern="^symbols_search_page_"))
    app.add_handler(CommandHandler("update_disclosure", admin_update_disclosure))
    app.add_handler(CallbackQueryHandler(update_disclosure_callback, pattern="^update_disclosure_"))
    app.add_handler(CallbackQueryHandler(alert_button_callback, pattern="^alert_"))
    app.add_handler(CallbackQueryHandler(alert_set_repeat_callback, pattern="^alert_set_repeat_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, natural_message_handler))
    app.add_handler(CommandHandler("alert_add", get_handler().callback))
    app.add_handler(CommandHandler("alert_list", get_list_handler().callback))
    app.add_handler(CommandHandler("alert_remove", get_remove_handler().callback))
    app.add_handler(CommandHandler("set_price", set_price_alert)) # 새로운 핸들러 등록
    app.add_handler(get_register_handler()) # /register
    app.add_handler(get_unregister_handler()) # /unregister
    app.add_handler(get_admin_handler()) # /admin
    app.add_handler(CommandHandler("test_notify", test_notify_command))
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", "8001"))

    if WEBHOOK_URL:
        logger.info(f"Starting bot in webhook mode on port {PORT}...")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook",
            webhook_url=WEBHOOK_URL
        )
    else:
        logger.info("Starting bot in polling mode...")
        app.run_polling()