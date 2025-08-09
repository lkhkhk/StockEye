
import pytest
from unittest.mock import AsyncMock, MagicMock
import os
import httpx

from src.bot.handlers.natural import natural_message_handler

# Mock user and chat IDs for testing
TEST_USER_ID = 12345
TEST_CHAT_ID = 12345
API_URL = f"http://stockseye-api:8000"

@pytest.fixture(autouse=True)
def setup_environment():
    """Sets up environment variables for tests."""
    os.environ["API_HOST"] = "stockseye-api"
    yield
    # Clean up environment variables if necessary
    del os.environ["API_HOST"]

@pytest.mark.asyncio
async def test_natural_handler_stock_info_e2e():
    """
    Tests the natural message handler for stock information retrieval end-to-end.
    """
    symbol = "005930"  # Samsung Electronics
    message_text = f"{symbol} 정보"

    # Mock Update and Context
    update = MagicMock()
    context = MagicMock()
    update.message.text = message_text
    update.message.reply_text = AsyncMock()
    update.effective_user.id = TEST_USER_ID # Needed for user creation if not exists

    print(f"[E2E] Testing natural handler with message: '{message_text}'")
    await natural_message_handler(update, context)

    # Verify the response
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args[0][0]
    assert "[종목 상세]" in call_args
    assert f"코드: {symbol}" in call_args
    assert "이름: Samsung Electronics" in call_args
    print("[E2E] Natural handler stock info test passed.")

@pytest.mark.asyncio
async def test_natural_handler_prediction_e2e():
    """
    Tests the natural message handler for stock prediction end-to-end.
    """
    symbol = "005930"  # Samsung Electronics
    message_text = f"{symbol} 예측"

    # Mock Update and Context
    update = MagicMock()
    context = MagicMock()
    update.message.text = message_text
    update.message.reply_text = AsyncMock()
    update.effective_user.id = TEST_USER_ID # Needed for user creation if not exists

    print(f"[E2E] Testing natural handler with message: '{message_text}'")
    await natural_message_handler(update, context)

    # Verify the response
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args[0][0]
    assert "[예측 결과]" in call_args
    assert f"{symbol}:" in call_args
    print("[E2E] Natural handler prediction test passed.")
