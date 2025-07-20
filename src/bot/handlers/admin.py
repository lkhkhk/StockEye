import os
import requests
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import logging

logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL", "http://api_service:8000")

ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "")

ADMIN_COMMANDS_TEXT = (
    "[관리자 전용 명령어 안내]\n"
    "- /admin_stats : 전체 통계 조회\n"
    "- /update_master : 종목마스터 갱신(초기 적재/갱신 겸용)\n"
    "- /update_price : 일별시세 갱신\n"
    "- /show_schedules : 스케줄러 상태 조회\n"
    "- /trigger_job [job_id] : 특정 잡 수동 실행\n"
    "\n"
    "초기 적재와 갱신은 /update_master 한 번으로 모두 처리됩니다.\n"
    "(종목이 없으면 신규 등록, 있으면 갱신)\n"
    "\n"
    "관리자 외 사용자는 접근할 수 없습니다."
)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id == ADMIN_ID:
        await update.message.reply_text(ADMIN_COMMANDS_TEXT)
    else:
        await update.message.reply_text("관리자 전용 명령어입니다.")

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(f"{API_URL}/health")
        response.raise_for_status()
        data = response.json()
        await update.message.reply_text(f"서비스 상태: {data.get('status', 'unknown')}")
    except Exception as e:
        await update.message.reply_text(f"헬스체크 실패: {e}")

async def admin_update_master(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """종목마스터 갱신 명령어"""
    try:
        # API 호출
        response = requests.post("http://api:8000/admin/update_master")
        
        if response.status_code == 200:
            result = response.json()
            await update.message.reply_text(
                f"✅ 종목마스터 갱신 완료!\n"
                f"📊 처리된 종목: {result['updated_count']}개\n"
                f"⏰ 시간: {result['timestamp']}"
            )
        else:
            await update.message.reply_text(f"❌ 갱신 실패: {response.status_code}")
            
    except Exception as e:
        logger.error(f"종목마스터 갱신 중 오류: {str(e)}")
        await update.message.reply_text(f"❌ 서버 오류: {str(e)}")

async def admin_update_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """일별시세 갱신 명령어"""
    try:
        # API 호출
        response = requests.post("http://api:8000/admin/update_price")
        
        if response.status_code == 200:
            result = response.json()
            await update.message.reply_text(
                f"✅ 일별시세 갱신 완료!\n"
                f"📊 처리된 데이터: {result['updated_count']}개\n"
                f"⏰ 시간: {result['timestamp']}"
            )
        else:
            await update.message.reply_text(f"❌ 갱신 실패: {response.status_code}")
            
    except Exception as e:
        logger.error(f"일별시세 갱신 중 오류: {str(e)}")
        await update.message.reply_text(f"❌ 서버 오류: {str(e)}")

async def admin_show_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """스케줄러 상태 조회 명령어"""
    import re
    try:
        # API 호출
        response = requests.get("http://api:8000/admin/schedule/status")
        
        if response.status_code == 200:
            result = response.json()
            status = result['status']
            
            message = "스케줄러 상태\n\n"
            message += f"실행 상태: {'실행중' if status['scheduler_running'] else '중지'}\n"
            message += f"등록된 잡: {status['job_count']}개\n\n"
            
            for job in status['jobs']:
                message += f"잡 ID: {job['id']}\n"
                message += f"  - 다음 실행: {job['next_run_time'] or '없음'}\n"
                message += f"  - 트리거: {job['trigger']}\n\n"
            # 한글, 영문, 숫자, 공백, :, ., -, \n만 허용 (이외 모두 제거)
            message = re.sub(r'[^\w\sㄱ-ㅎ가-힣0-9:\.\-\n]', '', message)
            # 연속된 줄바꿈 2개까지만 허용
            message = re.sub(r'\n{3,}', '\n\n', message)
            # 메시지 길이 제한 (4000자 이하)
            max_len = 4000
            for i in range(0, len(message), max_len):
                logger.info(f"[admin_show_schedules] 전송 메시지: {message[i:i+max_len]}")
                await update.message.reply_text(message[i:i+max_len], parse_mode=None)
        else:
            await update.message.reply_text(f"조회 실패: {response.status_code}", parse_mode=None)
            
    except Exception as e:
        logger.error(f"스케줄러 상태 조회 중 오류: {str(e)}")
        await update.message.reply_text(f"서버 오류: {str(e)}", parse_mode=None)

async def admin_trigger_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """특정 잡 수동 실행 명령어"""
    try:
        # 명령어에서 job_id 추출
        text = update.message.text
        parts = text.split()
        
        if len(parts) < 2:
            await update.message.reply_text(
                "❌ 사용법: /trigger_job job_id\n"
                "예시: /trigger_job update_master_job"
            )
            return
        
        job_id = parts[1]
        
        # API 호출
        response = requests.post(f"http://api:8000/admin/schedule/trigger/{job_id}")
        
        if response.status_code == 200:
            result = response.json()
            await update.message.reply_text(
                f"✅ 잡 실행 완료!\n"
                f"🔧 잡 ID: {result['job_id']}\n"
                f"⏰ 시간: {result['timestamp']}"
            )
        elif response.status_code == 404:
            await update.message.reply_text(f"❌ 잡을 찾을 수 없습니다: {job_id}")
        else:
            await update.message.reply_text(f"❌ 실행 실패: {response.status_code}")
            
    except Exception as e:
        logger.error(f"잡 실행 중 오류: {str(e)}")
        await update.message.reply_text(f"❌ 서버 오류: {str(e)}")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """관리자 통계 조회 명령어"""
    try:
        # API 호출
        response = requests.get("http://api:8000/admin/admin_stats")
        
        if response.status_code == 200:
            stats = response.json()
            await update.message.reply_text(
                f"📊 **시스템 통계**\n\n"
                f"👥 사용자 수: {stats['user_count']}명\n"
                f"💰 모의매매 기록: {stats['trade_count']}건\n"
                f"🔮 예측 기록: {stats['prediction_count']}건"
            , parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ 조회 실패: {response.status_code}")
            
    except Exception as e:
        logger.error(f"통계 조회 중 오류: {str(e)}")
        await update.message.reply_text(f"❌ 서버 오류: {str(e)}") 

def get_admin_handler():
    return CommandHandler("admin", admin_command) 