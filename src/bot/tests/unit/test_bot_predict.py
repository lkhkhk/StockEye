import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.handlers.predict import predict_command

@pytest.mark.asyncio
@patch('src.bot.handlers.predict.get_retry_client')
@patch('src.bot.handlers.predict.StockMasterService')
@patch('src.bot.handlers.predict.get_db')
async def test_predict_command_with_stock_name(mock_get_db, mock_stock_master_service, mock_get_retry_client):
    """/predict 명령어에 종목 이름 사용 시 성공 테스트"""
    # Given
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    update.effective_user.id = 12345
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["한화오션"]

    mock_db_session = MagicMock()
    db_gen = (i for i in [mock_db_session])
    mock_get_db.return_value = db_gen

    mock_stock = MagicMock()
    mock_stock.symbol = '042600'
    mock_stock.name = '한화오션'
    mock_stock_instance = mock_stock_master_service.return_value
    mock_stock_instance.get_stock_by_name.return_value = mock_stock

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"prediction": "상승", "reason": "실적 개선"}
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response
    mock_get_retry_client.return_value.__aenter__.return_value = mock_client

    # When
    await predict_command(update, context)

    # Then
    mock_stock_instance.get_stock_by_name.assert_called_once_with("한화오션", mock_db_session)
    mock_client.post.assert_awaited_once_with(
        "/api/v1/predict",
        json={"symbol": "042600", "telegram_id": "12345"}
    )
    update.message.reply_text.assert_awaited_once_with(
        "[예측 결과] 한화오션(042600): 상승\n사유: 실적 개선"
    )

@pytest.mark.asyncio
@patch('src.bot.handlers.predict.get_retry_client')
@patch('src.bot.handlers.predict.StockMasterService')
@patch('src.bot.handlers.predict.get_db')
async def test_predict_command_success_with_symbol(mock_get_db, mock_stock_master_service, mock_get_retry_client):
    """/predict 명령어 성공 테스트"""
    # Given: 테스트를 위한 Mock 객체 설정
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    update.effective_user.id = 12345
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_db_session = MagicMock()
    db_gen = (i for i in [mock_db_session])
    mock_get_db.return_value = db_gen

    mock_stock = MagicMock()
    mock_stock.symbol = '005930'
    mock_stock.name = '삼성전자'
    mock_stock_instance = mock_stock_master_service.return_value
    mock_stock_instance.get_stock_by_symbol.return_value = mock_stock


    # MOCK: httpx.Response 객체
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"prediction": "상승", "reason": "기술적 지표 분석 결과"}
    mock_response.raise_for_status.return_value = None

    # MOCK: httpx.AsyncClient 객체
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response
    
    mock_get_retry_client.return_value.__aenter__.return_value = mock_client

    # When: 핸들러 실행
    await predict_command(update, context)

    # Then: Mock 객체들이 예상대로 호출되었는지 검증
    mock_get_retry_client.assert_called_once()
    mock_client.post.assert_awaited_once_with(
        "/api/v1/predict",
        json={"symbol": "005930", "telegram_id": "12345"}
    )
    update.message.reply_text.assert_awaited_once_with(
        "[예측 결과] 삼성전자(005930): 상승\n사유: 기술적 지표 분석 결과"
    )

@pytest.mark.asyncio
async def test_predict_command_no_symbol():
    """/predict 명령어에 종목 코드가 없는 경우 테스트"""
    # Given
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []

    # When
    await predict_command(update, context)

    # Then
    update.message.reply_text.assert_called_once_with(
        "사용법: /predict [종목명 또는 종목코드]"
    )

@pytest.mark.asyncio
@patch('src.bot.handlers.predict.get_retry_client')
@patch('src.bot.handlers.predict.StockMasterService')
@patch('src.bot.handlers.predict.get_db')
async def test_predict_command_api_error(mock_get_db, mock_stock_master_service, mock_get_retry_client):
    """API가 HTTP 오류를 반환하는 경우 테스트"""
    # Given
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    update.effective_user.id = 12345
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_db_session = MagicMock()
    db_gen = (i for i in [mock_db_session])
    mock_get_db.return_value = db_gen

    mock_stock = MagicMock()
    mock_stock.symbol = '005930'
    mock_stock.name = '삼성전자'
    mock_stock_instance = mock_stock_master_service.return_value
    mock_stock_instance.get_stock_by_symbol.return_value = mock_stock

    # MOCK: httpx.Response 객체
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_response
    )

    # MOCK: httpx.AsyncClient 객체
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response
    mock_get_retry_client.return_value.__aenter__.return_value = mock_client

    # When
    await predict_command(update, context)

    # Then
    update.message.reply_text.assert_awaited_once_with(
        f"주가 예측 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (오류 코드: 500)"
    )

@pytest.mark.asyncio
@patch('src.bot.handlers.predict.get_retry_client')
@patch('src.bot.handlers.predict.StockMasterService')
@patch('src.bot.handlers.predict.get_db')
async def test_predict_command_network_error(mock_get_db, mock_stock_master_service, mock_get_retry_client):
    """네트워크 오류가 발생하는 경우 테스트"""
    # Given
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    update.effective_user.id = 12345
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["005930"]

    mock_db_session = MagicMock()
    db_gen = (i for i in [mock_db_session])
    mock_get_db.return_value = db_gen

    mock_stock = MagicMock()
    mock_stock.symbol = '005930'
    mock_stock.name = '삼성전자'
    mock_stock_instance = mock_stock_master_service.return_value
    mock_stock_instance.get_stock_by_symbol.return_value = mock_stock

    # MOCK: httpx.AsyncClient 객체
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.RequestError("Network Error", request=MagicMock())
    mock_get_retry_client.return_value.__aenter__.return_value = mock_client

    # When
    await predict_command(update, context)

    # Then
    update.message.reply_text.assert_awaited_once_with(
        "주가 예측 중 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    )

@pytest.mark.asyncio
@patch('src.bot.handlers.predict.StockMasterService')
@patch('src.bot.handlers.predict.get_db')
async def test_predict_command_stock_not_found(mock_get_db, mock_stock_master_service):
    """DB에서 종목을 찾을 수 없는 경우 테스트"""
    # Given
    update = AsyncMock(spec=Update)
    update.message.reply_text = AsyncMock()
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["없는종목"]

    mock_db_session = MagicMock()
    db_gen = (i for i in [mock_db_session])
    mock_get_db.return_value = db_gen

    mock_stock_instance = mock_stock_master_service.return_value
    mock_stock_instance.get_stock_by_name.return_value = None

    # When
    await predict_command(update, context)

    # Then
    mock_stock_instance.get_stock_by_name.assert_called_once_with("없는종목", mock_db_session)
    update.message.reply_text.assert_awaited_once_with(
        "'없는종목'에 해당하는 종목을 찾을 수 없습니다."
    )
