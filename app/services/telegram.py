import logging
from typing import Optional, List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from ..core.config import settings
from ..core.database import db
from ..models.user import User
from ..models.stock import Stock, UserStock

logger = logging.getLogger(__name__)

# 상태 정의
REGISTER, ADDING_STOCK = range(2)

class TelegramBotService:
    def __init__(self):
        self.app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
        self._setup_handlers()

    def _setup_handlers(self):
        """텔레그램 봇 핸들러 설정"""
        # 기본 명령어
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        
        # 사용자 등록 대화
        register_handler = ConversationHandler(
            entry_points=[CommandHandler("register", self.register)],
            states={
                REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_register)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.app.add_handler(register_handler)
        
        # 주식 관리 대화
        add_stock_handler = ConversationHandler(
            entry_points=[CommandHandler("add", self.add_stock_command)],
            states={
                ADDING_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_add_stock)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.app.add_handler(add_stock_handler)
        
        # 주식 삭제 명령어 (ConversationHandler 제거, CommandHandler 직접 추가)
        self.app.add_handler(CommandHandler("remove", self.remove_stock_command))
        
        # 기본 명령어
        self.app.add_handler(CommandHandler("list", self.list_stocks_command))
        
        # 콜백 쿼리 핸들러 (주식 삭제 버튼 처리)
        self.app.add_handler(CallbackQueryHandler(self.button_callback))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어 처리"""
        user = update.effective_user
        message = (
            f"안녕하세요 {user.first_name}님, StockEye(주시봇)에 오신 것을 환영합니다! 👁️\n\n"
            "이 봇은 주식 공시정보를 실시간으로 모니터링하여 알려드립니다.\n\n"
            "사용 가능한 명령어:\n"
            "/register - 사용자 등록\n"
            "/add - 모니터링할 주식 추가\n"
            "/remove - 모니터링 중인 주식 삭제\n"
            "/list - 현재 모니터링 중인 주식 목록 보기\n"
            "/help - 도움말 보기"
        )
        await update.message.reply_text(message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """도움말 명령어 처리"""
        message = (
            "🔍 StockEye(주시봇) 사용 방법:\n\n"
            "1. /register 명령으로 먼저 사용자 등록을 해주세요.\n"
            "2. /add 명령으로 모니터링할 주식을 추가하세요. (예: '005930 삼성전자' 형식)\n"
            "3. /remove 명령으로 더 이상 모니터링하지 않을 주식을 삭제할 수 있습니다.\n"
            "4. /list 명령으로 현재 모니터링 중인 주식 목록을 확인할 수 있습니다.\n\n"
            "새로운 공시가 등록되면 자동으로 알림을 보내드립니다!"
        )
        await update.message.reply_text(message)

    async def register(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """사용자 등록 시작"""
        user = update.effective_user
        
        async with db.pool.acquire() as conn:
            existing_user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1",
                str(user.id)
            )
            
            if existing_user:
                await update.message.reply_text(
                    f"{user.first_name}님은 이미 등록되어 있습니다!"
                )
                return ConversationHandler.END
            
            await update.message.reply_text(
                f"안녕하세요 {user.first_name}님! 서비스 이용을 위해 간단한 인증이 필요합니다.\n"
                "인증 키를 입력해주세요. (기본값: 'stockeye')\n"
                "취소하려면 /cancel 을 입력하세요."
            )
            return REGISTER

    async def process_register(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """사용자 등록 처리"""
        user = update.effective_user
        auth_key = update.message.text

        if auth_key != "stockeye":
            await update.message.reply_text(
                "❌ 인증 키가 올바르지 않습니다.\n"
                "다시 시도하려면 /register 를 입력하세요."
            )
            return ConversationHandler.END

        try:
            new_user = User(
                user_id=str(user.id),
                username=user.username,
                first_name=user.first_name
            )
            
            async with db.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO users (user_id, username, first_name)
                    VALUES ($1, $2, $3)
                    """,
                    new_user.user_id,
                    new_user.username,
                    new_user.first_name
                )
            
            await update.message.reply_text(
                f"✅ {user.first_name}님 환영합니다!\n"
                "이제 종목을 추가하고 공시를 모니터링할 수 있습니다.\n"
                "종목 추가: /add\n"
                "종목 삭제: /remove\n"
                "종목 목록: /list"
            )
            return ConversationHandler.END

        except Exception as e:
            logger.error(f"Error during registration: {e}")
            await update.message.reply_text(
                "❌ 등록 중 오류가 발생했습니다. 나중에 다시 시도해주세요."
            )
            return ConversationHandler.END

    async def add_stock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """주식 추가 명령어 처리"""
        user_id = str(update.effective_user.id)
        
        async with db.pool.acquire() as conn:
            # 등록된 사용자인지 확인
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1",
                user_id
            )
            
            if not user:
                await update.message.reply_text(
                    "❌ 사용자 등록이 필요합니다!\n"
                    "먼저 /register 명령으로 사용자 등록을 해주세요."
                )
                return ConversationHandler.END
            
            # 현재 모니터링 중인 주식 수 확인
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM user_stocks WHERE user_id = $1",
                user_id
            )
            
            await update.message.reply_text(
                "📈 주식 추가를 시작합니다!\n\n"
                f"현재 모니터링 중인 주식: {count}개\n\n"
                "✏️ 추가할 주식을 '종목코드 종목명' 형식으로 입력해주세요.\n"
                "예시: 005930 삼성전자\n\n"
                "❌ 취소하려면 /cancel 을 입력하세요."
            )
            return ADDING_STOCK

    async def process_add_stock(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """주식 추가 처리"""
        user_id = str(update.effective_user.id)
        text = update.message.text.strip()
        
        try:
            parts = text.split()
            if len(parts) < 2:
                await update.message.reply_text(
                    "❌ 입력 형식이 올바르지 않습니다.\n"
                    "올바른 형식: 종목코드 종목명\n"
                    "예시: 005930 삼성전자"
                )
                return ADDING_STOCK
            
            stock_code = parts[0]
            stock_name = ' '.join(parts[1:])
            
            # 종목코드 형식 검증
            try:
                stock = Stock(code=stock_code, name=stock_name)
            except ValueError:
                await update.message.reply_text(
                    "❌ 종목코드 형식이 올바르지 않습니다.\n"
                    "종목코드는 6자리 숫자여야 합니다."
                )
                return ADDING_STOCK
            
            async with db.pool.acquire() as conn:
                # 이미 등록된 종목인지 확인
                existing = await conn.fetchrow(
                    """
                    SELECT s.name FROM user_stocks us
                    JOIN stocks s ON us.stock_code = s.code
                    WHERE us.user_id = $1 AND us.stock_code = $2
                    """,
                    user_id, stock_code
                )
                
                if existing:
                    await update.message.reply_text(
                        f"⚠️ {existing['name']}({stock_code})는 이미 모니터링 중입니다."
                    )
                    return ConversationHandler.END
                
                # 트랜잭션 시작
                async with conn.transaction():
                    # 주식 정보 저장
                    await conn.execute(
                        """
                        INSERT INTO stocks (code, name)
                        VALUES ($1, $2)
                        ON CONFLICT (code) DO UPDATE
                        SET name = EXCLUDED.name
                        """,
                        stock.code, stock.name
                    )
                    
                    # 사용자-주식 연결
                    await conn.execute(
                        """
                        INSERT INTO user_stocks (user_id, stock_code)
                        VALUES ($1, $2)
                        """,
                        user_id, stock.code
                    )
                
                # 현재 모니터링 중인 총 주식 수 확인
                total_stocks = await conn.fetchval(
                    "SELECT COUNT(*) FROM user_stocks WHERE user_id = $1",
                    user_id
                )
                
                success_message = (
                    f"✅ {stock.name}({stock.code}) 모니터링을 시작합니다!\n\n"
                    f"📊 현재 모니터링 중인 주식: {total_stocks}개\n\n"
                    "➕ 추가 등록을 원하시면 다시 /add 명령을 사용해주세요.\n"
                    "📋 전체 목록 확인은 /list 명령을 사용해주세요."
                )
                await update.message.reply_text(success_message)
                
        except Exception as e:
            logger.error(f"주식 추가 중 오류 발생: {e}")
            await update.message.reply_text(
                "❌ 주식 추가 중 오류가 발생했습니다.\n"
                "다시 시도하거나 다른 종목을 입력해주세요."
            )
            return ADDING_STOCK
        
        return ConversationHandler.END

    async def list_stocks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """모니터링 중인 주식 목록 보기"""
        user_id = str(update.effective_user.id)
        
        async with db.pool.acquire() as conn:
            # 등록된 사용자인지 확인
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1",
                user_id
            )
            
            if not user:
                await update.message.reply_text(
                    "❌ 먼저 /register 명령으로 사용자 등록을 해주세요."
                )
                return
            
            # 사용자의 주식 목록 조회
            rows = await conn.fetch(
                """
                SELECT s.code, s.name
                FROM user_stocks us
                JOIN stocks s ON us.stock_code = s.code
                WHERE us.user_id = $1
                ORDER BY s.name
                """,
                user_id
            )
            
            if not rows:
                await update.message.reply_text(
                    "현재 모니터링 중인 주식이 없습니다.\n"
                    "/add 명령으로 추가해보세요."
                )
                return
            
            message = "📋 현재 모니터링 중인 주식 목록:\n\n"
            for idx, row in enumerate(rows, 1):
                message += f"{idx}. {row['name']} ({row['code']})\n"
            
            message += "\n새로운 주식 추가는 /add, 삭제는 /remove 명령을 사용하세요."
            await update.message.reply_text(message)

    async def remove_stock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """주식 삭제 명령어 처리"""
        user_id = str(update.effective_user.id)
        
        async with db.pool.acquire() as conn:
            # 등록된 사용자인지 확인
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1",
                user_id
            )
            
            if not user:
                await update.message.reply_text(
                    "❌ 먼저 /register 명령으로 사용자 등록을 해주세요."
                )
                return
            
            # 사용자의 주식 목록 조회
            stocks = await conn.fetch(
                """
                SELECT s.code, s.name
                FROM user_stocks us
                JOIN stocks s ON us.stock_code = s.code
                WHERE us.user_id = $1
                ORDER BY s.name
                """,
                user_id
            )
            
            if not stocks:
                await update.message.reply_text(
                    "현재 모니터링 중인 주식이 없습니다."
                )
                return
            
            # 인라인 키보드 생성
            keyboard = []
            for i in range(0, len(stocks), 2):
                row = []
                for stock in stocks[i:i+2]:
                    button = InlineKeyboardButton(
                        f"{stock['name']} ({stock['code']})",
                        callback_data=f"remove_{stock['code']}"
                    )
                    row.append(button)
                keyboard.append(row)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "삭제할 주식을 선택하세요:",
                reply_markup=reply_markup
            )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """인라인 버튼 콜백 처리 (주식 삭제 로직 포함)"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = str(query.from_user.id)
        
        if data.startswith("remove_"):
            stock_code = data.split("_")[1]
            
            async with db.pool.acquire() as conn:
                # 주식 정보 조회 (삭제 확인 메시지용)
                stock = await conn.fetchrow(
                    "SELECT name FROM stocks WHERE code = $1",
                    stock_code
                )
                
                if not stock:
                    try:
                        await query.edit_message_text(
                            "❌ 오류: 삭제하려는 종목을 찾을 수 없습니다."
                        )
                    except Exception as e:
                        logger.warning(f"Error editing message after failed stock find: {e}")
                    return
                
                try:
                    # 주식 삭제 실행
                    await conn.execute(
                        "DELETE FROM user_stocks WHERE user_id = $1 AND stock_code = $2",
                        user_id, stock_code
                    )

                    await query.edit_message_text(
                        f"✅ {stock['name']}({stock_code}) 모니터링이 중지되었습니다."
                    )
                    logger.info(f"User {user_id} removed stock {stock_code}")
                except Exception as e:
                    logger.error(f"Error removing stock {stock_code} for user {user_id}: {e}")
                    try:
                        await query.edit_message_text(
                            "❌ 오류: 주식 삭제 중 문제가 발생했습니다."
                        )
                    except Exception as edit_e:
                         logger.warning(f"Error editing message after removal failure: {edit_e}")

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """대화 취소"""
        await update.message.reply_text("❌ 작업이 취소되었습니다.")
        return ConversationHandler.END

    async def start(self):
        """봇 시작"""
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        logger.info("텔레그램 봇이 시작되었습니다.")

    async def stop(self):
        """봇 종료"""
        if self.app.updater:
            await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
        logger.info("텔레그램 봇이 종료되었습니다.")

telegram_bot = TelegramBotService() 