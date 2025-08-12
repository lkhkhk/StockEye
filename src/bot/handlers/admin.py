import os
import httpx
import logging
import asyncio
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

ADMIN_COMMANDS_TEXT = (
    "[관리자 전용 명령어 안내]\n" 
    "\n" 
    "**시스템 관리**\n" 
    "- /admin_stats : 전체 시스템 통계 조회\n" 
    "- /show_schedules : 스케줄러 상태 및 등록된 잡 목록 조회\n" 
    "- /trigger_job [job_id] : 특정 스케줄러 잡 수동 실행 (예: /trigger_job update_master_job)\n" 
    "\n" 
    "**데이터 갱신**\n" 
    "- /update_master : 전체 종목 마스터 데이터 갱신 (신규/변경 종목 반영)\n" 
    "- /update_price : 전체 종목 일별 시세 데이터 갱신\n" 
    "- /update_disclosure [종목코드|종목명|고유번호] : 특정 종목 공시 이력 수동 갱신 (입력 없으면 전체 처리)\n" 
    "\n" 
    "**테스트 및 디버그**\n" 
    "- /test_notify : 공시 알림 테스트 메시지 전송\n" 
    "- /health : API 서비스 헬스 체크\n" 
    "\n" 
    "**참고:**\n" 
    "- 데이터 갱신과 같은 대량 작업은 시간이 소요될 수 있으며, 작업 시작 및 완료 시 별도 안내 메시지가 전송됩니다.\n" 
    "- 관리자 외 사용자는 접근할 수 없습니다."
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
async def admin_update_master(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="종목마스터 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다.")
    asyncio.create_task(run_update_master_and_notify(context, int(chat_id)))

async def run_update_master_and_notify(context, chat_id: int):
    token = await get_auth_token(chat_id)
    if not token:
        await context.bot.send_message(chat_id=chat_id, text="❌ 인증 토큰 발급에 실패하여 작업을 진행할 수 없습니다.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with get_retry_client() as client:
            response = await client.post(f"{API_V1_URL}/admin/update_master", headers=headers, timeout=60)
            if response.status_code == 200:
                result = response.json()
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(f"✅ 종목마스터 갱신 완료!\n" 
                          f"📊 처리된 종목: {result['updated_count']}개\n" 
                          f"⏰ 시간: {result['timestamp']}")
                )
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ 갱신 실패: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"종목마스터 갱신(비동기) 중 오류: {str(e)}")
        await context.bot.send_message(chat_id=chat_id, text=f"오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

@admin_only
@ensure_user_registered
async def admin_update_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="일별시세 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다.")
    asyncio.create_task(run_update_price_and_notify(context, int(chat_id)))

async def run_update_price_and_notify(context, chat_id: int):
    token = await get_auth_token(chat_id)
    if not token:
        await context.bot.send_message(chat_id=chat_id, text="❌ 인증 토큰 발급에 실패하여 작업을 진행할 수 없습니다.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with get_retry_client() as client:
            response = await client.post(f"{API_V1_URL}/admin/update_price", headers=headers, timeout=60)
            if response.status_code == 200:
                result = response.json()
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(f"✅ 일별시세 갱신 완료!\n" 
                          f"📊 처리된 데이터: {result['updated_count']}개\n" 
                          f"⏰ 시간: {result['timestamp']}")
                )
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ 갱신 실패: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"일별시세 갱신(비동기) 중 오류: {str(e)}")
        await context.bot.send_message(chat_id=chat_id, text=f"오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

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
                message = "⏰ **스케줄러 잡 목록**\n\n" 
                if not jobs:
                    message += "실행 중인 잡이 없습니다."
                else:
                    for job in jobs:
                        message += f"- **ID:** `{job['id']}`\n" 
                        message += f"  **다음 실행:** `{job['next_run_time']}`\n" 
                        message += f"  **트리거:** `{job['trigger']}`\n"
                await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode='Markdown')
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
async def admin_update_disclosure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args
    if args:
        code_or_name = args[0]
        async with get_retry_client() as client:
            search_resp = await client.get(f"{API_V1_URL}/symbols/search", params={"query": code_or_name}, timeout=10)
            if search_resp.status_code == 200:
                stocks = search_resp.json()
                if isinstance(stocks, list) and len(stocks) > 1:
                    keyboard = []
                    for stock in stocks[:10]:
                        btn_text = f"{stock.get('name','')}"
                        callback_data = f"update_disclosure_{stock.get('symbol','')}"
                        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await context.bot.send_message(chat_id=chat_id, text="여러 종목이 검색되었습니다. 갱신할 종목을 선택하세요:", reply_markup=reply_markup)
                    return
    
    await context.bot.send_message(chat_id=chat_id, text="공시 이력 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다.")
    asyncio.create_task(run_update_disclosure_and_notify(context, int(chat_id), args))

async def run_update_disclosure_and_notify(context, chat_id: int, args: list):
    token = await get_auth_token(chat_id)
    if not token:
        await context.bot.send_message(chat_id=chat_id, text="❌ 인증 토큰 발급에 실패하여 작업을 진행할 수 없습니다.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    code_or_name = args[0] if args else None
    
    try:
        async with get_retry_client() as client:
            params = {"code_or_name": code_or_name} if code_or_name else {}
            response = await client.post(f"{API_V1_URL}/admin/update_disclosure", headers=headers, params=params, timeout=60)
            if response.status_code == 200:
                result = response.json()
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(f"✅ 공시 이력 갱신 완료!\n" 
                          f"➕ 추가: {result.get('inserted', 0)}건\n" 
                          f"⏩ 중복: {result.get('skipped', 0)}건\n" 
                          f"⚠️ 에러: {len(result.get('errors', []))}건")
                )
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ 갱신 실패: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"공시 이력 갱신(비동기) 중 오류: {str(e)}")
        await context.bot.send_message(chat_id=chat_id, text=f"오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

@ensure_user_registered
async def update_disclosure_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    token = await get_auth_token(query.from_user.id)
    if not token:
        await query.edit_message_text("❌ 인증 토큰 발급에 실패했습니다.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        data = query.data
        if data.startswith("update_disclosure_"):
            symbol = data.replace("update_disclosure_", "")
            async with get_retry_client() as client:
                response = await client.post(f"{API_V1_URL}/admin/update_disclosure", headers=headers, params={"code_or_name": symbol}, timeout=60)
                if response.status_code == 200:
                    result = response.json()
                    await query.edit_message_text(
                        f"✅ 공시 이력 갱신 완료!\n" 
                        f"➕ 추가: {result.get('inserted', 0)}건\n" 
                        f"⏩ 중복: {result.get('skipped', 0)}건\n" 
                        f"⚠️ 에러: {len(result.get('errors', []))}건"
                    )
                else:
                    await query.edit_message_text(f"공시 이력 갱신 중 오류가 발생했습니다: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"공시 이력 갱신(버튼) 중 오류: {str(e)}")
        await query.edit_message_text("공시 이력 갱신(버튼) 중 오류가 발생했습니다.")

@admin_only
@ensure_user_registered
async def test_notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        await context.bot.send_message(chat_id=chat_id, text="[테스트 알림] 공시 알림 테스트 메시지입니다.\n\n(이 메시지가 즉시 도착하면 실시간 알림 전송이 정상 동작함을 의미합니다.)")
    except Exception as e:
        await update.message.reply_text(f"테스트 알림 전송에 실패했습니다. 텔레그램 봇 설정을 확인해주세요.")

# --- 핸들러 등록 --- #
def get_admin_handler():
    return CommandHandler("admin", admin_command)

def get_health_handler():
    return CommandHandler("health", health_command)

def get_admin_update_master_handler():
    return CommandHandler("update_master", admin_update_master)

def get_admin_update_price_handler():
    return CommandHandler("update_price", admin_update_price)

def get_admin_show_schedules_handler():
    return CommandHandler("show_schedules", admin_show_schedules)

def get_admin_trigger_job_handler():
    return CommandHandler("trigger_job", admin_trigger_job)

def get_admin_stats_handler():
    return CommandHandler("admin_stats", admin_stats)

def get_admin_update_disclosure_handler():
    return CommandHandler("update_disclosure", admin_update_disclosure)

def get_update_disclosure_callback_handler():
    return CallbackQueryHandler(update_disclosure_callback, pattern="^update_disclosure_")

def get_test_notify_handler():
    return CommandHandler("test_notify", test_notify_command)