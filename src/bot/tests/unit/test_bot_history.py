import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes
import httpx # Added this import

from src.bot.handlers import history
from src.bot.handlers.history import API_URL

@pytest.fixture
def mock_get_retry_client():
    # MOCK: src.bot.handlers.history.get_retry_client
    # get_retry_client 함수를 모의하여 실제 HTTP 요청을 보내지 않도록 합니다.
    with patch('src.bot.handlers.history.get_retry_client') as mock_client:
        # AsyncMock: 비동기 컨텍스트 매니저인 get_retry_client의 반환값을 모의합니다.
        async_mock_client = AsyncMock()
        # AsyncMock: httpx.AsyncClient의 get/post 등 비동기 메서드를 모의합니다.
        mock_method = AsyncMock()
        # __aenter__는 비동기 컨텍스트 매니저 진입 시 호출되는 메서드입니다.
        # 이 메서드가 mock_method를 반환하도록 설정하여, `async with client:` 구문에서
        # `client` 변수가 mock_method를 참조하게 합니다.
        async_mock_client.__aenter__.return_value = mock_method
        # get_retry_client() 호출 시 async_mock_client가 반환되도록 설정합니다.
        mock_client.return_value = async_mock_client
        yield mock_method

class TestBotHistory:
    """히스토리 봇 명령어 테스트"""

    def setup_method(self):
        """테스트 설정"""
        # MOCK: telegram.Update 객체
        # AsyncMock: Update 객체를 모의합니다. 비동기적으로 동작합니다.
        self.update = AsyncMock(spec=Update)
        # MOCK: telegram.ext.ContextTypes.DEFAULT_TYPE 객체
        # AsyncMock: ContextTypes.DEFAULT_TYPE 객체를 모의합니다. 비동기적으로 동작합니다.
        self.context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        # MOCK: telegram.Message 객체
        # AsyncMock: Message 객체를 모의합니다. 비동기적으로 동작합니다.
        self.update.message = AsyncMock(spec=Message)
        # AsyncMock: reply_text 메서드를 모의합니다. 비동기적으로 동작합니다.
        self.update.message.reply_text = AsyncMock()
        # MOCK: telegram.User 객체
        # MagicMock: User 객체를 모의합니다. 동기적으로 동작합니다.
        self.update.effective_user = MagicMock(spec=User)
        self.update.effective_user.id = 12345

    @pytest.mark.asyncio
    async def test_history_command_success_with_history(self, mock_get_retry_client):
        """예측 이력이 있는 경우 성공 테스트"""
        # MOCK: httpx.Response 객체
        # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
        # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
        mock_response.raise_for_status = MagicMock() 
        # json() 메서드는 동기적으로 호출되므로 MagicMock으로 설정합니다.
        mock_response.json = MagicMock(return_value={
            "history": [
                {"created_at": "2025-01-01T12:00:00", "symbol": "005930", "prediction": "상승"},
                {"created_at": "2025-01-02T12:00:00", "symbol": "035720", "prediction": "하락"}
            ]
        })
        # mock_get_retry_client.get (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
        mock_get_retry_client.get.return_value = mock_response

        await history.history_command(self.update, self.context)

        # mock_get_retry_client.get (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다.
        mock_get_retry_client.get.assert_called_once_with(f"{API_URL}/prediction/history/{self.update.effective_user.id}", timeout=10)
        
        expected_msg = "[예측 이력]\n2025-01-01T12:00:00 | 005930 | 상승\n2025-01-02T12:00:00 | 035720 | 하락\n"
        # self.update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        self.update.message.reply_text.assert_called_once_with(expected_msg)

    @pytest.mark.asyncio
    async def test_history_command_success_no_history(self, mock_get_retry_client):
        """예측 이력이 없는 경우 성공 테스트"""
        # MOCK: httpx.Response 객체
        # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
        # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
        mock_response.raise_for_status = MagicMock() 
        # json() 메서드는 동기적으로 호출되므로 MagicMock으로 설정합니다.
        mock_response.json = MagicMock(return_value={"history": []})
        # mock_get_retry_client.get (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
        mock_get_retry_client.get.return_value = mock_response

        await history.history_command(self.update, self.context)

        # self.update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        self.update.message.reply_text.assert_called_once_with("예측 이력이 없습니다.")

    @pytest.mark.asyncio
    async def test_history_command_api_request_error(self, mock_get_retry_client):
        """API 요청 실패 시 오류 메시지 테스트"""
        # mock_get_retry_client.get (AsyncMock) 호출 시 httpx.RequestError를 발생시키도록 설정합니다.
        mock_get_retry_client.get.side_effect = httpx.RequestError("API Error", request=MagicMock())

        await history.history_command(self.update, self.context)

        # self.update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        self.update.message.reply_text.assert_called_once_with(f"서버 통신 중 오류가 발생했습니다: API Error")

    @pytest.mark.asyncio
    async def test_history_command_api_http_error(self, mock_get_retry_client):
        """API가 HTTP 오류를 반환할 때 테스트"""
        # MOCK: httpx.Response 객체
        # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다.
        mock_response = AsyncMock()
        mock_response.status_code = 500
        # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다.
        mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_response))
        # mock_get_retry_client.get (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
        mock_get_retry_client.get.return_value = mock_response

        await history.history_command(self.update, self.context)
        
        # self.update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        self.update.message.reply_text.assert_called_once_with("예측 이력 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

    @pytest.mark.asyncio
    async def test_history_command_malformed_history_data(self, mock_get_retry_client):
        """이력 데이터에 예상 키가 누락된 경우 오류 처리 테스트"""
        # MOCK: httpx.Response 객체
        # AsyncMock: HTTP 응답 객체를 모의합니다. 비동기적으로 동작합니다
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다
        # MagicMock: raise_for_status 메서드를 모의합니다. 동기적으로 동작합니다
        mock_response.raise_for_status = MagicMock() 
        # json() 메서드는 동기적으로 호출되므로 MagicMock으로 설정합니다.
        # Simulate malformed data: missing 'symbol' key in one record
        mock_response.json = MagicMock(return_value={
            "history": [
                {"created_at": "2025-01-01T12:00:00", "symbol": "005930", "prediction": "상승"},
                {"created_at": "2025-01-02T12:00:00", "prediction": "하락"} # Missing 'symbol'
            ]
        })
        # mock_get_retry_client.get (AsyncMock) 호출 시 mock_response를 반환하도록 설정합니다.
        mock_get_retry_client.get.return_value = mock_response

        await history.history_command(self.update, self.context)

        # self.update.message.reply_text (AsyncMock)가 올바른 인자로 한 번 호출되었는지 확인합니다.
        self.update.message.reply_text.assert_called_once_with("예측 이력 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
