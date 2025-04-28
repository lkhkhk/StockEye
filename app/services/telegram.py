import logging
import asyncio
from functools import wraps
import html
from typing import Optional, List, Dict
from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, constants
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
from ..services.dart_updater import update_corp_codes_from_dart
from . import disclosure # telegram.py와 같은 디렉토리에 있으므로 '.' 사용

logger = logging.getLogger(__name__)

# 상태 정의
REGISTER, ADDING_STOCK, AWAITING_ADD_CONFIRMATION = range(3)

# --- 관리자 확인 데코레이터 --- #
def admin_only(func):
    @wraps(func)
    async def wrapped(self, update: object, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = None
        user_id = None
        chat_id_for_reply = None # Needed for sending replies if user is not admin

        # Determine the user and chat_id based on the type of 'update'
        if isinstance(update, Update):
            if update.effective_user:
                user = update.effective_user
            if update.effective_chat: # Use effective_chat for chat_id
                chat_id_for_reply = update.effective_chat.id
        elif isinstance(update, CallbackQuery):
            if update.from_user:
                user = update.from_user
            if update.message and update.message.chat: # CallbackQuery has message attribute
                chat_id_for_reply = update.message.chat.id
        else:
            # Log error if it's neither Update nor CallbackQuery
            logger.error(f"관리자 데코레이터 오류: 처리할 수 없는 객체 타입 ({type(update)}).")
            return # Cannot proceed without user info

        # Check if user object was found
        if not user:
            logger.warning("관리자 기능 사용 시도: 유효한 사용자를 찾을 수 없음.")
            if chat_id_for_reply: # Try to notify if possible
                 try:
                      await context.bot.send_message(chat_id=chat_id_for_reply, text="오류: 요청 사용자 정보를 확인할 수 없습니다.")
                 except Exception as e:
                      logger.error(f"관리자 데코레이터 사용자 없음 오류 메시지 전송 실패: {e}")
            return

        user_id = str(user.id) # Now we are sure 'user' is not None

        # Check if ADMIN_ID is configured
        if not settings.ADMIN_ID:
            logger.warning("관리자 기능 사용 시도: ADMIN_ID가 .env 파일에 설정되지 않았습니다.")
            if chat_id_for_reply:
                try:
                    await context.bot.send_message(chat_id=chat_id_for_reply, text="오류: 봇 관리자 설정이 필요합니다.")
                except Exception as e:
                    logger.error(f"ADMIN_ID 누락 오류 메시지 전송 실패: {e}")
            return

        # Check if the user is the admin
        if user_id != settings.ADMIN_ID:
            logger.warning(f"관리자 기능 무단 사용 시도: User ID {user_id}")
            if chat_id_for_reply:
                try:
                    # Use send_message as reply_text might not work for CallbackQuery context directly
                    await context.bot.send_message(chat_id=chat_id_for_reply, text="❌ 이 기능을 사용할 권한이 없습니다.")
                except Exception as e:
                    logger.error(f"권한 없음 메시지 전송 실패 (user_id={user_id}): {e}")
            return

        # If all checks pass, execute the original function
        return await func(self, update, context, *args, **kwargs)
    return wrapped
# -------------------------- #

# --- 추가: 페이징 처리 상수 ---
USERS_PAGE_SIZE = 10
STOCKS_PAGE_SIZE = 15 # 전체 종목 목록 페이지 크기
# --------------------------

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
                ADDING_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_add_stock)],
                AWAITING_ADD_CONFIRMATION: [
                    CallbackQueryHandler(self.process_add_confirmation, pattern='^confirm_add_')
                ]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.app.add_handler(add_stock_handler)
        
        # 주식 삭제 명령어 (ConversationHandler 제거, CommandHandler 직접 추가)
        self.app.add_handler(CommandHandler("remove", self.remove_stock_command))
        
        # 기본 명령어
        self.app.add_handler(CommandHandler("list", self.list_stocks_command))
        
        # 콜백 쿼리 핸들러 (주식 삭제 버튼 처리)
        self.app.add_handler(CallbackQueryHandler(self.button_callback, pattern='^(?!confirm_add_).*$'))

        # --- 관리자 명령어 핸들러 등록 --- #
        self.app.add_handler(CommandHandler("admin", self.admin_command))
        self.app.add_handler(CommandHandler("list_users", self.list_users_command))
        self.app.add_handler(CommandHandler("delete_user", self.delete_user_command))
        self.app.add_handler(CommandHandler("broadcast", self.broadcast_command))
        self.app.add_handler(CommandHandler("update_corp_codes", self.update_corp_codes_command))
        self.app.add_handler(CommandHandler("check_disclosures", self.check_disclosures_command))
        self.app.add_handler(CommandHandler("list_all_stocks", self.list_all_stocks_command))
        # ------------------------------- #

        # --- 사용자 검색 명령어 핸들러 등록 --- #
        self.app.add_handler(CommandHandler("search", self.search_stock_command))
        # ----------------------------------- #

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
        """주식 추가 처리 (사용자 입력 분석 및 확인 요청 - 검증 강화 v2)"""
        user_id = str(update.effective_user.id)
        text = update.message.text.strip()

        stock_code_input = None
        stock_name_input = None
        potential_matches = []
        exact_match = None # 정확히 일치하는 항목 저장

        # 입력 분석
        parts = text.split()
        if len(parts) >= 1 and parts[0].isdigit() and len(parts[0]) == 6:
            stock_code_input = parts[0]
            if len(parts) > 1:
                stock_name_input = ' '.join(parts[1:])
        elif len(parts) >= 1:
            stock_name_input = text
        else:
            await update.message.reply_text(
                "❌ 입력 형식이 올바르지 않습니다. 종목코드(6자리 숫자) 또는 종목명을 입력해주세요.\n"
                "다시 입력하거나 /cancel 로 취소하세요."
            )
            return ADDING_STOCK

        try:
            async with db.pool.acquire() as conn:
                # 1. 코드와 이름이 모두 입력된 경우: 정확히 일치하는지 확인 (corp_code 상관없이)
                if stock_code_input and stock_name_input:
                    exact_match = await conn.fetchrow(
                        "SELECT code, name, corp_code FROM stocks WHERE code = $1 AND name = $2",
                        stock_code_input, stock_name_input
                    )
                    if exact_match:
                        potential_matches = [exact_match]
                    # else: 정확히 일치하는 것 없음, 아래에서 유사 검색 진행

                # 2. 정확히 일치하는 것을 못 찾았거나, 코드 또는 이름만 입력된 경우: 유사 검색
                if not exact_match:
                    query = """
                        SELECT code, name, corp_code
                        FROM stocks
                        WHERE (code = $1 OR name = $2 OR ($2 IS NOT NULL AND name LIKE $3))
                           AND code IS NOT NULL -- 상장 폐지 등 제외 (종목코드 있어야 함)
                        ORDER BY
                            CASE WHEN code = $1 THEN 0 ELSE 1 END,
                            CASE WHEN name = $2 THEN 1 ELSE 2 END,
                            LENGTH(name)
                        LIMIT 5
                    """
                    name_like_pattern = f'%{stock_name_input}%' if stock_name_input else None
                    potential_matches = await conn.fetch(query, stock_code_input, stock_name_input, name_like_pattern)

                # 검색 결과 처리
                if not potential_matches:
                    await update.message.reply_text(
                        f"❌ 입력하신 정보와 일치하는 종목을 찾을 수 없습니다.\n"
                        f"입력: '{html.escape(text)}'\n\n"
                        "종목코드(6자리 숫자)나 이름을 확인 후 다시 입력해주세요.\n"
                        "➡️ 또는 /search 명령어로 먼저 검색해보세요! (예: /search 삼성)\n\n"
                        "취소하려면 /cancel 을 입력하세요."
                    )
                    return ADDING_STOCK

                # 가장 가능성 높은 1개 선택
                best_match = potential_matches[0]
                matched_code = best_match['code']
                matched_name = best_match['name']
                matched_corp_code = best_match['corp_code'] # corp_code 확인

                # 이미 모니터링 중인지 확인
                existing = await conn.fetchrow(
                    "SELECT 1 FROM user_stocks WHERE user_id = $1 AND stock_code = $2",
                    user_id, matched_code
                )
                if existing:
                    safe_name = html.escape(matched_name or "")
                    await update.message.reply_text(
                        f"⚠️ {safe_name}(<code>{matched_code}</code>)는 이미 모니터링 중입니다.",
                         parse_mode='HTML'
                    )
                    return ConversationHandler.END

                # 사용자 데이터에 후보 저장
                context.user_data['candidate_stock'] = {'code': matched_code, 'name': matched_name, 'corp_code': matched_corp_code}

                # 사용자에게 확인 요청
                corp_code_display = f"(고유번호: {matched_corp_code})" if matched_corp_code else "<b style='color:orange;'>(고유번호 없음)</b>"
                confirmation_message = f"❓ 이 종목이 맞습니까?\n\n➡️ {html.escape(matched_name or '')} (<code>{matched_code}</code>) {corp_code_display}\n\n"
                if not exact_match:
                     confirmation_message += f"(입력: '{html.escape(text)}')"

                # --- 수정: 버튼 3개로 변경 ---
                keyboard = [
                    [InlineKeyboardButton("✅ 예, 맞습니다", callback_data=f"confirm_add_yes_{matched_code}")],
                    [InlineKeyboardButton("🔄 다시 입력", callback_data="confirm_add_retry")],
                    [InlineKeyboardButton("❌ 취소", callback_data="confirm_add_cancel")]
                ]
                # ---------------------------
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(confirmation_message, reply_markup=reply_markup, parse_mode='HTML')
                return AWAITING_ADD_CONFIRMATION

        except ValueError as e:
             await update.message.reply_text(
                 f"❌ 입력 오류: {e}\n"
                 "다시 입력하거나 /cancel 로 취소하세요."
             )
             return ADDING_STOCK
        except Exception as e:
            logger.error(f"주식 추가 처리 중 오류 발생: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ 주식 추가 중 오류가 발생했습니다.\n"
                "다시 시도하거나 /cancel 로 취소하세요."
            )
            return ConversationHandler.END

    async def process_add_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """주식 추가 확인 처리 (인라인 버튼 콜백 - 3가지 옵션)"""
        query = update.callback_query
        await query.answer()

        user_id = str(query.from_user.id)
        callback_data = query.data
        should_end_conversation = True # 기본적으로 대화 종료
        next_state = ConversationHandler.END

        try:
            if callback_data.startswith("confirm_add_yes"):
                candidate = context.user_data.get('candidate_stock')
                if not candidate:
                     logger.warning(f"주식 추가 확인(yes) 오류: 사용자 데이터에 후보 종목 없음 (User ID: {user_id})")
                     await query.edit_message_text("❌ 오류 발생: 추가할 종목 정보를 찾을 수 없습니다. 다시 시도해주세요.")
                else:
                    stock_code = candidate['code']
                    stock_name = candidate['name']
                    async with db.pool.acquire() as conn:
                        # corp_code 확인 로직은 유지
                        stock_info = await conn.fetchrow("SELECT corp_code FROM stocks WHERE code = $1", stock_code)
                        if not stock_info or not stock_info['corp_code']:
                             logger.warning(f"종목 {stock_name}({stock_code}) 추가 시 corp_code가 DB에 없습니다. DART 갱신 필요.")

                        await conn.execute(
                            "INSERT INTO user_stocks (user_id, stock_code) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                            user_id, stock_code
                        )
                        total_stocks = await conn.fetchval("SELECT COUNT(*) FROM user_stocks WHERE user_id = $1", user_id)
                        safe_name = html.escape(stock_name or "")
                        success_message = (
                            f"✅ {safe_name}(<code>{stock_code}</code>) 모니터링을 시작합니다!\n\n"
                            f"📊 현재 모니터링 중인 주식: {total_stocks}개\n\n"
                            "➕ 추가 등록: /add\n"
                            "📋 목록 확인: /list"
                        )
                        await query.edit_message_text(success_message, parse_mode='HTML')
                        logger.info(f"User {user_id} added stock {stock_code} ({stock_name})")

            elif callback_data == "confirm_add_retry":
                await query.edit_message_text(
                    "알겠습니다. 추가할 주식을 다시 입력해주세요.\n"
                    "'종목코드 종목명' 또는 '종목명' 형식\n"
                    "(예: 005930 삼성전자 또는 삼성전자)\n\n"
                    "취소하려면 /cancel 을 입력하세요."
                )
                should_end_conversation = False # 대화 계속
                next_state = ADDING_STOCK # 상태 변경

            elif callback_data == "confirm_add_cancel":
                 await query.edit_message_text("❌ 작업이 취소되었습니다.")
                 # 대화는 기본값으로 종료됨
            
            else: # 예상치 못한 콜백 데이터
                 logger.warning(f"처리되지 않은 주식 추가 확인 콜백: {callback_data}")
                 await query.edit_message_text("알 수 없는 응답입니다. 작업을 취소합니다.")

        except Exception as e:
             logger.error(f"주식 추가 확인 콜백 처리 중 오류: {e}", exc_info=True)
             try:
                 await query.edit_message_text("❌ 처리 중 오류가 발생했습니다. 작업을 취소합니다.")
             except Exception as edit_e:
                 logger.error(f"주식 추가 확인 오류 메시지 전송 실패: {edit_e}")
        finally:
            # 사용자 데이터 정리
            if 'candidate_stock' in context.user_data:
                del context.user_data['candidate_stock']
            
            # 상태 반환 (대화 종료 또는 다음 상태)
            return next_state

    async def list_stocks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """모니터링 중인 주식 목록 보기 (공시 조회 버튼 추가)"""
        user_id = str(update.effective_user.id)
        message = update.message # CommandHandler에서 호출됨

        async with db.pool.acquire() as conn:
            user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            if not user:
                await message.reply_text("❌ 먼저 /register 명령으로 사용자 등록을 해주세요.")
                return

            stocks = await conn.fetch(
                """
                SELECT s.code, s.name, s.corp_code
                FROM user_stocks us
                JOIN stocks s ON us.stock_code = s.code
                WHERE us.user_id = $1
                ORDER BY s.name
                """,
                user_id
            )

            if not stocks:
                await message.reply_text(
                    "현재 모니터링 중인 주식이 없습니다.\n"
                    "/add 명령으로 추가해보세요."
                )
                return

            keyboard = []
            message_text = "📋 모니터링 중인 주식 목록:\n(종목 선택 시 최근 공시 5건 조회)\n\n"
            for stock in stocks:
                safe_name = html.escape(stock['name'] or "")
                button_text_base = f"{safe_name} ({stock['code']})"
                corp_code_status = "(공시조회 가능 ✅)" if stock['corp_code'] else "(공시조회 불가 ⚠️)"
                button_text = f"{button_text_base} {corp_code_status}"

                callback_action = f"list_show_{stock['code']}" if stock['corp_code'] else "noop" # 고유번호 없으면 noop
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_action)])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text(message_text, reply_markup=reply_markup, parse_mode='HTML')

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
        """모든 인라인 버튼 콜백 처리"""
        query = update.callback_query
        await query.answer() # 로딩 표시 제거

        data = query.data
        user_id = str(query.from_user.id)

        if data.startswith("remove_"):
            await self.handle_remove_button(query, context)
        elif data.startswith("list_users_page_"):
            await self.handle_list_users_pagination(query, context)
        elif data.startswith("search_add_"):
            await self.handle_search_add_button(query, context)
        elif data.startswith("list_show_"):
            await self.handle_list_show_button(query, context)
        elif data.startswith("list_all_stocks_page_"):
            await self.handle_list_all_stocks_pagination(query, context)
        elif data == "noop":
            pass
        else:
            logger.warning(f"처리되지 않은 콜백 데이터: {data}")
            try:
                await query.edit_message_text("알 수 없는 요청입니다.")
            except Exception as e:
                 logger.error(f"알 수 없는 콜백 오류 메시지 수정 실패: {e}")

    async def handle_remove_button(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """주식 삭제 버튼 처리"""
        stock_code = query.data.split("_")[1]
        user_id = str(query.from_user.id)
        try:
            async with db.pool.acquire() as conn:
                stock = await conn.fetchrow("SELECT name FROM stocks WHERE code = $1", stock_code)
                if not stock:
                    await query.edit_message_text("❌ 오류: 삭제하려는 종목을 찾을 수 없습니다.")
                    return

                await conn.execute("DELETE FROM user_stocks WHERE user_id = $1 AND stock_code = $2", user_id, stock_code)
                safe_stock_name = html.escape(stock['name'] or "")
                await query.edit_message_text(
                    f"✅ {safe_stock_name}(<code>{stock_code}</code>) 모니터링이 중지되었습니다.",
                    parse_mode='HTML'
                )
                logger.info(f"User {user_id} removed stock {stock_code}")
        except Exception as e:
            logger.error(f"주식 삭제 콜백 처리 중 오류: {e}", exc_info=True)
            try: await query.edit_message_text("❌ 오류: 주식 삭제 중 문제가 발생했습니다.")
            except Exception as edit_e: logger.warning(f"주식 삭제 오류 메시지 수정 실패: {edit_e}")

    async def handle_list_users_pagination(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """사용자 목록 페이징 버튼 처리"""
        page = int(query.data.split("_")[-1])
        await self.list_users_command(query, context, page=page) # query 객체를 넘겨 edit_message_text 사용

    async def handle_search_add_button(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """검색 결과에서 추가 버튼 처리"""
        stock_code = query.data.split("_")[-1]
        user_id = str(query.from_user.id)

        try:
            async with db.pool.acquire() as conn:
                stock = await conn.fetchrow("SELECT code, name, corp_code FROM stocks WHERE code = $1", stock_code)
                if not stock:
                    await query.edit_message_text("❌ 오류: 추가하려는 종목 정보를 찾을 수 없습니다.")
                    return

                # 이미 모니터링 중인지 확인
                existing = await conn.fetchrow("SELECT 1 FROM user_stocks WHERE user_id = $1 AND stock_code = $2", user_id, stock['code'])
                if existing:
                    safe_name = html.escape(stock['name'] or "")
                    await query.edit_message_text(f"⚠️ {safe_name}(<code>{stock['code']}</code>)는 이미 모니터링 중입니다.", parse_mode='HTML')
                    return

                # 사용자 데이터에 후보 저장 (add ConversationHandler와 동일한 키 사용)
                context.user_data['candidate_stock'] = {'code': stock['code'], 'name': stock['name'], 'corp_code': stock['corp_code']}

                # 확인 메시지 생성 및 전송 (process_add_stock 로직 재사용)
                matched_name = stock['name']
                matched_code = stock['code']
                matched_corp_code = stock['corp_code']
                corp_code_display = f"(고유번호: {matched_corp_code})" if matched_corp_code else "<b style='color:orange;'>(고유번호 없음)</b>"
                confirmation_message = f"❓ 이 종목을 추가하시겠습니까?\n\n➡️ {html.escape(matched_name or '')} (<code>{matched_code}</code>) {corp_code_display}\n\n"
                keyboard = [
                    [InlineKeyboardButton("✅ 예, 맞습니다", callback_data=f"confirm_add_yes_{matched_code}")],
                    [InlineKeyboardButton("🔄 다시 입력 (취소됨)", callback_data="confirm_add_retry")], # 검색에서 왔으므로 재입력은 취소와 동일하게 처리
                    [InlineKeyboardButton("❌ 취소", callback_data="confirm_add_cancel")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                # 검색 결과 메시지를 수정하여 확인 프롬프트 표시
                await query.edit_message_text(confirmation_message, reply_markup=reply_markup, parse_mode='HTML')
                # !!! 중요: 여기서 상태를 반환하지 않음. 콜백은 process_add_confirmation 에서 처리됨 !!!

        except Exception as e:
            logger.error(f"검색 결과 추가 콜백 처리 중 오류: {e}", exc_info=True)
            try: await query.edit_message_text("❌ 처리 중 오류가 발생했습니다.")
            except Exception as edit_e: logger.error(f"검색 결과 추가 오류 메시지 수정 실패: {edit_e}")

    async def handle_list_show_button(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """목록에서 공시 조회 버튼 처리"""
        stock_code = query.data.split("_")[-1]
        user_id = str(query.from_user.id)

        try:
            async with db.pool.acquire() as conn:
                 stock = await conn.fetchrow("SELECT name, corp_code FROM stocks WHERE code = $1", stock_code)

            if not stock or not stock['corp_code']:
                 await query.edit_message_text("❌ 오류: 종목 정보를 찾을 수 없거나 DART 고유번호가 없어 공시 조회가 불가능합니다.")
                 return

            corp_code = stock['corp_code']
            safe_name = html.escape(stock['name'] or "")
            await query.edit_message_text(f"⏳ {safe_name}(<code>{stock_code}</code>)의 최근 공시를 DART에서 조회 중...", parse_mode='HTML')

            # --- 수정: 함수 호출 방식 변경 ---
            disclosures_list = await disclosure.get_latest_disclosures(corp_code, limit=5)
            # -----------------------------

            if not disclosures_list:
                await query.edit_message_text(f"ℹ️ {safe_name}(<code>{stock_code}</code>)의 최근 공시 정보가 없습니다.", parse_mode='HTML')
                return

            message_lines = [f"📜 {safe_name}(<code>{stock_code}</code>) 최근 공시 (최대 5건):"]
            for disc in disclosures_list:
                detail_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={disc['rcept_no']}"
                report_title = html.escape(disc['report_nm'] or "제목 없음")
                report_date = f"{disc['rcept_dt'][:4]}-{disc['rcept_dt'][4:6]}-{disc['rcept_dt'][6:]}" if len(disc['rcept_dt']) == 8 else disc['rcept_dt']
                message_lines.append(f"\n📄 <a href='{detail_url}'>{report_title}</a> ({report_date})")

            await query.edit_message_text("\n".join(message_lines), parse_mode='HTML', disable_web_page_preview=True)

        except Exception as e:
            logger.error(f"공시 조회 콜백 처리 중 오류: {e}", exc_info=True)
            try: await query.edit_message_text("❌ 공시 조회 중 오류가 발생했습니다.")
            except Exception as edit_e: logger.error(f"공시 조회 오류 메시지 수정 실패: {edit_e}")

    async def handle_list_all_stocks_pagination(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """전체 종목 목록 페이징 버튼 처리"""
        try:
            page = int(query.data.split("_")[-1])
            # --- 로그 추가 ---
            logger.info(f"'/list_all_stocks' 페이징 요청 수신: page={page}, user={query.from_user.id}, data={query.data}")
            # ---------------
            # list_all_stocks_command 호출 전 로그
            logger.debug(f"Calling list_all_stocks_command for page {page} from callback.")
            await self.list_all_stocks_command(query, context, page=page)
            # list_all_stocks_command 호출 후 로그 (성공 시)
            logger.debug(f"Successfully processed list_all_stocks_command for page {page} from callback.")
        except Exception as e:
            # --- 오류 로그 강화 ---
            logger.error(f"전체 종목 목록 페이징 콜백 처리 중 오류 (data={query.data}): {e}", exc_info=True)
            # ---------------------
            try:
                await query.edit_message_text("❌ 페이징 처리 중 오류가 발생했습니다.")
            except Exception as edit_e:
                 logger.error(f"페이징 오류 메시지 수정 실패: {edit_e}")

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
            "/list_all_stocks - DB의 전체 주식 목록 보기\n"
            "/delete_user <user_id> - 특정 사용자 삭제\n"
            "/broadcast <message> - 모든 사용자에게 메시지 발송\n"
            "/update_corp_codes - DART 고유번호 정보 수동 갱신\n"
            "/check_disclosures [corp_code|all] - 수동으로 공시 정보 확인"
        )
        await update.message.reply_text(message)

    @admin_only
    async def list_users_command(self, update: object, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
        """등록된 모든 사용자 목록 보기 (페이징 및 종목 수 추가)"""
        # 콜백에서 호출될 경우 query 객체, CommandHandler에서 호출될 경우 Update 객체
        is_callback = isinstance(update, Update.callback_query.__class__)
        if is_callback:
            query = update
            message = query.message # 콜백의 원본 메시지
        else: # CommandHandler
            message = update.message
            query = None # 콜백 아님

        try:
            async with db.pool.acquire() as conn:
                # 총 사용자 수 계산
                total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
                if total_users == 0:
                    reply_text = "등록된 사용자가 없습니다."
                    if query: await query.edit_message_text(reply_text)
                    else: await message.reply_text(reply_text)
                    return

                total_pages = (total_users + USERS_PAGE_SIZE - 1) // USERS_PAGE_SIZE
                page = max(1, min(page, total_pages)) # 페이지 번호 범위 검증
                offset = (page - 1) * USERS_PAGE_SIZE

                # 사용자 목록 및 각 사용자의 등록 종목 수 조회
                users = await conn.fetch(
                    """
                    SELECT
                        u.user_id, u.username, u.first_name, u.registered_at,
                        COUNT(us.stock_code) as stock_count
                    FROM users u
                    LEFT JOIN user_stocks us ON u.user_id = us.user_id
                    GROUP BY u.user_id, u.username, u.first_name, u.registered_at
                    ORDER BY u.registered_at
                    LIMIT $1 OFFSET $2
                    """,
                    USERS_PAGE_SIZE, offset
                )

            message_lines = []
            for i, user in enumerate(users, start=offset + 1):
                safe_first_name = html.escape(user['first_name'] or "")
                safe_username = f"(@{html.escape(user['username'])})" if user['username'] else ""
                reg_time = user['registered_at'].strftime('%Y-%m-%d %H:%M') if user['registered_at'] else 'N/A'
                stock_count = user['stock_count'] # 추가된 종목 수
                message_lines.append(
                    f"{i}. {safe_first_name} {safe_username} (ID: <code>{user['user_id']}</code>)\n"
                    f"   - 등록: {reg_time}, 모니터링: {stock_count}개" # 종목 수 표시
                )

            header = f"👥 총 {total_users}명 사용자 (페이지 {page}/{total_pages}):\n\n"
            full_message = header + "\n".join(message_lines)

            # --- 페이징 버튼 생성 ---
            keyboard = []
            button_row = []
            if page > 1:
                button_row.append(InlineKeyboardButton("◀️ 이전", callback_data=f"list_users_page_{page-1}"))
            if page < total_pages:
                button_row.append(InlineKeyboardButton("다음 ▶️", callback_data=f"list_users_page_{page+1}"))
            if button_row:
                keyboard.append(button_row)

            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            # --------------------

            if query: # 콜백 응답으로 메시지 수정
                await query.edit_message_text(full_message, reply_markup=reply_markup, parse_mode='HTML')
            else: # 새 메시지로 전송
                await message.reply_text(full_message, reply_markup=reply_markup, parse_mode='HTML')

        except Exception as e:
            logger.error(f"사용자 목록 조회 오류 (page={page}): {e}", exc_info=True)
            error_text = "❌ 사용자 목록 조회 중 오류가 발생했습니다."
            if query: await query.edit_message_text(error_text)
            else: await message.reply_text(error_text)

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

    @admin_only
    async def update_corp_codes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """DART 고유번호 정보 수동 갱신"""
        await update.message.reply_text("🔄 DART 고유번호 정보 갱신을 시작합니다... 잠시 기다려주세요.")
        try:
            inserted, updated = await update_corp_codes_from_dart()
            # --- 수정: 결과 메시지에 삽입/갱신 수 모두 표시 ---
            await update.message.reply_text(
                f"✅ DART 고유번호 정보 갱신 완료!\n"
                f"- 신규 등록된 종목 수: {inserted}건\n"
                f"- 정보가 갱신된 종목 수: {updated}건"
            )
            # ---------------------------------------------
        except Exception as e:
            logger.error(f"수동 DART 고유번호 갱신 중 오류: {e}", exc_info=True)
            await update.message.reply_text(f"❌ DART 고유번호 정보 갱신 중 오류가 발생했습니다: {e}")

    @admin_only
    async def check_disclosures_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """수동으로 공시 정보 확인 (관리자 전용)"""
        args = context.args
        target = "all" # 기본값: 전체
        if args:
            target = args[0].strip()

        await update.message.reply_text(f"🔄 수동 공시 확인 시작 (대상: {target})...")

        try:
            if target.lower() == "all":
                # --- 수정: 함수 호출 방식 변경 ---
                await disclosure.check_disclosures()
                # -----------------------------
                await update.message.reply_text("✅ 전체 모니터링 대상에 대한 공시 확인 완료.")
            elif len(target) == 8 and target.isdigit(): # corp_code 형식인지 확인
                corp_code = target
                async with db.pool.acquire() as conn:
                     users = await conn.fetch(
                         """SELECT DISTINCT us.user_id, s.name, s.code
                            FROM user_stocks us
                            JOIN stocks s ON us.stock_code = s.code
                            WHERE s.corp_code = $1""",
                         corp_code
                     )
                if users:
                     user_ids = {user['user_id'] for user in users}
                     stock_name = users[0]['name'] # 대표 이름
                     stock_code = users[0]['code'] # 대표 코드
                     # --- 수정: 함수 호출 방식 변경 ---
                     # process_single_stock은 disclosure 모듈 내에 정의됨
                     new_disclosures_count = await disclosure.process_single_stock(corp_code, stock_code, stock_name, user_ids)
                     # 참고: process_single_stock이 반환값이 없다면 new_disclosures_count 사용 불가.
                     #       disclosure.py의 process_single_stock 함수 확인 필요.
                     #       현재 disclosure.py 코드 상으로는 반환값이 없으므로 아래 메시지 수정
                     # -----------------------------
                     # await update.message.reply_text(f"✅ {html.escape(stock_name)} ({corp_code}) 공시 확인 완료. {new_disclosures_count}건 신규 처리.")
                     await update.message.reply_text(f"✅ {html.escape(stock_name)} ({corp_code}) 공시 확인 및 처리 완료.") # 반환값 없으므로 메시지 수정
                else:
                    await update.message.reply_text(f"ℹ️ 입력한 고유번호({corp_code})를 모니터링하는 사용자가 없습니다.")
            else:
                await update.message.reply_text("❌ 잘못된 입력입니다. '/check_disclosures all' 또는 '/check_disclosures <8자리_고유번호>' 형식으로 입력하세요.")

        except Exception as e:
            logger.error(f"수동 공시 확인 중 오류 (대상: {target}): {e}", exc_info=True)
            await update.message.reply_text("❌ 수동 공시 확인 중 오류가 발생했습니다.")

    # --- 사용자 검색 명령어 핸들러 수정: 버튼 텍스트에서 HTML 태그 제거 ---
    async def search_stock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """주식 검색 기능 (추가 버튼 포함)"""
        search_term = " ".join(context.args).strip()
        if not search_term:
            await update.message.reply_text("검색할 종목코드 또는 종목명을 입력해주세요. (예: /search 삼성전자 또는 /search 005930)")
            return

        try:
            async with db.pool.acquire() as conn:
                query = """
                    SELECT code, name, corp_code
                    FROM stocks
                    WHERE (code LIKE $1 OR name LIKE $1) AND code IS NOT NULL -- 수정: code is not null 조건 추가
                    ORDER BY
                        CASE WHEN code = $2 THEN 0 ELSE 1 END,
                        CASE WHEN name = $2 THEN 0 ELSE 1 END,
                        name
                    LIMIT 10
                """
                rows = await conn.fetch(query, f'%{search_term}%', search_term)

            if not rows:
                await update.message.reply_text(f"'{html.escape(search_term)}'에 대한 검색 결과가 없습니다.")
                return

            message_lines = ["🔍 검색 결과 (선택하여 추가):"]
            keyboard = []
            for row in rows:
                safe_name = html.escape(row['name'] or "")
                # --- 수정: 버튼 텍스트에서 <code> 태그 제거 ---
                button_text = f"➕ {safe_name} ({row['code']})" # 일반 텍스트로 변경
                # -------------------------------------------
                callback_data = f"search_add_{row['code']}"
                # parse_mode 인자 없는 것 재확인
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

            if not keyboard:
                 await update.message.reply_text(f"'{html.escape(search_term)}'에 대한 검색 결과 표시 중 오류.")
                 return

            reply_markup = InlineKeyboardMarkup(keyboard)
            # 메시지 자체는 HTML 파싱 허용 유지 (버튼과 무관)
            await update.message.reply_text("\n".join(message_lines), reply_markup=reply_markup, parse_mode='HTML')

        except Exception as e:
            logger.error(f"주식 검색 중 오류 발생 ({search_term}): {e}", exc_info=True)
            await update.message.reply_text("❌ 검색 중 오류가 발생했습니다.")
    # ----------------------------------- #

    @admin_only
    async def list_all_stocks_command(self, update: object, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
        """DB에 저장된 전체 주식 목록 보기 (페이징)"""
        is_callback = isinstance(update, Update.callback_query.__class__)
        if is_callback:
            query = update
            message = query.message
            # --- 로그 추가: 콜백 호출 시 ---
            logger.info(f"list_all_stocks_command 호출됨 (콜백): page={page}, message_id={message.message_id}, user={query.from_user.id}")
            # ------------------------------
        else: # CommandHandler
            message = update.message
            query = None
            # --- 로그 추가: 명령어 호출 시 ---
            logger.info(f"list_all_stocks_command 호출됨 (명령어): page={page}, user={message.from_user.id}")
            # -----------------------------

        try:
            async with db.pool.acquire() as conn:
                total_stocks = await conn.fetchval("SELECT COUNT(*) FROM stocks")
                if total_stocks == 0:
                    reply_text = "DB에 저장된 주식이 없습니다."
                    if query: await query.edit_message_text(reply_text)
                    else: await message.reply_text(reply_text)
                    return

                total_pages = (total_stocks + STOCKS_PAGE_SIZE - 1) // STOCKS_PAGE_SIZE
                page = max(1, min(page, total_pages))
                offset = (page - 1) * STOCKS_PAGE_SIZE

                stocks_list = await conn.fetch(
                    """
                    SELECT code, name, corp_code
                    FROM stocks
                    ORDER BY name
                    LIMIT $1 OFFSET $2
                    """,
                    STOCKS_PAGE_SIZE, offset
                )

            message_lines = []
            for i, stock in enumerate(stocks_list, start=offset + 1):
                safe_name = html.escape(stock['name'] or "이름 없음")
                corp_code_display = f"(<code>{stock['corp_code']}</code>)" if stock['corp_code'] else "(고유번호 없음)"
                message_lines.append(f"{i}. {safe_name} (<code>{stock['code']}</code>) {corp_code_display}")

            header = f"📚 전체 주식 DB 목록 ({total_stocks}개, 페이지 {page}/{total_pages}):\n\n"
            full_message = header + "\n".join(message_lines)

            keyboard = []
            button_row = []
            if page > 1:
                button_row.append(InlineKeyboardButton("◀️ 이전", callback_data=f"list_all_stocks_page_{page-1}"))
            if page < total_pages:
                button_row.append(InlineKeyboardButton("다음 ▶️", callback_data=f"list_all_stocks_page_{page+1}"))
            if button_row:
                keyboard.append(button_row)

            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

            if query:
                # --- 로그 추가: 메시지 수정 전 ---
                logger.info(f"list_all_stocks_command (콜백): 메시지 수정 시도 (message_id={message.message_id}, page={page})")
                # ------------------------------
                await query.edit_message_text(full_message, reply_markup=reply_markup, parse_mode='HTML')
                # --- 로그 추가: 메시지 수정 후 ---
                logger.info(f"list_all_stocks_command (콜백): 메시지 수정 완료 (message_id={message.message_id}, page={page})")
                # ------------------------------
            else:
                # --- 로그 추가: 새 메시지 전송 전 ---
                logger.info(f"list_all_stocks_command (명령어): 새 메시지 전송 시도 (page={page})")
                # -------------------------------
                await message.reply_text(full_message, reply_markup=reply_markup, parse_mode='HTML')
                # --- 로그 추가: 새 메시지 전송 후 ---
                logger.info(f"list_all_stocks_command (명령어): 새 메시지 전송 완료 (page={page})")
                # -------------------------------

        except Exception as e:
            # --- 오류 로그 강화 ---
            logger.error(f"전체 주식 목록 조회/표시 오류 (page={page}, is_callback={is_callback}): {e}", exc_info=True)
            # -------------------
            error_text = "❌ 전체 주식 목록 조회 중 오류가 발생했습니다."
            try:
                if query:
                    await query.edit_message_text(error_text)
                else:
                    await message.reply_text(error_text)
            except Exception as edit_e:
                 # --- 오류 메시지 전송 실패 로그 강화 ---
                 logger.error(f"전체 주식 목록 조회 오류 메시지 전송/수정 실패: {edit_e}")
                 # -----------------------------------

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