import os
import httpx
import logging
from functools import wraps
from typing import Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from src.common.http_client import get_retry_client
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

# --- 관리자 명령어 텍스트 ---
ADMIN_COMMANDS_TEXT = (
    "[관리자 전용 명령어 안내]\n" 
    "\n" 
    "**시스템 관리**\n" 
    "- /admin_stats          : 전체 시스템 통계 조회\n" 
    "- /show_schedules       : 스케줄러 상태 및 등록된 잡 목록 조회 (잡 즉시 실행 가능)\n" 
    "- /trigger_job [job_id] : (비상용) 특정 스케줄러 잡 ID로 수동 실행\n"
)

@admin_only
@ensure_user_registered
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ADMIN_COMMANDS_TEXT)

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
        await update.message.reply_text("❌ 인증 토큰 발급에 실패했습니다.")
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
                await update.message.reply_text(f"조회 실패: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"스케줄러 상태 조회 중 오류: {str(e)}")
        await update.message.reply_text("스케줄러 상태 조회 중 오류가 발생했습니다.")

@admin_only
@ensure_user_registered
async def admin_trigger_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = await get_auth_token(update.effective_chat.id)
    if not token:
        await update.message.reply_text("❌ 인증 토큰 발급에 실패했습니다.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        text = update.message.text
        parts = text.split()
        if len(parts) < 2:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ 사용법: /trigger_job job_id\n예시: /trigger_job update_master_job")
            return
        
        job_id = parts[1]
        chat_id = update.effective_chat.id
        
        async with get_retry_client() as client:
            response = await client.post(
                f"{API_V1_URL}/admin/schedule/trigger/{job_id}", 
                headers=headers, 
                json={"chat_id": chat_id},
                timeout=10
            )
            if response.status_code == 200:
                message = (
                    f"✅ 잡 실행 요청 접수\n"
                    f"- 잡 ID: `{job_id}`\n\n"
                    f"완료 시 별도 알림이 전송됩니다."
                )
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text=message,
                    parse_mode='Markdown'
                )
            elif response.status_code == 404:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ 잡을 찾을 수 없습니다: {job_id}")
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ 실행 실패: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"잡 실행 중 오류: {str(e)}")
        await update.message.reply_text("잡 수동 실행 중 오류가 발생했습니다.")

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
        async with get_retry_client() as client:
            response = await client.post(
                f"{API_V1_URL}/admin/schedule/trigger/{job_id}",
                headers=headers,
                json={"chat_id": chat_id},
                timeout=10
            )
            if response.status_code == 200:
                message = (
                    f"✅ 잡 실행 요청 접수\n"
                    f"- 잡 ID: `{job_id}`\n\n"
                    f"완료 시 별도 알림이 전송됩니다."
                )
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            elif response.status_code == 404:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ 잡을 찾을 수 없습니다: {job_id}")
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ 실행 실패: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"잡 실행(콜백) 중 오류: {str(e)}")
        await context.bot.send_message(chat_id=chat_id, text="잡 수동 실행(콜백) 중 오류가 발생했습니다.")

@admin_only
@ensure_user_registered
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = await get_auth_token(update.effective_chat.id)
    if not token:
        await update.message.reply_text("❌ 인증 토큰 발급에 실패했습니다.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with get_retry_client() as client:
            response = await client.get(f"{API_V1_URL}/admin/admin_stats", headers=headers, timeout=10)
            if response.status_code == 200:
                stats = response.json()
                await update.message.reply_text(f"📊 **시스템 통계**\n\n👥 사용자 수: {stats['user_count']}명\n💰 모의매매 기록: {stats['trade_count']}건\n🔮 예측 기록: {stats['prediction_count']}건", parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ 조회 실패: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"통계 조회 중 오류: {str(e)}")
        await update.message.reply_text("통계 조회 중 오류가 발생했습니다.")



@admin_only
@ensure_user_registered
async def test_notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        await context.bot.send_message(chat_id=chat_id, text="[테스트 알림] 공시 알림 테스트 메시지입니다.\n\n(이 메시지가 즉시 도착하면 실시간 알림 전송이 정상 동작함을 의미합니다.)")
    except Exception as e:
        await update.message.reply_text(f"테스트 알림 전송에 실패했습니다. 텔레그램 봇 설정을 확인해주세요.")

# --- 핸들러 등록 ---
def get_admin_handler():
    return CommandHandler("admin", admin_command)

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