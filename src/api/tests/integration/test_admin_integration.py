import pytest
import httpx
import os
from sqlalchemy.orm import Session
from src.common.database.db_connector import SessionLocal
from src.common.models.user import User

# Configuration for the API service
API_HOST = os.getenv("API_HOST", "localhost")
API_URL = f"http://{API_HOST}:8000"
API_V1_URL = f"{API_URL}/api/v1"

# Admin Telegram ID from .env.development (ensure this matches your setup)
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
BOT_SECRET_KEY = os.getenv("BOT_SECRET_KEY")

@pytest.fixture(scope="module", autouse=True)
def setup_environment():
    """Ensure environment variables are set for the test module."""
    # These should ideally be set by docker-compose for the test runner
    # but we ensure them here for standalone test execution clarity.
    if not os.getenv("API_HOST"):
        os.environ["API_HOST"] = "stockeye-api"
    if not os.getenv("TELEGRAM_ADMIN_ID"):
        # Fallback for local testing if .env not loaded
        os.environ["TELEGRAM_ADMIN_ID"] = "7412973494" 
    if not os.getenv("BOT_SECRET_KEY"):
        # Fallback for local testing if .env not loaded
        os.environ["BOT_SECRET_KEY"] = "a_very_strong_and_secret_key_for_bot_auth_12345"
    
    global API_HOST, API_URL, API_V1_URL, TELEGRAM_ADMIN_ID, BOT_SECRET_KEY
    API_HOST = os.getenv("API_HOST")
    API_URL = f"http://{API_HOST}:8000"
    API_V1_URL = f"{API_URL}/api/v1"
    TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
    BOT_SECRET_KEY = os.getenv("BOT_SECRET_KEY")

@pytest.fixture(scope="function", autouse=True)
def clean_db_after_each_test():
    """Clean up the database after each test function."""
    db: Session = SessionLocal()
    try:
        db.query(User).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error cleaning DB: {e}")
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(User).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error cleaning DB after yield: {e}")
    finally:
        db.close()

async def get_bot_auth_token(telegram_id: str) -> str:
    """Helper to get a JWT token for a given telegram_id via the bot token endpoint."""
    headers = {"X-Bot-Secret-Key": BOT_SECRET_KEY}
    data = {"telegram_id": int(telegram_id)}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_V1_URL}/auth/bot/token", headers=headers, json=data)
        response.raise_for_status()
        return response.json()["access_token"]

async def register_telegram_user(telegram_id: str):
    """Helper to register a user via the telegram_register endpoint."""
    data = {"telegram_id": telegram_id, "is_active": True}
    async with httpx.AsyncClient() as client:
        response = await client.put(f"{API_V1_URL}/users/telegram_register", json=data)
        response.raise_for_status()
        return response.json()

@pytest.mark.asyncio
async def test_admin_user_access_admin_stats():
    """Test that an admin user can successfully access the admin_stats endpoint."""
    assert TELEGRAM_ADMIN_ID is not None, "TELEGRAM_ADMIN_ID must be set for this test."
    assert BOT_SECRET_KEY is not None, "BOT_SECRET_KEY must be set for this test."

    # 1. Register the admin user
    print(f"\nRegistering admin user: {TELEGRAM_ADMIN_ID}")
    await register_telegram_user(TELEGRAM_ADMIN_ID)

    # 2. Get JWT token for the admin user
    print(f"Getting auth token for admin user: {TELEGRAM_ADMIN_ID}")
    admin_token = await get_bot_auth_token(TELEGRAM_ADMIN_ID)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. Access admin_stats endpoint with admin token
    print("Accessing admin_stats with admin token...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_V1_URL}/admin/admin_stats", headers=admin_headers)
        print(f"Admin stats response status: {response.status_code}")
        print(f"Admin stats response body: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert "user_count" in data
        assert data["user_count"] == 1 # Only the admin user should exist

@pytest.mark.asyncio
async def test_regular_user_cannot_access_admin_stats():
    """Test that a regular user cannot access the admin_stats endpoint."""
    regular_user_id = "111222333" # A non-admin telegram ID
    assert TELEGRAM_ADMIN_ID is not None, "TELEGRAM_ADMIN_ID must be set for this test."
    assert BOT_SECRET_KEY is not None, "BOT_SECRET_KEY must be set for this test."

    # 1. Register a regular user
    print(f"\nRegistering regular user: {regular_user_id}")
    await register_telegram_user(regular_user_id)

    # 2. Get JWT token for the regular user
    print(f"Getting auth token for regular user: {regular_user_id}")
    regular_token = await get_bot_auth_token(regular_user_id)
    regular_headers = {"Authorization": f"Bearer {regular_token}"}

    # 3. Attempt to access admin_stats endpoint with regular user token
    print("Attempting to access admin_stats with regular user token...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_V1_URL}/admin/admin_stats", headers=regular_headers)
        print(f"Regular user admin stats response status: {response.status_code}")
        print(f"Regular user admin stats response body: {response.text}")
        assert response.status_code == 403 # Forbidden
        assert "Not enough permissions" in response.json()["detail"]
