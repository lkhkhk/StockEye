import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import os

# Import the functions to be tested
from src.bot.handlers.symbols import symbols_search_command, symbols_search_pagination_callback, PAGE_SIZE

# This test is temporary and used for debugging pagination logic.
# It mocks the API responses to control the test data.
# It is marked as skipped because it's not part of the regular e2e test suite.
@pytest.mark.skip(reason="Temporary test, used for debugging pagination logic with mocked API responses.")
@pytest.mark.asyncio
async def test_pagination_logic_temp():
    """
    Temporary test to verify pagination logic with mocked API responses.
    Simulates a search result with 25 items and checks pagination behavior.
    """
    print("\n[TEMP TEST] Testing pagination logic with mocked API responses...")

    mock_items_page1 = [{'symbol': f'SYM{i:02d}', 'name': f'Item {i:02d}'} for i in range(1, 11)]
    mock_items_page2 = [{'symbol': f'SYM{i:02d}', 'name': f'Item {i:02d}'} for i in range(11, 21)]
    mock_items_page3 = [{'symbol': f'SYM{i:02d}', 'name': f'Item {i:02d}'} for i in range(21, 26)]

    async def mock_api_search_symbols(query: str, limit: int, offset: int, auth_token: str = None) -> dict:
        if offset == 0:
            return {'items': mock_items_page1, 'total_count': 25}
        elif offset == 10:
            return {'items': mock_items_page2, 'total_count': 25}
        elif offset == 20:
            return {'items': mock_items_page3, 'total_count': 25}
        else:
            # Simulate API returning empty for out-of-bounds offset
            return {'items': [], 'total_count': 25}

    with patch('src.bot.handlers.symbols._api_search_symbols', new=mock_api_search_symbols):
        context_mock = MagicMock()
        context_mock.user_data = {}
        context_mock.bot = MagicMock() # Mock context.bot
        context_mock.bot.send_message = AsyncMock() # Ensure context.bot.send_message is AsyncMock

        update_mock = MagicMock()
        update_mock.effective_user.id = 12345 # Dummy user ID
        update_mock.message.reply_text = AsyncMock()
        # update_mock.callback_query is set to None for initial command, then re-initialized for callbacks

        query_str = "한화"

        # --- Test Scenario: Initial search command ---
        context_mock.args = [query_str]
        update_mock.callback_query = None # Simulate initial command
        await symbols_search_command(update_mock, context_mock)

        update_mock.message.reply_text.assert_called_once()
        call_args_initial = update_mock.message.reply_text.call_args[0][0]
        assert f"'{query_str}' 검색 결과 (총 25개)" in call_args_initial
        assert "페이지: 1/3" in call_args_initial
        assert "- SYM01 Item 01" in call_args_initial
        update_mock.message.reply_text.reset_mock() # Reset for next assertion

        # --- Test Scenario: Click Next (offset 10) ---
        update_mock.callback_query = MagicMock() # Re-initialize callback_query mock
        update_mock.callback_query.answer = AsyncMock()
        update_mock.callback_query.edit_message_text = AsyncMock()
        update_mock.callback_query.data = f"symbols_search_page_{query_str}_10"
        await symbols_search_pagination_callback(update_mock, context_mock)

        update_mock.callback_query.answer.assert_called_once()
        update_mock.callback_query.edit_message_text.assert_called_once()
        call_args_page2 = update_mock.callback_query.edit_message_text.call_args[0][0]
        assert f"'{query_str}' 검색 결과 (총 25개)" in call_args_page2
        assert "페이지: 2/3" in call_args_page2
        assert "- SYM11 Item 11" in call_args_page2
        update_mock.callback_query.answer.reset_mock()
        update_mock.callback_query.edit_message_text.reset_mock()

        # --- Test Scenario: Click Next (offset 20) ---
        update_mock.callback_query = MagicMock() # Re-initialize callback_query mock
        update_mock.callback_query.answer = AsyncMock()
        update_mock.callback_query.edit_message_text = AsyncMock()
        update_mock.callback_query.data = f"symbols_search_page_{query_str}_20"
        await symbols_search_pagination_callback(update_mock, context_mock)

        update_mock.callback_query.answer.assert_called_once()
        update_mock.callback_query.edit_message_text.assert_called_once()
        call_args_page3 = update_mock.callback_query.edit_message_text.call_args[0][0]
        assert f"'{query_str}' 검색 결과 (총 25개)" in call_args_page3
        assert "페이지: 3/3" in call_args_page3
        assert "- SYM21 Item 21" in call_args_page3
        update_mock.callback_query.answer.reset_mock()
        update_mock.callback_query.edit_message_text.reset_mock()

        # --- Test Scenario: Click Next (offset 30 - beyond last page) ---
        update_mock.callback_query.data = f"symbols_search_page_{query_str}_30"
        await symbols_search_pagination_callback(update_mock, context_mock)

        update_mock.callback_query.answer.assert_called_once()
        update_mock.callback_query.edit_message_text.assert_called_once()
        call_args_beyond = update_mock.callback_query.edit_message_text.call_args[0][0]
        assert f"'{query_str}' 검색 결과 (총 25개)" in call_args_beyond
        assert "페이지: 3/3" in call_args_beyond # Should still show last page
        assert "- SYM21 Item 21" in call_args_beyond # Should still show last page content

        context_mock.bot.send_message.assert_called_once_with(chat_id=update_mock.effective_chat.id, text="더 이상 결과가 없습니다.")

    print("[TEMP TEST] Pagination logic test passed.")