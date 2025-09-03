import pytest
from unittest.mock import MagicMock, AsyncMock
import os
import httpx

from src.bot.handlers.symbols import symbols_command, symbols_pagination_callback, symbol_info_callback, symbols_search_pagination_callback

# Mock environment variables for testing
TEST_USER_ID = 12345
TEST_ADMIN_ID = 99999 # Assuming a different ID for admin for future tests

@pytest.fixture(scope="module", autouse=True)
def setup_environment():
    """Sets up environment variables for tests."""
    os.environ["API_HOST"] = "stockeye-api"
    os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
    os.environ["TELEGRAM_ADMIN_ID"] = str(TEST_ADMIN_ID)
    os.environ["BOT_SECRET_KEY"] = "test_bot_secret_key"
    os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key"
    print(f"\n[E2E Setup] API_HOST: {os.getenv('API_HOST')}")
    print(f"[E2E Setup] TELEGRAM_ADMIN_ID: {os.getenv('TELEGRAM_ADMIN_ID')}")

@pytest.mark.asyncio
async def test_symbols_command_e2e():
    """
    Tests the /symbols command by directly calling the handler
    and interacting with the live API.
    """
    print(f"httpx version: {httpx.__version__}")
    # Create a single MagicMock for context and initialize user_data
    context_mock = MagicMock()
    context_mock.user_data = {}
    context_mock.args = [] # No arguments for /symbols command

    # Mock Update for symbols_command
    update_mock = MagicMock()
    update_mock.effective_user.id = TEST_USER_ID
    update_mock.message.reply_text = AsyncMock()

    print(f"\n[E2E] Calling /symbols command for user {TEST_USER_ID}...")
    await symbols_command(update_mock, context_mock)

    # Verify the response message
    update_mock.message.reply_text.assert_called_once()
    call_args = update_mock.message.reply_text.call_args[0][0]
    assert "[종목 목록]" in call_args
    assert "총 5개" in call_args # Assuming 5 test stocks are seeded
    assert "페이지: 1/1" in call_args
    # Assert that 5 items are listed
    listed_items = [line for line in call_args.split('\n') if line.startswith('- ')]
    assert len(listed_items) == 5

    print("[E2E] /symbols command test passed.")

    # Test symbol_info_callback (clicking a symbol button)
    print("\n[E2E] Testing symbol_info_callback (clicking a symbol button)...")
    query_mock_symbol_info = MagicMock()
    query_mock_symbol_info.data = "symbol_info_005930" # Simulate clicking Samsung Electronics button
    query_mock_symbol_info.answer = AsyncMock()
    update_mock.callback_query = query_mock_symbol_info # Attach callback_query to update_mock

    # Reset reply_text mock before this specific test to ensure it's called only once here
    update_mock.message.reply_text.reset_mock()

    await symbol_info_callback(update_mock, context_mock)

    query_mock_symbol_info.answer.assert_called_once()
    # symbol_info_callback calls symbols_search_command, which then calls reply_text
    update_mock.message.reply_text.assert_called_once()
    call_args_symbol_info = update_mock.message.reply_text.call_args[0][0]
    assert "[종목 상세]" in call_args_symbol_info
    assert "코드: 005930" in call_args_symbol_info
    assert "이름: 삼성전자" in call_args_symbol_info

    print("[E2E] Symbol_info_callback (clicking a symbol button) test passed.")
