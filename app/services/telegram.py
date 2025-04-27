import logging
import asyncio
from functools import wraps
import html
from typing import Optional, List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
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

# --- 관리자 확인 데코레이터 --- #
def admin_only(func):
    @wraps(func)
    async def wrapped(self, update: object, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # 수정: update 타입 확인 및 getattr 사용 (self 다음 update가 실제 Update 객체)
        if not isinstance(update, Update):
            logger.error(f"관리자 데코레이터 오류: 'update' 객체 타입 아님 ({type(update)}).")
            return

        user = getattr(update, 'effective_user', None) # getattr 로 안전하게 접근

        if not user:
            logger.warning("관리자 기능 사용 시도: 유효한 사용자를 찾을 수 없음 (effective_user 없음).")
            # 사용자에게 오류 알림 시도
            if hasattr(update, 'message') and update.message:
                try:
                    await update.message.reply_text("오류: 요청 사용자 정보를 확인할 수 없습니다.")
                except Exception as e:
                    logger.error(f"사용자 정보 없음 오류 메시지 전송 실패: {e}")
            return

        user_id = str(user.id)
        if not settings.ADMIN_ID:
            logger.warning("관리자 기능 사용 시도: ADMIN_ID가 .env 파일에 설정되지 않았습니다.")
            return

        if user_id != settings.ADMIN_ID:
            logger.warning(f"관리자 기능 무단 사용 시도: User ID {user_id}")
            if hasattr(update, 'message') and update.message:
                try:
                    await update.message.reply_text("❌ 이 명령어를 사용할 권한이 없습니다.")
                except Exception as e:
                    logger.error(f"권한 없음 메시지 전송 실패: {e}")
            return

        # 권한이 있으면 원래 함수 실행 (self 인자 전달)
        return await func(self, update, context, *args, **kwargs)
    return wrapped
# -------------------------- #

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

        # --- 관리자 명령어 핸들러 등록 --- #
        self.app.add_handler(CommandHandler("admin", self.admin_command))
        self.app.add_handler(CommandHandler("list_users", self.list_users_command))
        self.app.add_handler(CommandHandler("delete_user", self.delete_user_command))
        self.app.add_handler(CommandHandler("broadcast", self.broadcast_command))
        # ------------------------------- #

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
        # 관리자라면 관리 명령어 안내 추가
        if settings.ADMIN_ID and str(user.id) == settings.ADMIN_ID:
             message += "\n\n🔑 관리자 메뉴: /admin"

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
            
            safe_first_name = html.escape(user.first_name or "")
            await update.message.reply_text(
                f"✅ {safe_first_name}님 환영합니다!\n"
                "이제 종목을 추가하고 공시를 모니터링할 수 있습니다.\n"
                "종목 추가: /add\n"
                "종목 삭제: /remove\n"
                "종목 목록: /list",
                parse_mode='HTML'
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
                
                safe_stock_name = html.escape(stock.name)
                success_message = (
                    f"✅ {safe_stock_name}(<code>{stock.code}</code>) 모니터링을 시작합니다!\n\n"
                    f"📊 현재 모니터링 중인 주식: {total_stocks}개\n\n"
                    "➕ 추가 등록을 원하시면 다시 /add 명령을 사용해주세요.\n"
                    "📋 전체 목록 확인은 /list 명령을 사용해주세요."
                )
                await update.message.reply_text(success_message, parse_mode='HTML')
                
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
            
            message_lines = []
            for idx, row in enumerate(rows, 1):
                safe_name = html.escape(row['name'] or "")
                message_lines.append(f"{idx}. {safe_name} (<code>{row['code']}</code>)")

            message_header = "📋 현재 모니터링 중인 주식 목록:\n\n"
            message_footer = "\n\n새로운 주식 추가는 /add, 삭제는 /remove 명령을 사용하세요."
            full_message = message_header + "\n".join(message_lines) + message_footer

            await update.message.reply_text(full_message, parse_mode='HTML')

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
                    safe_name = html.escape(stock['name'] or "")
                    button_text = f"{safe_name} ({stock['code']})"
                    button = InlineKeyboardButton(
                        button_text,
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

                    safe_stock_name = html.escape(stock['name'] or "")
                    await query.edit_message_text(
                        f"✅ {safe_stock_name}(<code>{stock_code}</code>) 모니터링이 중지되었습니다.",
                        parse_mode='HTML'
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

    # --- 관리자 명령어 핸들러 구현 --- #
    @admin_only
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """관리자 명령어 목록 표시"""
        message = (
            "🔑 관리자 명령어 목록:\n\n"
            "/list_users - 모든 등록 사용자 목록 보기\n"
            "/delete_user <user_id> - 특정 사용자 삭제\n"
            "/broadcast <message> - 모든 사용자에게 메시지 발송"
        )
        await update.message.reply_text(message)

    @admin_only
    async def list_users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """등록된 모든 사용자 목록 보기"""
        async with db.pool.acquire() as conn:
            users = await conn.fetch("SELECT user_id, username, first_name, registered_at FROM users ORDER BY registered_at")

        if not users:
            await update.message.reply_text("등록된 사용자가 없습니다.")
            return

        message_lines = []
        for i, user in enumerate(users, 1):
            safe_first_name = html.escape(user['first_name'] or "")
            safe_username = f"(@{html.escape(user['username'])})" if user['username'] else ""
            reg_time = user['registered_at'].strftime('%Y-%m-%d %H:%M') if user['registered_at'] else 'N/A'
            message_lines.append(f"{i}. {safe_first_name} {safe_username} (ID: <code>{user['user_id']}</code>) - 등록: {reg_time}")

        # 메시지가 너무 길 경우 분할 전송
        MAX_LENGTH = constants.MessageLimit.MAX_TEXT_LENGTH
        if len("\n".join(message_lines)) + 50 > MAX_LENGTH: # 헤더 길이 고려
            parts = []
            current_part_lines = []
            current_length = 0
            for line in message_lines:
                line_len = len(line) + 1 # 줄바꿈 문자 포함
                if current_length + line_len > MAX_LENGTH - 50: # 헤더 길이 고려
                    parts.append("\n".join(current_part_lines))
                    current_part_lines = [line]
                    current_length = line_len
                else:
                    current_part_lines.append(line)
                    current_length += line_len
            if current_part_lines:
                 parts.append("\n".join(current_part_lines))

            total_parts = len(parts)
            for i, part_content in enumerate(parts):
                header = f"👥 총 {len(users)}명의 등록된 사용자 ({i+1}/{total_parts}) :\n\n"
                full_part = header + part_content
                await update.message.reply_text(full_part, parse_mode='HTML')
                await asyncio.sleep(0.5) # 메시지 전송 간격
        else:
             full_message = f"👥 총 {len(users)}명의 등록된 사용자:\n\n" + "\n".join(message_lines)
             await update.message.reply_text(full_message, parse_mode='HTML')

    @admin_only
    async def delete_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """특정 사용자 삭제"""
        if not context.args:
            await update.message.reply_text("사용법: /delete_user <삭제할_사용자_ID>")
            return

        user_id_to_delete = context.args[0]

        # 자기 자신 삭제 방지
        if user_id_to_delete == str(update.effective_user.id):
             await update.message.reply_text("❌ 자기 자신을 삭제할 수 없습니다.")
             return

        async with db.pool.acquire() as conn:
            # 사용자 존재 확인
            user = await conn.fetchrow("SELECT user_id, first_name FROM users WHERE user_id = $1", user_id_to_delete)
            if not user:
                await update.message.reply_text(f"❌ 사용자 ID `{user_id_to_delete}`를 찾을 수 없습니다.")
                return

            try:
                # 트랜잭션 사용: user_stocks 먼저 삭제 후 users 삭제
                async with conn.transaction():
                    # 사용자 관련 주식 모니터링 정보 삭제
                    await conn.execute("DELETE FROM user_stocks WHERE user_id = $1", user_id_to_delete)
                    # 사용자 삭제
                    await conn.execute("DELETE FROM users WHERE user_id = $1", user_id_to_delete)

                safe_first_name = html.escape(user['first_name'] or "")
                await update.message.reply_text(
                     f"✅ 사용자 {safe_first_name}(<code>{user_id_to_delete}</code>) 및 관련 데이터가 성공적으로 삭제되었습니다.",
                     parse_mode='HTML'
                )
                logger.info(f"Admin {update.effective_user.id} deleted user {user_id_to_delete}")

            except Exception as e:
                logger.error(f"Error deleting user {user_id_to_delete}: {e}")
                await update.message.reply_text("❌ 사용자 삭제 중 오류가 발생했습니다.")

    @admin_only
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """모든 사용자에게 메시지 발송"""
        admin_chat_id = update.effective_chat.id # 관리자 채팅 ID 가져오기

        if not context.args:
            # 수정: reply_text -> send_message
            await context.application.bot.send_message(
                chat_id=admin_chat_id,
                text="사용법: /broadcast <보낼 메시지 내용>"
            )
            return

        message_text = " ".join(context.args)
        broadcast_message = f"📢 [관리자 공지]\n\n{message_text}"

        async with db.pool.acquire() as conn:
            users = await conn.fetch("SELECT user_id FROM users")

        if not users:
            # 수정: reply_text -> send_message
            await context.application.bot.send_message(
                chat_id=admin_chat_id,
                text="메시지를 보낼 사용자가 없습니다."
            )
            return

        send_tasks = []
        user_ids = [user['user_id'] for user in users]
        for user_id in user_ids:
            send_tasks.append(
                context.application.bot.send_message(
                    chat_id=user_id,
                    text=broadcast_message
                )
            )

        # 수정: reply_text -> send_message
        await context.application.bot.send_message(
            chat_id=admin_chat_id,
            text=f"📣 총 {len(user_ids)}명에게 메시지 발송을 시작합니다..."
        )

        results = await asyncio.gather(*send_tasks, return_exceptions=True)

        success_count = 0
        fail_count = 0
        failed_users = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                fail_count += 1
                failed_users.append(user_ids[i])
                logger.warning(f"Broadcast failed for user {user_ids[i]}: {result}")
            else:
                success_count += 1

        result_message = f"""✅ 메시지 발송 완료!
- 성공: {success_count}명
- 실패: {fail_count}명"""
        if failed_users:
            result_message += f"\n- 실패 사용자 ID (일부): {', '.join(failed_users[:5])}{'...' if len(failed_users)>5 else ''}"

        # 수정: reply_text -> send_message
        await context.application.bot.send_message(
            chat_id=admin_chat_id,
            text=result_message
        )
    # ------------------------------- #

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