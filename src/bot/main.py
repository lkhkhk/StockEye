import logging
import os
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters

from src.bot.handlers import (
    start,
    help,
    register,
    predict,
    watchlist,
    alert,
    history,
    symbols,
    trade,
    admin,
    natural
)

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 환경 변수
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")
        return

    # Application 객체 생성
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 핸들러 등록
    # Special handler with high priority to catch worker completion messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, predict.rerun_prediction_on_completion), group=-1)

    application.add_handler(CommandHandler("start", start.start_command))
    application.add_handler(CommandHandler("help", help.help_command))
    application.add_handler(CommandHandler("register", register.register_command))
    
    # Predict handlers (without the rerun handler)
    for handler in predict.get_predict_handlers():
        application.add_handler(handler)

    # Watchlist handlers
    application.add_handler(CommandHandler("watchlist_add", watchlist.watchlist_add_command))
    application.add_handler(CommandHandler("watchlist_remove", watchlist.watchlist_remove_command))
    application.add_handler(CommandHandler("watchlist", watchlist.watchlist_get_command))

    # Alert handlers
    application.add_handler(alert.get_alert_handler())

    # History handlers
    application.add_handler(CommandHandler("history", history.history_command))

    # Symbols handlers
    for handler in symbols.get_symbols_handlers():
        application.add_handler(handler)

    # Trade handlers
    application.add_handler(CommandHandler("trade_simulate", trade.trade_simulate_command))
    application.add_handler(CommandHandler("trade_history", trade.trade_history_command))

    # Admin handlers
    application.add_handler(admin.get_admin_handler())
    application.add_handler(admin.get_admin_callback_handler()) # Added this line
    application.add_handler(admin.get_health_handler())
    application.add_handler(admin.get_admin_show_schedules_handler())
    application.add_handler(admin.get_admin_trigger_job_handler())
    application.add_handler(admin.get_trigger_job_callback_handler())
    application.add_handler(admin.get_admin_stats_handler())
    application.add_handler(admin.get_test_notify_handler())
    application.add_handler(admin.get_admin_update_historical_prices_handler())

    # Natural language processing handler (in default group 0)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, natural.natural_message_handler), group=0)

    # 봇 시작
    logger.info("Starting bot in polling mode...")
    application.run_polling()

if __name__ == '__main__':
    main()
