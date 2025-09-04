import os
import logging
from logging.handlers import RotatingFileHandler
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackQueryHandler,
    ConversationHandler
)
from dotenv import load_dotenv

# 핸들러 함수 직접 임포트
from handlers.history import history_command
from handlers.help import help_command
from handlers.admin import (
    health_command, admin_stats, admin_show_schedules, 
    admin_trigger_job, trigger_job_callback,
    test_notify_command, admin_command
)
from handlers.predict import predict_command
from handlers.watchlist import watchlist_add_command, watchlist_remove_command, watchlist_get_command
from handlers.symbols import (
    symbols_command, symbol_info_command, 
    symbols_pagination_callback, symbol_info_callback, symbols_search_pagination_callback
)
from handlers.natural import natural_message_handler
from handlers.alert import (
    alert_command,
    ask_alert_type,
    add_disclosure_alert,
    ask_price_condition,
    set_price_alert,
    cancel_alert_conversation,
    ASK_ALERT_TYPE,
    ASK_PRICE_CONDITION,
    ASK_PRICE_TARGET,
)
from handlers.register import register_command, unregister_command
from handlers.start import start_command

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
APP_ENV = os.getenv("APP_ENV", "development")

# 로깅 설정
LOGGING_LEVEL = logging.DEBUG if APP_ENV != "production" else logging.INFO
LOG_DIR = "/logs"
LOG_FILE = os.path.join(LOG_DIR, "bot.log")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=LOGGING_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Conversation Handler for alerts
    alert_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("alert", alert_command)],
        states={
            ASK_ALERT_TYPE: [
                CallbackQueryHandler(ask_alert_type, pattern="^alert_add_select_")
            ],
            ASK_PRICE_CONDITION: [
                CallbackQueryHandler(add_disclosure_alert, pattern="^alert_add_type_disclosure$"),
                CallbackQueryHandler(ask_price_condition, pattern="^alert_add_type_price$"),
            ],
            ASK_PRICE_TARGET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_price_alert)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_alert_conversation)],
    )

    app.add_handler(alert_conv_handler)

    # Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("register", register_command))
    app.add_handler(CommandHandler("unregister", unregister_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("predict", predict_command))
    app.add_handler(CommandHandler("watchlist_add", watchlist_add_command))
    app.add_handler(CommandHandler("watchlist_remove", watchlist_remove_command))
    app.add_handler(CommandHandler("watchlist_get", watchlist_get_command))
    app.add_handler(CommandHandler("symbols", symbols_command))
    app.add_handler(CommandHandler("symbol_info", symbol_info_command))
    app.add_handler(CommandHandler("test_notify", test_notify_command))

    # Admin Command Handlers
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("health", health_command))
    app.add_handler(CommandHandler("admin_stats", admin_stats))
    app.add_handler(CommandHandler("show_schedules", admin_show_schedules))
    app.add_handler(CommandHandler("trigger_job", admin_trigger_job))

    # Other Callback Query Handlers
    app.add_handler(CallbackQueryHandler(symbols_pagination_callback, pattern="^symbols_page_"))
    app.add_handler(CallbackQueryHandler(symbol_info_callback, pattern="^symbol_info_"))
    app.add_handler(CallbackQueryHandler(symbols_search_pagination_callback, pattern="^symbols_search_page_"))
    app.add_handler(CallbackQueryHandler(trigger_job_callback, pattern="^trigger_job_"))

    # Message Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, natural_message_handler))

    # Webhook / Polling
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
