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
    assert "총 3886개" in call_args # Updated assertion based on actual seeded data
    assert "페이지: 1/389" in call_args
    assert "- 000270 기아" in call_args
    assert "- 000660 SK하이닉스" in call_args
    assert "- 005380 현대자동차" in call_args
    assert "- 005930 삼성전자" in call_args
    assert "- 035720 카카오" in call_args
    assert "- 036720 한빛네트" in call_args
    assert "- 040130 엔플렉스" in call_args
    assert "- 055000 동서정보기술" in call_args
    assert "- 032600 애드모바일" in call_args
    assert "- 056140 리더컴" in call_args

    print("[E2E] /symbols command test passed.")

    # Test pagination (Next page)
    print("\n[E2E] Testing symbols pagination (Next page)...")
    query_mock = MagicMock()
    query_mock.data = "symbols_page_10" # Simulate clicking next page
    query_mock.answer = AsyncMock()
    query_mock.edit_message_text = AsyncMock()
    update_mock.callback_query = query_mock # Attach callback_query to update_mock

    await symbols_pagination_callback(update_mock, context_mock)

    query_mock.answer.assert_called_once()
    query_mock.edit_message_text.assert_called_once()
    call_args_next_page = query_mock.edit_message_text.call_args[0][0]
    assert "[종목 목록]" in call_args_next_page
    assert "페이지: 2/389" in call_args_next_page
    assert "- 000020 동화약품" in call_args_next_page # Assuming this is the 11th item

    print("[E2E] Symbols pagination (Next page) test passed.")

    # Test pagination (Previous page)
    print("\n[E2E] Testing symbols pagination (Previous page)...")
    query_mock.data = "symbols_page_0" # Simulate clicking previous page
    query_mock.answer = AsyncMock()
    query_mock.edit_message_text = AsyncMock()
    update_mock.callback_query = query_mock # Re-attach callback_query to update_mock

    await symbols_pagination_callback(update_mock, context_mock)

    query_mock.answer.assert_called_once()
    query_mock.edit_message_text.assert_called_once()
    call_args_prev_page = query_mock.edit_message_text.call_args[0][0]
    assert "[종목 목록]" in call_args_prev_page
    assert "페이지: 1/389" in call_args_prev_page
    assert "- 000270 기아" in call_args_prev_page # Assuming this is the 1st item

    print("[E2E] Symbols pagination (Previous page) test passed.")

    # Test symbol_info_command (search by name)
    print("\n[E2E] Testing /symbol_info command (search by name)...")
    context_mock.args = ["한화"] # Search for "한화"
    update_mock.message.reply_text = AsyncMock() # Reset mock for new command
    update_mock.callback_query = None # Ensure it's treated as a new command

    await symbols_command(update_mock, context_mock) # Call symbols_command which dispatches to symbols_search_command

    update_mock.message.reply_text.assert_called_once()
    call_args_search = update_mock.message.reply_text.call_args[0][0]
    assert "'한화' 검색 결과" in call_args_search
    assert "총 25개" in call_args_search # Assuming 25 results for "한화"
    assert "페이지: 1/3" in call_args_search # 25 items, PAGE_SIZE=10 -> 3 pages
    assert "- 000880 한화" in call_args_search # Assuming first result

    print("[E2E] /symbol_info command (search by name) test passed.")

    # Test symbol_info_command pagination (Next page for search)
    print("\n[E2E] Testing symbol_info_command pagination (Next page for search)...")
    query_mock_search = MagicMock()
    query_mock_search.data = "symbols_search_page_한화_10" # Simulate clicking next page for search
    query_mock_search.answer = AsyncMock()
    query_mock_search.edit_message_text = AsyncMock()
    update_mock.callback_query = query_mock_search # Attach callback_query to update_mock

    await symbols_search_pagination_callback(update_mock, context_mock)

    query_mock_search.answer.assert_called_once()
    query_mock_search.edit_message_text.assert_called_once()
    call_args_search_next_page = query_mock_search.edit_message_text.call_args[0][0]
    assert "'한화' 검색 결과" in call_args_search_next_page
    assert "페이지: 2/3" in call_args_search_next_page
    assert "총 25개" in call_args_search_next_page
    assert "- 000880 한화" not in call_args_search_next_page # Should not be on first page anymore

    print("[E2E] Symbol_info_command pagination (Next page for search) test passed.")

    # Test symbol_info_command pagination (Previous page for search)
    print("\n[E2E] Testing symbol_info_command pagination (Previous page for search)...")
    query_mock_search.data = "symbols_search_page_한화_0" # Simulate clicking previous page for search
    query_mock_search.answer = AsyncMock()
    query_mock_search.edit_message_text = AsyncMock()
    update_mock.callback_query = query_mock_search # Re-attach callback_query to update_mock

    await symbols_search_pagination_callback(update_mock, context_mock)

    query_mock_search.answer.assert_called_once()
    query_mock_search.edit_message_text.assert_called_once()
    call_args_search_prev_page = query_mock_search.edit_message_text.call_args[0][0]
    assert "'한화' 검색 결과" in call_args_search_prev_page
    assert "페이지: 1/3" in call_args_search_prev_page
    assert "총 25개" in call_args_search_prev_page
    assert "- 000880 한화" in call_args_search_prev_page # Should be on first page again

    print("[E2E] Symbol_info_command pagination (Previous page for search) test passed.")

    # Test symbol_info_callback (clicking a symbol button)
    print("\n[E2E] Testing symbol_info_callback (clicking a symbol button)...")
    query_mock_symbol_info = MagicMock()
    query_mock_symbol_info.data = "symbol_info_005930" # Simulate clicking Samsung Electronics button
    query_mock_symbol_info.answer = AsyncMock()
    query_mock_symbol_info.edit_message_text = AsyncMock()
    update_mock.callback_query = query_mock_symbol_info # Attach callback_query to update_mock

    await symbol_info_callback(update_mock, context_mock)

    query_mock_symbol_info.answer.assert_called_once()
    # For symbol_info_callback, it calls symbols_search_command, which then calls reply_text
    # So we need to check update_mock.message.reply_text
    update_mock.message.reply_text.assert_called_once()
    call_args_symbol_info = update_mock.message.reply_text.call_args[0][0]
    assert "[종목 상세]" in call_args_symbol_info
    assert "코드: 005930" in call_args_symbol_info
    assert "이름: 삼성전자" in call_args_symbol_info

    print("[E2E] Symbol_info_callback (clicking a symbol button) test passed.")
