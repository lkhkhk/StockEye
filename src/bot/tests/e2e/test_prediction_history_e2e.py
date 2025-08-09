
import pytest
from unittest.mock import AsyncMock, MagicMock
import os
import httpx

from src.bot.handlers.predict import predict_command

# Mock user and chat IDs for testing
TEST_USER_ID = 12345
TEST_CHAT_ID = 12345
API_URL = f"http://stockseye-api:8000/api/v1"

@pytest.fixture(autouse=True)
def setup_environment():
    """Sets up environment variables for tests."""
    os.environ["API_HOST"] = "stockseye-api"
    yield
    # Clean up environment variables if necessary
    del os.environ["API_HOST"]

@pytest.mark.asyncio
async def test_prediction_history_e2e():
    """
    Tests that prediction history is saved correctly after a prediction command.
    """
    symbol = "005930"  # Samsung Electronics
    command_text = f"/predict {symbol}"

    # 1. Call the predict command
    update = MagicMock()
    context = MagicMock()
    update.message.text = command_text
    update.message.reply_text = AsyncMock()
    update.effective_user.id = TEST_USER_ID
    context.args = [symbol]

    print(f"\n[E2E] Calling predict command: {command_text}")
    await predict_command(update, context)

    # Verify the bot's response (optional, as prediction might fail due to lack of data)
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args[0][0]
    print(f"[E2E] Bot response: {call_args}")

    # 2. Verify prediction history in DB via API
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/prediction/history/{TEST_USER_ID}", timeout=10)
        response.raise_for_status()
        history = response.json()

        print(f"[E2E] Prediction history from API: {history}")

        assert len(history) > 0
        assert history[0]["symbol"] == symbol
        assert history[0]["user_id"] == TEST_USER_ID
        print("[E2E] Prediction history saved and retrieved successfully.")
