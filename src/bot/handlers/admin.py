import os
import httpx
import logging
from functools import wraps
from typing import Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from src.common.utils.http_client import get_retry_client
from src.bot.decorators import ensure_user_registered

logger = logging.getLogger(__name__)

# --- API Configuration ---
API_HOST = os.getenv("API_HOST", "localhost")
API_URL = f"http://{API_HOST}:8000"
API_V1_URL = f"{API_URL}/api/v1"
BOT_SECRET_KEY = os.getenv("BOT_SECRET_KEY")

# --- Admin Configuration ---
ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "")

# --- Helper Functions ---
async def get_auth_token(telegram_id: int) -> Optional[str]:
    """API로부터 해당 telegram_id의 사용자를 위한 JWT 토큰을 받아옵니다."""
    if not BOT_SECRET_KEY:
        logger.error("BOT_SECRET_KEY가 설정되지 않았습니다. 인증 토큰을 발급할 수 없습니다.")
        return None
    
    headers = {"X-Bot-Secret-Key": BOT_SECRET_KEY}
    data = {"telegram_id": telegram_id}
    
    try:
        async with get_retry_client() as client:
            response = await client.post(f"{API_V1_URL}/auth/bot/token", headers=headers, json=data)
            response.raise_for_status()
            token_data = response.json()
            return token_data.get("access_token")
    except httpx.HTTPStatusError as e:
        logger.error(f"API 토큰 발급 실패: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"토큰 발급 중 예외 발생: {e}")
    return None

def admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if user_id != ADMIN_ID:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="관리자 전용 명령어입니다.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

@admin_only
@ensure_user_registered
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """관리자 메뉴를 버튼과 함께 보여줍니다."""
    keyboard = [
        [InlineKeyboardButton("📊 시스템 통계 조회", callback_data="admin:stats")],
        [InlineKeyboardButton("⏰ 스케줄러 상태 조회", callback_data="admin:show_schedules")],
        [InlineKeyboardButton("🔔 테스트 알림 발송", callback_data="admin:test_notify")],
        [InlineKeyboardButton("💾 (초기 1회) 과거 시세 전체 갱신", callback_data="admin:update_prices_all")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "[관리자 전용 명령어]\n\n원하시는 작업을 선택해주세요.\n\n`과거 시세 전체 갱신`은 시스템 초기 설정 시 한 번만 실행하면 되며, 이후에는 스케줄러에 의해 자동으로 관리됩니다.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

@admin_only
@ensure_user_registered
async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """관리자 메뉴 버튼 콜백을 처리합니다."""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "admin:stats":
        await query.message.reply_text("📊 시스템 통계 조회를 시작합니다...")
        await admin_stats(update, context)
    elif action == "admin:show_schedules":
        await query.message.reply_text("⏰ 스케줄러 상태 조회를 시작합니다...")
        await admin_show_schedules(update, context)
    elif action == "admin:test_notify":
        await query.message.reply_text("🔔 테스트 알림을 발송합니다...")
        await test_notify_command(update, context)
    elif action == "admin:update_prices_all":
        await query.message.reply_text("💾 과거 시세 전체 갱신을 요청합니다. 시간이 다소 소요될 수 있습니다.")
        # Call the original function with default parameters for a full update
        await admin_update_historical_prices(update, context, full_update=True)

@ensure_user_registered
async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        async with get_retry_client() as client:
            response = await client.get(f"{API_URL}/health", timeout=10)
            response.raise_for_status()
            data = response.json()
            await update.message.reply_text(f"서비스 상태: {data.get('status', 'unknown')}")
    except Exception as e:
        await update.message.reply_text(f"헬스체크에 실패했습니다. 서버 상태를 확인해주세요.")

@admin_only
@ensure_user_registered
async def admin_show_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = await get_auth_token(update.effective_chat.id)
    if not token:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ 인증 토큰 발급에 실패했습니다.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with get_retry_client() as client:
            response = await client.get(f"{API_V1_URL}/admin/schedule/status", headers=headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                jobs = result.get('jobs', [])
                
                if not jobs:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="⏰ 실행 중인 스케줄 잡이 없습니다.")
                    return

                keyboard = []
                message = "⏰ **스케줄러 잡 목록**\n\n"
                for job in jobs:
                    job_id = job.get('id', 'N/A')
                    job_name = job.get('name', job_id)
                    next_run_time = job.get('next_run_time', 'N/A')
                    if next_run_time != 'N/A':
                        next_run_time = datetime.fromisoformat(next_run_time).strftime('%Y-%m-%d %H:%M:%S')

                    message += f"🔹 **{job_name}**\n"
                    message += f"   - ID: `{job_id}`\n"
                    message += f"   - 다음 실행: {next_run_time}\n"                    
                    button = InlineKeyboardButton(f"▶️ 즉시 실행: {job_name}", callback_data=f"trigger_job_{job_id}")
                    keyboard.append([button])

                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"조회 실패: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"스케줄러 상태 조회 중 오류: {str(e)}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="스케줄러 상태 조회 중 오류가 발생했습니다.")

@admin_only
@ensure_user_registered
async def admin_trigger_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    token = await get_auth_token(chat_id)
    if not token:
        await context.bot.send_message(chat_id=chat_id, text="❌ 인증 토큰 발급에 실패했습니다.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        text = update.message.text
        parts = text.split()
        if len(parts) < 2:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ 사용법: /trigger_job job_id\n예시: /trigger_job update_master_job")
            return
        
        job_id = parts[1]
        
        await context.bot.send_message(chat_id=chat_id, text=f"⏳ 잡 실행 요청 접수: `{job_id}`. 작업이 완료되면 알림이 전송됩니다.", parse_mode='Markdown')

        async with get_retry_client() as client:
            response = await client.post(
                f"{API_V1_URL}/admin/schedule/trigger/{job_id}", 
                headers=headers, 
                json={"chat_id": chat_id},
                timeout=10
            )
            response.raise_for_status()

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        if e.response.status_code == 404:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ 잡을 찾을 수 없습니다: `{job_id}`")
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ 잡 실행 실패: {e.response.status_code} {error_detail}")
        logger.error(f"잡 실행 중 HTTP 오류: {e.response.status_code} - {error_detail}", exc_info=True)
    except Exception as e:
        logger.error(f"잡 실행 중 오류: {str(e)}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text="잡 수동 실행 중 오류가 발생했습니다.")

@admin_only
@ensure_user_registered
async def admin_update_historical_prices(update: Update, context: ContextTypes.DEFAULT_TYPE, full_update: bool = False):
    chat_id = update.effective_chat.id
    token = await get_auth_token(chat_id)
    if not token:
        await context.bot.send_message(chat_id=chat_id, text="❌ 인증 토큰 발급에 실패했습니다.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        stock_identifier = None
        start_date_str = "1990-01-01"
        end_date_str = datetime.now().strftime('%Y-%m-%d')

        if not full_update:
            text = update.message.text
            parts = text.split()
            
            def is_valid_date(date_string):
                try:
                    datetime.strptime(date_string, '%Y-%m-%d')
                    return True
                except ValueError:
                    return False

            if len(parts) == 2:
                if is_valid_date(parts[1]):
                    end_date_str = parts[1]
                else:
                    stock_identifier = parts[1]
            elif len(parts) == 3:
                if is_valid_date(parts[1]) and is_valid_date(parts[2]):
                    start_date_str = parts[1]
                    end_date_str = parts[2]
                elif not is_valid_date(parts[1]) and is_valid_date(parts[2]):
                    stock_identifier = parts[1]
                    end_date_str = parts[2]
                else:
                    await context.bot.send_message(chat_id=chat_id, text="❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해주세요.")
                    return
            elif len(parts) == 4:
                if is_valid_date(parts[2]) and is_valid_date(parts[3]):
                    stock_identifier = parts[1]
                    start_date_str = parts[2]
                    end_date_str = parts[3]
                else:
                    await context.bot.send_message(chat_id=chat_id, text="❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해주세요.")
                    return
            elif len(parts) == 1 and not full_update:
                pass # Full update, no args needed
            elif len(parts) > 1:
                await context.bot.send_message(chat_id=chat_id, text="❌ 사용법: /update_historical_prices [종목코드/종목명] [종료_날짜] 또는 [종목코드/종목명] [시작_날짜] [종료_날짜]\n날짜 형식: YYYY-MM-DD")
                return

        if stock_identifier:
            await context.bot.send_message(chat_id=chat_id, text=f"⏳ 과거 일별 시세 갱신 요청 접수: {stock_identifier} ({start_date_str} ~ {end_date_str}). 작업이 완료되면 알림이 전송됩니다.", parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"⏳ 과거 일별 시세 전체 갱신 요청 접수: {start_date_str} ~ {end_date_str}. 작업이 완료되면 알림이 전송됩니다.", parse_mode='Markdown')

        async with get_retry_client() as client:
            response = await client.post(
                f"{API_V1_URL}/admin/update_historical_prices", 
                headers=headers, 
                json={
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    "stock_identifier": stock_identifier,
                    "chat_id": chat_id
                },
                timeout=30
            )
            response.raise_for_status()
            await context.bot.send_message(chat_id=chat_id, text="✅ 과거 일별 시세 갱신 작업이 성공적으로 트리거되었습니다.", parse_mode='Markdown')

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        await context.bot.send_message(chat_id=chat_id, text=f"❌ 과거 일별 시세 갱신 실패: {e.response.status_code} {error_detail}")
        logger.error(f"과거 일별 시세 갱신 중 HTTP 오류: {e.response.status_code} - {error_detail}", exc_info=True)
    except Exception as e:
        logger.error(f"과거 일별 시세 갱신 중 오류: {str(e)}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text="과거 일별 시세 갱신 중 오류가 발생했습니다.")

@admin_only
@ensure_user_registered
async def trigger_job_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer(text="잡 실행을 요청합니다...")

    job_id = query.data.replace("trigger_job_", "")
    chat_id = update.effective_chat.id

    token = await get_auth_token(chat_id)
    if not token:
        await context.bot.send_message(chat_id=chat_id, text="❌ 인증 토큰 발급에 실패했습니다.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        await context.bot.send_message(chat_id=chat_id, text=f"⏳ 잡 실행 요청 접수: `{job_id}`. 작업이 완료되면 알림이 전송됩니다.", parse_mode='Markdown')

        async with get_retry_client() as client:
            response = await client.post(
                f"{API_V1_URL}/admin/schedule/trigger/{job_id}",
                headers=headers,
                json={"chat_id": chat_id},
                timeout=10
            )
            response.raise_for_status()

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        if e.response.status_code == 404:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ 잡을 찾을 수 없습니다: `{job_id}`")
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ 잡 실행 실패: {e.response.status_code} {error_detail}")
        logger.error(f"잡 실행(콜백) 중 HTTP 오류: {e.response.status_code} - {error_detail}", exc_info=True)
    except Exception as e:
        logger.error(f"잡 실행(콜백) 중 오류: {str(e)}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text="잡 수동 실행(콜백) 중 오류가 발생했습니다.")

@admin_only
@ensure_user_registered
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = await get_auth_token(update.effective_chat.id)
    if not token:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ 인증 토큰 발급에 실패했습니다.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with get_retry_client() as client:
            response = await client.get(f"{API_V1_URL}/admin/admin_stats", headers=headers, timeout=10)
            if response.status_code == 200:
                stats = response.json()
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"📊 **시스템 통계**\n\n👥 사용자 수: {stats['user_count']}명\n💰 모의매매 기록: {stats['trade_count']}건\n🔮 예측 기록: {stats['prediction_count']}건", parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ 조회 실패: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"통계 조회 중 오류: {str(e)}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="통계 조회 중 오류가 발생했습니다.")

@admin_only
@ensure_user_registered
async def test_notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        await context.bot.send_message(chat_id=chat_id, text="[테스트 알림] 공시 알림 테스트 메시지입니다.\n\n(이 메시지가 즉시 도착하면 실시간 알림 전송이 정상 동작함을 의미합니다.)")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"테스트 알림 전송에 실패했습니다. 텔레그램 봇 설정을 확인해주세요.")

# --- 핸들러 등록 ---
def get_admin_handler():
    return CommandHandler("admin", admin_command)

def get_admin_callback_handler():
    return CallbackQueryHandler(admin_callback_handler, pattern="^admin:")

def get_health_handler():
    return CommandHandler("health", health_command)

def get_admin_show_schedules_handler():
    return CommandHandler("show_schedules", admin_show_schedules)

def get_admin_trigger_job_handler():
    return CommandHandler("trigger_job", admin_trigger_job)

def get_trigger_job_callback_handler():
    return CallbackQueryHandler(trigger_job_callback, pattern="^trigger_job_")

def get_admin_stats_handler():
    return CommandHandler("admin_stats", admin_stats)

def get_test_notify_handler():
    return CommandHandler("test_notify", test_notify_command)

def get_admin_update_historical_prices_handler():
    return CommandHandler("update_historical_prices", admin_update_historical_prices)