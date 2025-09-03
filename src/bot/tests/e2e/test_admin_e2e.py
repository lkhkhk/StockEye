import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
import os
import logging

# Import handler functions from your bot
from src.bot.handlers.admin import admin_stats, get_auth_token
from src.bot.handlers.register import register_command
from src.common.database.db_connector import SessionLocal
from src.common.models.user import User

# Mock user and chat IDs for testing
TEST_ADMIN_ID = 7412973494
TEST_CHAT_ID = 7412973494

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module", autouse=True)
def setup_environment():
    """Sets up environment variables for tests."""
    os.environ["API_HOST"] = "stockeye-api"
    os.environ["TELEGRAM_ADMIN_ID"] = str(TEST_ADMIN_ID)
    yield
    # Clean up environment variables
    if "API_HOST" in os.environ:
        del os.environ["API_HOST"]
    if "TELEGRAM_ADMIN_ID" in os.environ:
        del os.environ["TELEGRAM_ADMIN_ID"]

@pytest_asyncio.fixture(scope="function")
async def registered_admin_user():
    """Fixture to register an admin user and clean up afterward."""
    # --- Setup: Register the admin user ---
    update_register = MagicMock()
    context_register = MagicMock()
    update_register.effective_chat.id = TEST_CHAT_ID
    update_register.message.reply_text = AsyncMock()
    
    await register_command(update_register, context_register)
    
    try:
        yield # Test runs here
    finally:
        # --- Teardown: Delete the user ---
        db = SessionLocal()
        try:
            db.query(User).filter(User.telegram_id == TEST_CHAT_ID).delete()
            db.commit()
        finally:
            db.close()

@pytest.mark.asyncio
async def test_admin_stats_e2e(registered_admin_user):
    """
    Tests the /admin_stats command to ensure it returns system statistics for an admin user.
    """
    # Mock Update and Context for admin_stats
    update = MagicMock()
    context = MagicMock()
    update.effective_user.id = TEST_ADMIN_ID
    update.effective_chat.id = TEST_CHAT_ID
    update.message.reply_text = AsyncMock()
    # This is needed for the admin_only decorator
    context.bot.send_message = AsyncMock()

    # Get token and log it
    token = await get_auth_token(TEST_ADMIN_ID)
    print(f"Auth token: {token}")

    print(f"\n[E2E] Testing /admin_stats for admin user {TEST_ADMIN_ID}...")
    await admin_stats(update, context)

    # Verify the confirmation message
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args[0][0]
    assert "📊 **시스템 통계**" in call_args
    assert "👥 사용자 수: 1명" in call_args # After registration, there should be 1 user
    assert "💰 모의매매 기록:" in call_args
    assert "🔮 예측 기록:" in call_args
    print("[E2E] /admin_stats command test passed.")
