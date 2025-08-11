import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes
import requests

from src.bot.handlers.natural import natural_message_handler, API_URL

class TestNaturalHandler:
    def setup_method(self):
        self.update = AsyncMock(spec=Update)
        self.context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        
        self.update.message = AsyncMock(spec=Message)
        self.update.message.reply_text = AsyncMock(return_value=None)
        
        self.update.effective_chat = MagicMock(spec=Chat)
        self.update.effective_chat.id = 12345

        self.update.effective_user = MagicMock(spec=User)
        self.update.effective_user.id = "test_user_id"

    @pytest.mark.asyncio
    @patch('requests.post')
    @patch('requests.get')
    async def test_natural_message_handler_stock_code_predict(self, mock_get, mock_post):
        """메시지에 종목 코드와 '예측' 키워드가 포함된 경우 테스트"""
        self.update.message.text = "005930 예측해줘"

        # predict mock
        mock_post_response = MagicMock(spec=requests.Response)
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            "symbol": "005930",
            "prediction": "상승",
            "reason": "이동평균선이 정배열입니다."
        }
        mock_post_response.raise_for_status.return_value = None
        mock_post.return_value = mock_post_response

        await natural_message_handler(self.update, self.context)

        # 종목코드(005930)가 있으므로 get은 호출되지 않음
        mock_get.assert_not_called()
        mock_post.assert_called_once_with(f"{API_URL}/predict", json={"symbol": "005930", "telegram_id": "test_user_id"}, timeout=10)
        self.update.message.reply_text.assert_called_once_with("[예측 결과] 005930: 상승\n사유: 이동평균선이 정배열입니다.")

    @pytest.mark.asyncio
    @patch('requests.post')
    @patch('requests.get')
    async def test_natural_message_handler_stock_name_detail(self, mock_get, mock_post):
        """메시지에 종목명과 '얼마' 키워드가 포함된 경우 테스트"""
        self.update.message.text = "삼성전자 얼마야"

        # symbols/search mock
        mock_get_response = MagicMock(spec=requests.Response)
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"items": [
            {
                "symbol": "005930",
                "name": "삼성전자",
                "market": "KOSPI"
            }
        ]}
        mock_get_response.raise_for_status.return_value = None
        mock_get.return_value = mock_get_response

        # predict mock
        mock_post_response = MagicMock(spec=requests.Response)
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            "symbol": "005930",
            "prediction": "상승",
            "reason": "이동평균선이 정배열입니다."
        }
        mock_post_response.raise_for_status.return_value = None
        mock_post.return_value = mock_post_response

        await natural_message_handler(self.update, self.context)

        mock_get.assert_called_once_with(f"{API_URL}/symbols/search", params={"query": "삼성전자 얼마야"}, timeout=10)
        mock_post.assert_called_once_with(f"{API_URL}/predict", json={"symbol": "005930", "telegram_id": "test_user_id"}, timeout=10)
        self.update.message.reply_text.assert_called_once_with("[예측 결과] 005930: 상승\n사유: 이동평균선이 정배열입니다.")

    @pytest.mark.asyncio
    @patch('requests.get')
    async def test_natural_message_handler_no_symbol_found(self, mock_get):
        """메시지에서 종목을 찾을 수 없는 경우 테스트"""
        self.update.message.text = "알 수 없는 종목"

        mock_get_response = MagicMock(spec=requests.Response)
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"items": []} # 종목 검색 결과 없음
        mock_get_response.raise_for_status.return_value = None
        mock_get.return_value = mock_get_response

        await natural_message_handler(self.update, self.context)

        # 핸들러의 로직에 따라 mock_get.call_args_list를 확인
        assert mock_get.call_count == 5
        mock_get.assert_any_call(f"{API_URL}/symbols/search", params={"query": "알 수 없는 종목"}, timeout=10)
        mock_get.assert_any_call(f"{API_URL}/symbols/search", params={"query": "알"}, timeout=10)
        mock_get.assert_any_call(f"{API_URL}/symbols/search", params={"query": "수"}, timeout=10)
        mock_get.assert_any_call(f"{API_URL}/symbols/search", params={"query": "없는"}, timeout=10)
        mock_get.assert_any_call(f"{API_URL}/symbols/search", params={"query": "종목"}, timeout=10)

        self.update.message.reply_text.assert_called_once_with("메시지에서 종목코드(6자리)나 종목명을 찾을 수 없습니다. 예: '삼성전자 얼마야', '005930 예측'")

    @pytest.mark.asyncio
    @patch('requests.post')
    @patch('requests.get')
    async def test_natural_message_handler_predict_api_failure(self, mock_get, mock_post):
        """예측 API 호출이 실패하는 경우 테스트"""
        self.update.message.text = "005930 예측"

        # predict mock (실패)
        mock_post_response = MagicMock(spec=requests.Response)
        mock_post_response.status_code = 500
        mock_post_response.text = "Internal Server Error"
        mock_post_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error", 
            response=mock_post_response
        )
        mock_post.return_value = mock_post_response

        await natural_message_handler(self.update, self.context)

        mock_get.assert_not_called()
        mock_post.assert_called_once_with(f"{API_URL}/predict", json={"symbol": "005930", "telegram_id": "test_user_id"}, timeout=10)
        self.update.message.reply_text.assert_called_once_with("예측 실패: Internal Server Error")

    @pytest.mark.asyncio
    @patch('requests.get')
    async def test_natural_message_handler_detail_api_failure(self, mock_get):
        """종목 상세 API 호출이 실패하는 경우 테스트"""
        self.update.message.text = "삼성전자"

        # symbols/search mock (첫 번째 호출은 성공, 두 번째 호출은 실패)
        mock_get_response_success = MagicMock(spec=requests.Response)
        mock_get_response_success.status_code = 200
        mock_get_response_success.json.return_value = {"items": [
            {
                "symbol": "005930",
                "name": "삼성전자",
                "market": "KOSPI"
            }
        ]}
        mock_get_response_success.raise_for_status.return_value = None
        
        mock_get_response_failure = MagicMock(spec=requests.Response)
        mock_get_response_failure.status_code = 500
        mock_get_response_failure.text = "Internal Server Error"
        mock_get_response_failure.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error",
            response=mock_get_response_failure
        )
        mock_get.side_effect = [mock_get_response_success, mock_get_response_failure]

        await natural_message_handler(self.update, self.context)

        # symbols/search가 두 번 호출되었는지 확인 (첫 번째는 종목명 검색, 두 번째는 symbol로 상세 조회)
        assert mock_get.call_count == 2
        mock_get.assert_any_call(f"{API_URL}/symbols/search", params={"query": "삼성전자"}, timeout=10) # 첫 번째 호출
        mock_get.assert_any_call(f"{API_URL}/symbols/search", params={"query": "005930"}, timeout=10) # 두 번째 호출
        self.update.message.reply_text.assert_called_once_with("종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (오류: Internal Server Error)")

    @pytest.mark.asyncio
    @patch('requests.get')
    async def test_natural_message_handler_stock_name_detail_no_predict_keyword(self, mock_get):
        """메시지에 종목명만 있고 '예측' 키워드가 없는 경우 상세 정보를 반환하는지 테스트"""
        self.update.message.text = "삼성전자"

        # symbols/search mock
        mock_get_response = MagicMock(spec=requests.Response)
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"items": [
            {
                "symbol": "005930",
                "name": "삼성전자",
                "market": "KOSPI"
            }
        ]}
        mock_get_response.raise_for_status.return_value = None
        
        # 상세 조회를 위한 두 번째 호출도 동일한 mock을 사용하도록 설정
        mock_get.return_value = mock_get_response

        await natural_message_handler(self.update, self.context)

        # symbols/search가 두 번 호출되었는지 확인 (첫 번째는 종목명 검색, 두 번째는 symbol로 상세 조회)
        assert mock_get.call_count == 2
        mock_get.assert_any_call(f"{API_URL}/symbols/search", params={"query": "삼성전자"}, timeout=10)
        mock_get.assert_any_call(f"{API_URL}/symbols/search", params={"query": "005930"}, timeout=10)
        self.update.message.reply_text.assert_called_once_with("[종목 상세]\n코드: 005930\n이름: 삼성전자\n시장: KOSPI")
