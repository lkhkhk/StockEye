import pytest
from unittest.mock import MagicMock, AsyncMock
import os
import httpx
import asyncio # Import asyncio for sleep

from src.bot.handlers.symbols import symbols_command, symbol_info_callback

# Mock environment variables for testing
TEST_USER_ID = 12345
TEST_ADMIN_ID = 99999 # Assuming a different ID for admin for future tests

@pytest.fixture(scope="module", autouse=True)
async def setup_environment():
    """Sets up environment variables and seeds controlled test data for tests."""
    os.environ["API_HOST"] = "stockeye-api"
    os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
    os.environ["TELEGRAM_ADMIN_ID"] = str(TEST_ADMIN_ID)
    os.environ["BOT_SECRET_KEY"] = "test_bot_secret_key"
    os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key"
    print(f"\n[E2E Setup] API_HOST: {os.getenv('API_HOST')}\n")

    async with httpx.AsyncClient() as client:
        # Call the reset-database endpoint to ensure a clean state
        print("[E2E Setup] Calling reset-database endpoint...")
        try:
            response = await client.post(f"http://{os.getenv('API_HOST')}:8000/api/v1/admin/debug/reset-database", timeout=20)
            response.raise_for_status()
            print(f"[E2E Setup] Database reset and seeded: {response.json()}")
        except httpx.RequestError as e:
            pytest.fail(f"API 서버 연결 실패: {e}. 테스트를 진행할 수 없습니다.")
        except httpx.HTTPStatusError as e:
            pytest.fail(f"DB 초기화 실패: {e.response.status_code} - {e.response.text}")

    yield
    
    # Teardown (optional, as DB is reset at start of module)
    print("\n--- E2E 테스트 환경 설정 종료 ---")

@pytest.mark.asyncio
async def test_symbols_list_and_info_e2e():
    """
    Tests the /symbols command and symbol_info_callback for a clean E2E flow.
    """
    # 1. Test /symbols command
    context_mock = MagicMock()
    context_mock.user_data = {}
    context_mock.args = [] # No arguments for /symbols command

    update_mock = MagicMock()
    update_mock.effective_user.id = TEST_USER_ID
    update_mock.message.reply_text = AsyncMock()

    print(f"\n[E2E] Calling /symbols command for user {TEST_USER_ID}...")
    await symbols_command(update_mock, context_mock)

    # Verify the response message for /symbols
    update_mock.message.reply_text.assert_called_once()
    call_args = update_mock.message.reply_text.call_args[0][0]
    assert "[종목 목록]" in call_args
    assert "총 5개" in call_args # Asserting based on controlled, seeded data
    assert "페이지: 1/1" in call_args
    listed_items = [line for line in call_args.split('\n') if line.startswith('- ')]
    assert len(listed_items) == 5
    print("[E2E] /symbols command test passed.")

    # 2. Test symbol_info_callback (clicking a symbol button)
    print("\n[E2E] Testing symbol_info_callback (clicking a symbol button)...")
    query_mock_symbol_info = MagicMock()
    query_mock_symbol_info.data = "symbol_info_005930" # Simulate clicking Samsung Electronics
    query_mock_symbol_info.answer = AsyncMock()
    update_mock.callback_query = query_mock_symbol_info
    update_mock.message = query_mock_symbol_info.message # CallbackQuery has a message attribute
    update_mock.message.reply_text = AsyncMock() # Reset mock for the new reply

    await symbol_info_callback(update_mock, context_mock)

    query_mock_symbol_info.answer.assert_called_once()
    update_mock.message.reply_text.assert_called_once()
    call_args_symbol_info = update_mock.message.reply_text.call_args[0][0]
    assert "[종목 상세]" in call_args_symbol_info
    assert "코드: 005930" in call_args_symbol_info
    assert "이름: 삼성전자" in call_args_symbol_info
    print("[E2E] symbol_info_callback test passed.")

@pytest.mark.asyncio
async def test_symbols_search_e2e():
    """
    Tests the /symbols [keyword] command for a clean E2E flow.
    """
    # 1. Test /symbols [keyword] command
    context_mock = MagicMock()
    context_mock.user_data = {}
    context_mock.args = ["삼성"] # Search for a stock

    update_mock = MagicMock()
    update_mock.effective_user.id = TEST_USER_ID
    update_mock.message.reply_text = AsyncMock()

    print(f"\n[E2E] Calling /symbols search for user {TEST_USER_ID} with keyword '삼성'...")
    await symbols_command(update_mock, context_mock)

    # Verify the response message for the search
    update_mock.message.reply_text.assert_called_once()
    call_args = update_mock.message.reply_text.call_args[0][0]
    assert "'삼성' 검색 결과" in call_args
    assert "총 1개" in call_args # Expecting only '삼성전자' from seeded data
    assert "페이지: 1/1" in call_args
    assert "- 005930 삼성전자" in call_args
    print("[E2E] /symbols search test passed.")