import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update
from telegram.ext import ContextTypes
import httpx
import os

from src.bot.handlers.history import history_command

class TestHistoryHandler:

    @pytest.fixture
    def mock_update(self):
        update = MagicMock(spec=Update)
        update.effective_user.id = 123
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        return MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get') # Changed patch target
    async def test_history_command_success(self, mock_httpx_get, mock_update, mock_context):
        # GIVEN
        mock_response = MagicMock(spec=httpx.Response) # Put spec=httpx.Response back
        mock_response.json = AsyncMock(return_value={
            "history": [
                {"created_at": "2023-01-01", "symbol": "005930", "prediction": "상승"},
                {"created_at": "2023-01-02", "symbol": "000660", "prediction": "하락"}
            ]
        }) # Changed to directly mock .json to be an AsyncMock
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200

        mock_httpx_get.return_value = mock_response # Direct mock of httpx.AsyncClient.get

        # WHEN
        await history_command(mock_update, mock_context)

        # THEN
        mock_httpx_get.assert_called_once_with(f"http://{os.getenv('API_HOST', 'localhost')}:8000/prediction/history/123", timeout=10)
        expected_msg = "[예측 이력]\n2023-01-01 | 005930 | 상승\n2023-01-02 | 000660 | 하락\n"
        mock_update.message.reply_text.assert_called_once_with(expected_msg)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get') # Changed patch target
    async def test_history_command_empty_history(self, mock_httpx_get, mock_update, mock_context):
        # GIVEN
        mock_response = MagicMock(spec=httpx.Response) # Put spec=httpx.Response back
        mock_response.json = AsyncMock(return_value={"history": []}) # Changed to directly mock .json to be an AsyncMock
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200

        mock_httpx_get.return_value = mock_response # Direct mock of httpx.AsyncClient.get

        # WHEN
        await history_command(mock_update, mock_context)

        # THEN
        mock_httpx_get.assert_called_once_with(f"http://{os.getenv('API_HOST', 'localhost')}:8000/prediction/history/123", timeout=10)
        mock_update.message.reply_text.assert_called_once_with("예측 이력이 없습니다.")

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get') # Changed patch target
    async def test_history_command_request_error(self, mock_httpx_get, mock_update, mock_context):
        # GIVEN
        mock_httpx_get.side_effect = httpx.RequestError("Network error", request=httpx.Request("GET", "http://test.com")) # Direct side_effect

        # WHEN
        await history_command(mock_update, mock_context)

        # THEN
        mock_httpx_get.assert_called_once_with(f"http://{os.getenv('API_HOST', 'localhost')}:8000/prediction/history/123", timeout=10)
        mock_update.message.reply_text.assert_called_once_with(f"서버 통신 중 오류가 발생했습니다: Network error")

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get') # Changed patch target
    async def test_history_command_general_exception(self, mock_httpx_get, mock_update, mock_context):
        # GIVEN
        mock_httpx_get.side_effect = Exception("Something went wrong") # Direct side_effect

        # WHEN
        await history_command(mock_update, mock_context)

        # THEN
        mock_httpx_get.assert_called_once_with(f"http://{os.getenv('API_HOST', 'localhost')}:8000/prediction/history/123", timeout=10)
        mock_update.message.reply_text.assert_called_once_with("예측 이력 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")