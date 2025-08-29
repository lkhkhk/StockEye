import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes
import httpx # Added this import

from src.bot.handlers import history
from src.bot.handlers.history import API_URL

@pytest.fixture
def mock_get_retry_client():
    with patch('src.bot.handlers.history.get_retry_client') as mock_client:
        async_mock_client = AsyncMock()
        mock_method = AsyncMock()
        async_mock_client.__aenter__.return_value = mock_method
        mock_client.return_value = async_mock_client
        yield mock_method

class TestBotHistory:
    """히스토리 봇 명령어 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.update = AsyncMock(spec=Update)
        self.context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        self.update.message = AsyncMock(spec=Message)
        self.update.message.reply_text = AsyncMock()
        self.update.effective_user = MagicMock(spec=User)
        self.update.effective_user.id = 12345

    @pytest.mark.asyncio
    async def test_history_command_success_with_history(self, mock_get_retry_client):
        """예측 이력이 있는 경우 성공 테스트"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock() # Added to prevent RuntimeWarning
        mock_response.json.return_value = {
            "history": [
                {"created_at": "2025-01-01T12:00:00", "symbol": "005930", "prediction": "상승"},
                {"created_at": "2025-01-02T12:00:00", "symbol": "035720", "prediction": "하락"}
            ]
        }
        mock_get_retry_client.get.return_value = mock_response

        await history.history_command(self.update, self.context)

        mock_get_retry_client.get.assert_called_once_with(f"{API_URL}/prediction/history/{self.update.effective_user.id}", timeout=10)
        
        expected_msg = "[예측 이력]\n2025-01-01T12:00:00 | 005930 | 상승\n2025-01-02T12:00:00 | 035720 | 하락\n"
        self.update.message.reply_text.assert_called_once_with(expected_msg)

    @pytest.mark.asyncio
    async def test_history_command_success_no_history(self, mock_get_retry_client):
        """예측 이력이 없는 경우 성공 테스트"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock() # Added to prevent RuntimeWarning
        mock_response.json.return_value = {"history": []}
        mock_get_retry_client.get.return_value = mock_response

        await history.history_command(self.update, self.context)

        self.update.message.reply_text.assert_called_once_with("예측 이력이 없습니다.")

    @pytest.mark.asyncio
    async def test_history_command_api_request_error(self, mock_get_retry_client):
        """API 요청 실패 시 오류 메시지 테스트"""
        mock_get_retry_client.get.side_effect = httpx.RequestError("API Error", request=MagicMock())

        await history.history_command(self.update, self.context)

        self.update.message.reply_text.assert_called_once_with(f"서버 통신 중 오류가 발생했습니다: API Error")

    @pytest.mark.asyncio
    async def test_history_command_api_http_error(self, mock_get_retry_client):
        """API가 HTTP 오류를 반환할 때 테스트"""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_response))
        mock_get_retry_client.get.return_value = mock_response

        await history.history_command(self.update, self.context)
        
        self.update.message.reply_text.assert_called_once_with("예측 이력 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

    @pytest.mark.asyncio
    async def test_history_command_malformed_history_data(self, mock_get_retry_client):
        """이력 데이터에 예상 키가 누락된 경우 오류 처리 테스트"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock() # Added to prevent RuntimeWarning
        # Simulate malformed data: missing 'symbol' key in one record
        mock_response.json.return_value = {
            "history": [
                {"created_at": "2025-01-01T12:00:00", "symbol": "005930", "prediction": "상승"},
                {"created_at": "2025-01-02T12:00:00", "prediction": "하락"} # Missing 'symbol'
            ]
        }
        mock_get_retry_client.get.return_value = mock_response

        await history.history_command(self.update, self.context)

        # Expect the generic error message due to KeyError
        self.update.message.reply_text.assert_called_once_with("예측 이력 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

