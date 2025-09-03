from functools import wraps
import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.common.utils.http_client import get_retry_client
import os

logger = logging.getLogger(__name__)

API_HOST = os.getenv("API_HOST", "localhost")
API_URL = f"http://{API_HOST}:8000"
API_V1_URL = f"{API_URL}/api/v1"
TELEGRAM_USER_PASSWORD = "telegram_user_password"

def ensure_user_registered(func):
    """
    핸들러 실행 전에 사용자가 DB에 등록되었는지 확인하고, 없으면 등록합니다.
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update.effective_user:
            return

        user_id = update.effective_user.id
        try:
            async with get_retry_client() as client:
                # is_active=True로 항상 활성 상태를 보장
                payload = {"telegram_id": str(user_id), "is_active": True}
                response = await client.put(f"{API_V1_URL}/users/telegram_register", json=payload)
                
                if response.status_code not in [200, 201]: # 200 OK or 201 Created
                    logger.warning(f"사용자 등록/확인 API 호출 실패: {response.status_code} - {response.text}")
                else:
                    logger.debug(f"사용자 등록/확인 성공: telegram_id={user_id}")
                    
                    # 사용자 등록/확인 후 로그인하여 토큰 발급
                    login_payload = {"username": f"tg_{user_id}", "password": TELEGRAM_USER_PASSWORD}
                    login_response = await client.post(f"{API_V1_URL}/users/login", json=login_payload)
                    
                    if login_response.status_code == 200:
                        token_data = login_response.json()
                        context.user_data['auth_token'] = token_data['access_token']
                        logger.debug(f"사용자 {user_id} 토큰 발급 성공")
                    else:
                        logger.warning(f"사용자 {user_id} 토큰 발급 실패: {login_response.status_code} - {login_response.text}")

        except Exception as e:
            logger.error(f"사용자 등록/확인 중 예외 발생:", exc_info=True)
        
        # 원래 핸들러 함수 실행
        return await func(update, context, *args, **kwargs)
    
    return wrapped