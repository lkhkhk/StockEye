import os
import requests
import logging
import asyncio
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from src.common.http_client import session # Import the session object directly

logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL", "http://api_service:8000")

ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "")

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
    "- /admin_stats : 전체 통계 조회\n"
    "- /update_master : 종목마스터 갱신(초기 적재/갱신 겸용)\n"
    "- /update_price : 일별시세 갱신\n"
    "- /show_schedules : 스케줄러 상태 조회\n"
    "- /trigger_job [job_id] : 특정 잡 수동 실행\n"
    "- /update_disclosure [종목코드|종목명|고유번호] : 공시 이력 수동 갱신 (입력 없으면 전체 처리, 복수 검색 시 선택 UI 제공)\n"
    "\n"
    "초기 적재와 갱신은 /update_master 한 번으로 모두 처리됩니다.\n"
    "(종목이 없으면 신규 등록, 있으면 갱신)\n"
    "\n"
    "공시/마스터/시세 등 전체처리, 대량 작업은 시간이 소요될 수 있으며,\n"
    "작업 시작 시 중간 안내 메시지와 완료 후 결과 메시지가 별도로 안내됩니다.\n"
    "\n"
    "관리자 외 사용자는 접근할 수 없습니다."
)

@admin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ADMIN_COMMANDS_TEXT)

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = await session.get(f"{API_URL}/health", timeout=10) # session 사용 및 timeout 추가
        response.raise_for_status()
        data = response.json()
        await update.message.reply_text(f"서비스 상태: {data.get('status', 'unknown')}")
    except Exception as e:
        await update.message.reply_text(f"헬스체크에 실패했습니다. 서버 상태를 확인해주세요.")

async def admin_update_master(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """종목마스터 갱신 명령어"""
    try:
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text="종목마스터 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다.")
        asyncio.create_task(run_update_master_and_notify(context, chat_id))
        return  # 안내 메시지 전송 후 즉시 반환
    except Exception as e:
        logger.error(f"종목마스터 갱신 중 오류: {str(e)}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

async def run_update_master_and_notify(context, chat_id):
    try:
        response = await session.post(f"{API_URL}/admin/update_master", timeout=60) # session 사용 및 timeout 추가
        if response.status_code == 200:
            result = await response.json()
            await context.bot.send_message(
                chat_id=chat_id,
                text=(f"✅ 종목마스터 갱신 완료!\n"
                      f"📊 처리된 종목: {result['updated_count']}개\n"
                      f"⏰ 시간: {result['timestamp']}")
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ 갱신 실패: {response.status_code}")
    except Exception as e:
        logger.error(f"종목마스터 갱신(비동기) 중 오류: {str(e)}")
        await context.bot.send_message(chat_id=chat_id, text=f"오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

async def admin_update_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """일별시세 갱신 명령어"""
    try:
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text="일별시세 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다.")
        asyncio.create_task(run_update_price_and_notify(context, chat_id))
        return  # 안내 메시지 전송 후 즉시 반환
    except Exception as e:
        logger.error(f"일별시세 갱신 중 오류: {str(e)}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

async def run_update_price_and_notify(context, chat_id):
    try:
        response = await session.post(f"{API_URL}/admin/update_price", timeout=60) # session 사용 및 timeout 추가
        if response.status_code == 200:
            result = await response.json()
            await context.bot.send_message(
                chat_id=chat_id,
                text=(f"✅ 일별시세 갱신 완료!\n"
                      f"📊 처리된 데이터: {result['updated_count']}개\n"
                      f"⏰ 시간: {result['timestamp']}")
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ 갱신 실패: {response.status_code}")
    except Exception as e:
        logger.error(f"일별시세 갱신(비동기) 중 오류: {str(e)}")
        await context.bot.send_message(chat_id=chat_id, text=f"오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

@admin_only
async def admin_show_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """스케줄러 상태 조회 명령어"""
    import re
    try:
        # API 호출
        response = await session.get(f"{API_URL}/admin/schedule/status", timeout=10) # session 사용 및 timeout 추가
        
        if response.status_code == 200:
            result = await response.json()
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
            await update.message.reply_text(f"조회 실패: {response.status_code}", parse_mode=None)
            
    except Exception as e:
        logger.error(f"스케줄러 상태 조회 중 오류: {str(e)}")
        await update.message.reply_text(f"스케줄러 상태 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", parse_mode=None)

@admin_only
async def admin_trigger_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """특정 잡 수동 실행 명령어"""
    try:
        # 명령어에서 job_id 추출
        text = update.message.text
        parts = text.split()
        
        if len(parts) < 2:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ 사용법: /trigger_job job_id\n예시: /trigger_job update_master_job")
            return
        
        job_id = parts[1]
        
        # API 호출
        response = await session.post(f"{API_URL}/admin/schedule/trigger/{job_id}", timeout=10) # session 사용 및 timeout 추가
        
        if response.status_code == 200:
            result = await response.json()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ 잡 실행 완료!\n🔧 잡 ID: {result.get('job_id', 'N/A')}\n💬 메시지: {result.get('message', '-')}")
        elif response.status_code == 404:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ 잡을 찾을 수 없습니다: {job_id}")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ 실행 실패: {response.status_code}")
            
    except Exception as e:
        logger.error(f"잡 실행 중 오류: {str(e)}")
        await update.message.reply_text(f"잡 수동 실행 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """관리자 통계 조회 명령어"""
    try:
        # API 호출
        response = await session.get(f"{API_URL}/admin/admin_stats", timeout=10) # session 사용 및 timeout 추가
        
        if response.status_code == 200:
            stats = await response.json()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"📊 **시스템 통계**\n\n👥 사용자 수: {stats['user_count']}명\n💰 모의매매 기록: {stats['trade_count']}건\n🔮 예측 기록: {stats['prediction_count']}건", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ 조회 실패: {response.status_code}")
            
    except Exception as e:
        logger.error(f"통계 조회 중 오류: {str(e)}")
        await update.message.reply_text(f"통계 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.") 

async def admin_update_disclosure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """공시 이력 수동 갱신 명령어 (/update_disclosure [code_or_name])"""
    try:
        chat_id = update.effective_chat.id
        args = context.args
        if len(args) < 1:
            await context.bot.send_message(chat_id=chat_id, text="전체 종목 공시 이력 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다.")
            asyncio.create_task(run_update_disclosure_and_notify(context, chat_id, None))
            return  # 안내 메시지 전송 후 즉시 반환
        code_or_name = args[0]
        search_resp = await session.get(f"{API_URL}/symbols/search", params={"query": code_or_name}, timeout=10) # session 사용 및 timeout 추가
        if search_resp.status_code == 200:
            stocks = search_resp.json()
            if isinstance(stocks, list) and len(stocks) > 1:
                keyboard = []
                for stock in stocks[:10]:
                    btn_text = f"{stock.get('name','')}" # ({stock.get('symbol','')})"
                    callback_data = f"update_disclosure_{stock.get('symbol','')}"
                    keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(chat_id=chat_id, text="여러 종목이 검색되었습니다. 갱신할 종목을 선택하세요:", reply_markup=reply_markup)
                return  # 안내 메시지 전송 후 즉시 반환
            elif isinstance(stocks, list) and len(stocks) == 1:
                code_or_name = stocks[0]['symbol']
        await context.bot.send_message(chat_id=chat_id, text="공시 이력 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다.")
        asyncio.create_task(run_update_disclosure_and_notify(context, chat_id, code_or_name))
        return  # 안내 메시지 전송 후 즉시 반환
    except Exception as e:
        logger.error(f"공시 이력 갱신 중 오류: {str(e)}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

async def run_update_disclosure_and_notify(context, chat_id, code_or_name: str):
    try:
        if not code_or_name:
            response = await session.post(f"{API_URL}/admin/update_disclosure", timeout=60) # session 사용 및 timeout 추가
            if response.status_code == 200:
                result = await response.json()
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(f"✅ 전체 종목 공시 이력 갱신 완료!\n"
                          f"➕ 추가: {result.get('inserted', 0)}건\n"
                          f"⏩ 중복: {result.get('skipped', 0)}건\n"
                          f"⚠️ 에러: {len(result.get('errors', []))}건")
                )
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ 전체 처리 실패: {response.status_code} {response.text}")
            return
        response = await session.post(f"{API_URL}/admin/update_disclosure", params={"code_or_name": code_or_name}, timeout=60) # session 사용 및 timeout 추가
        if response.status_code == 200:
            result = await response.json()
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

async def update_disclosure_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """복수 종목 선택 인라인 버튼 콜백 핸들러"""
    query = update.callback_query
    await query.answer()
    try:
        data = query.data
        if data.startswith("update_disclosure_"):
            symbol = data.replace("update_disclosure_", "")
            response = await session.post(f"{API_URL}/admin/update_disclosure", params={"code_or_name": symbol}, timeout=60) # session 사용 및 timeout 추가
            if response.status_code == 200:
                result = await response.json()
                await query.edit_message_text(
                    f"✅ 공시 이력 갱신 완료!\n"
                    f"➕ 추가: {result.get('inserted', 0)}건\n"
                    f"⏩ 중복: {result.get('skipped', 0)}건\n"
                    f"⚠️ 에러: {len(result.get('errors', []))}건"
                )
            else:
                await query.edit_message_text(f"공시 이력 갱신 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
    except Exception as e:
        logger.error(f"공시 이력 갱신(버튼) 중 오류: {str(e)}")
        await query.edit_message_text(f"공시 이력 갱신(버튼) 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

@admin_only
async def test_notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        await context.bot.send_message(chat_id=chat_id, text="[테스트 알림] 공시 알림 테스트 메시지입니다.\n\n(이 메시지가 즉시 도착하면 실시간 알림 전송이 정상 동작함을 의미합니다.)")
    except Exception as e:
        await update.message.reply_text(f"테스트 알림 전송에 실패했습니다. 텔레그램 봇 설정을 확인해주세요.")

def get_admin_handler():
    return CommandHandler("admin", admin_command)