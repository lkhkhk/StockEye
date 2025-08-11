import pytest
import requests
from unittest.mock import AsyncMock, patch, Mock
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.handlers.predict import predict_command

@pytest.mark.asyncio
async def test_predict_command_success():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_response = AsyncMock(status_code=200, ok=True)
    mock_response.json = Mock(return_value={"prediction": "상승", "reason": "기술적 지표 분석 결과"})
    mock_response.raise_for_status.return_value = None

    with patch('src.bot.handlers.predict.session.post', return_value=mock_response) as mock_post:
        await predict_command(update, context)

        mock_post.assert_called_once_with(
            "http://stockeye-api:8000/predict",
            json={"symbol": "005930"},
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "[예측 결과] 005930: 상승\n사유: 기술적 지표 분석 결과"
        )

@pytest.mark.asyncio
async def test_predict_command_no_symbol():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []

    with patch('src.bot.handlers.predict.session.post') as mock_post:
        await predict_command(update, context)

        mock_post.assert_not_called()
        update.message.reply_text.assert_called_once_with(
            "사용법: /predict [종목코드] 예: /predict 005930"
        )

@pytest.mark.asyncio
async def test_predict_command_api_error():
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("API Error")

    with patch('src.bot.handlers.predict.session.post', return_value=mock_response) as mock_post:
        await predict_command(update, context)

        mock_post.assert_called_once_with(
            "http://stockeye-api:8000/predict",
            json={"symbol": "005930"},
            timeout=10
        )
        update.message.reply_text.assert_called_once_with(
            "주가 예측 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )
