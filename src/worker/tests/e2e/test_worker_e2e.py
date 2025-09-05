import pytest
import pytest_asyncio
import asyncio
import json
import os
import logging
import httpx
from typing import Optional
from unittest.mock import AsyncMock, MagicMock
import redis.asyncio as redis

from src.common.database.db_connector import SessionLocal
from src.common.models.user import User
from src.common.services.user_service import UserService
from src.common.schemas.user import UserCreate

# Mock user and chat IDs for testing
TEST_ADMIN_ID = 7412973494
TEST_CHAT_ID = 7412973494
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
API_HOST = os.getenv("API_HOST", "localhost")


logger = logging.getLogger(__name__)

async def get_auth_token(telegram_id: int) -> Optional[str]:
    """API로부터 해당 telegram_id의 사용자를 위한 JWT 토큰을 받아옵니다."""
    API_HOST = os.getenv("API_HOST", "localhost")
    API_URL = f"http://{API_HOST}:8000"
    API_V1_URL = f"{API_URL}/api/v1"
    BOT_SECRET_KEY = os.getenv("BOT_SECRET_KEY")
    if not BOT_SECRET_KEY:
        logger.error("BOT_SECRET_KEY가 설정되지 않았습니다. 인증 토큰을 발급할 수 없습니다.")
        return None
    
    headers = {"X-Bot-Secret-Key": BOT_SECRET_KEY}
    data = {"telegram_id": telegram_id}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{API_V1_URL}/auth/bot/token", headers=headers, json=data)
            response.raise_for_status()
            token_data = response.json()
            return token_data.get("access_token")
    except httpx.HTTPStatusError as e:
        logger.error(f"API 토큰 발급 실패: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"토큰 발급 중 예외 발생: {e}")
    return None

@pytest.fixture(scope="module", autouse=True)
def setup_environment():
    """Sets up environment variables for tests."""
    os.environ["API_HOST"] = "stockeye-api"
    os.environ["TELEGRAM_ADMIN_ID"] = str(TEST_ADMIN_ID)
    yield
    if "API_HOST" in os.environ:
        del os.environ["API_HOST"]
    if "TELEGRAM_ADMIN_ID" in os.environ:
        del os.environ["TELEGRAM_ADMIN_ID"]

@pytest_asyncio.fixture(scope="function")
async def registered_admin_user():
    """Fixture to register an admin user and clean up afterward."""
    db = SessionLocal()
    user_service = UserService()
    username = f"test_user_{TEST_CHAT_ID}"
    try:
        # Clean up user if it exists from a previous failed run
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            db.delete(existing_user)
            db.commit()

        user = user_service.create_user_from_telegram(db, telegram_id=TEST_CHAT_ID, username=username, first_name="Test", last_name="User", password="testpassword")
        yield user
    finally:
        # Final cleanup
        user_to_delete = db.query(User).filter(User.username == username).first()
        if user_to_delete:
            db.delete(user_to_delete)
            db.commit()
        db.close()

@pytest.mark.asyncio
async def test_trigger_job_e2e(registered_admin_user):
    """
    Tests triggering a job via an API call and receiving a completion notification through Redis.
    """
    API_HOST = os.getenv("API_HOST", "localhost")
    API_URL = f"http://{API_HOST}:8000"
    API_V1_URL = f"{API_URL}/api/v1"
    redis_client = await redis.from_url(f"redis://{REDIS_HOST}", decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("notifications")

    token = await get_auth_token(TEST_CHAT_ID)
    assert token is not None, "Failed to get auth token"

    headers = {"Authorization": f"Bearer {token}"}
    job_id = "update_stock_master_job"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_V1_URL}/admin/schedule/trigger/{job_id}", 
                headers=headers, 
                json={"chat_id": TEST_CHAT_ID},
                timeout=10
            )
            response.raise_for_status()

        # Wait for the completion message
        completion_message = None
        for _ in range(20): # Wait for up to 20 seconds
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                data = json.loads(message['data'])
                if "종목마스터 갱신" in data.get("text", "") and "작업 완료" in data.get("text", ""):
                    completion_message = data
                    break
            await asyncio.sleep(1)
        
        assert completion_message is not None, "Did not receive completion message from worker"
        assert completion_message['chat_id'] == TEST_CHAT_ID
        assert "✅" in completion_message['text'] or "❌" in completion_message['text']

    finally:
        await pubsub.close()
        await redis_client.close()
