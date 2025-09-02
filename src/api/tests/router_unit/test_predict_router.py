import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.routers.predict import router as predict_router, get_predict_service, get_user_service
from src.common.database.db_connector import get_db
from src.common.schemas.predict import StockPredictionRequest, StockPredictionResponse
from src.common.models.prediction_history import PredictionHistory
from src.common.models.user import User
from src.api.services.predict_service import PredictService
from src.api.services.user_service import UserService

# --- Test Setup ---

app = FastAPI()

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_predict_service():
    return MagicMock(spec=PredictService)

@pytest.fixture
def mock_user_service():
    return MagicMock(spec=UserService)

@pytest.fixture
def client(mock_db_session, mock_predict_service, mock_user_service):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_predict_service] = lambda: mock_predict_service
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.include_router(predict_router)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# --- Test Cases ---

@pytest.mark.asyncio
async def test_predict_stock_success_with_history(client, mock_db_session, mock_predict_service, mock_user_service):
    # GIVEN
    symbol = "005930"
    telegram_id = 12345
    request_data = {"symbol": symbol, "telegram_id": telegram_id}
    
    mock_prediction_result = {"prediction": "상승", "confidence": 0.8, "reason": "Good news"}
    mock_predict_service.predict_stock_movement.return_value = mock_prediction_result

    mock_user = User(id=1, telegram_id=telegram_id, username="testuser")
    mock_user_service.get_user_by_telegram_id.return_value = mock_user

    # WHEN
    response = client.post("/predict", json=request_data)

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["prediction"] == "상승"
    assert data["confidence"] == 0.8 # Assert confidence as float
    mock_predict_service.predict_stock_movement.assert_called_once_with(mock_db_session, symbol)
    mock_user_service.get_user_by_telegram_id.assert_called_once_with(mock_db_session, telegram_id)
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_predict_stock_success_no_history_no_telegram_id(client, mock_db_session, mock_predict_service, mock_user_service):
    # GIVEN
    symbol = "005930"
    request_data = {"symbol": symbol}
    
    mock_prediction_result = {"prediction": "상승", "confidence": 0.8, "reason": "Good news"}
    mock_predict_service.predict_stock_movement.return_value = mock_prediction_result

    # WHEN
    response = client.post("/predict", json=request_data)

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["prediction"] == "상승"
    assert data["confidence"] == 0.8 # Assert confidence as float
    mock_predict_service.predict_stock_movement.assert_called_once_with(mock_db_session, symbol)
    mock_user_service.get_user_by_telegram_id.assert_not_called()
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_predict_stock_success_no_history_prediction_na(client, mock_db_session, mock_predict_service, mock_user_service):
    # GIVEN
    symbol = "005930"
    telegram_id = 12345
    request_data = {"symbol": symbol, "telegram_id": telegram_id}
    
    mock_prediction_result = {"prediction": "N/A", "confidence": 0.0, "reason": "No data"}
    mock_predict_service.predict_stock_movement.return_value = mock_prediction_result

    # WHEN
    response = client.post("/predict", json=request_data)

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["prediction"] == "N/A"
    assert data["confidence"] == 0.0 # Assert confidence as float
    mock_predict_service.predict_stock_movement.assert_called_once_with(mock_db_session, symbol)
    mock_user_service.get_user_by_telegram_id.assert_not_called()
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_predict_stock_predict_service_exception(client, mock_db_session, mock_predict_service):
    # GIVEN
    symbol = "005930"
    request_data = {"symbol": symbol}
    
    mock_predict_service.predict_stock_movement.side_effect = Exception("Prediction error")

    # WHEN
    response = client.post("/predict", json=request_data)

    # THEN
    assert response.status_code == 500
    assert response.json()["detail"] == "An error occurred during prediction."
    mock_predict_service.predict_stock_movement.assert_called_once_with(mock_db_session, symbol)

@pytest.mark.asyncio
async def test_predict_stock_user_service_exception(client, mock_db_session, mock_predict_service, mock_user_service):
    # GIVEN
    symbol = "005930"
    telegram_id = 12345
    request_data = {"symbol": symbol, "telegram_id": telegram_id}
    
    mock_prediction_result = {"prediction": "상승", "confidence": 0.8, "reason": "Good news"}
    mock_predict_service.predict_stock_movement.return_value = mock_prediction_result

    mock_user_service.get_user_by_telegram_id.side_effect = Exception("User service error")

    # WHEN
    response = client.post("/predict", json=request_data)

    # THEN
    assert response.status_code == 200 # Prediction should still be returned
    data = response.json()
    assert data["symbol"] == symbol
    assert data["prediction"] == "상승"
    assert data["confidence"] == 0.8 # Assert confidence as float
    mock_predict_service.predict_stock_movement.assert_called_once_with(mock_db_session, symbol)
    mock_user_service.get_user_by_telegram_id.assert_called_once_with(mock_db_session, telegram_id)
    mock_db_session.add.assert_not_called() # History should not be added
    mock_db_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_predict_stock_new_user(client, mock_db_session, mock_predict_service, mock_user_service):
    # GIVEN
    symbol = "005930"
    telegram_id = 12345
    request_data = {"symbol": symbol, "telegram_id": telegram_id}
    
    mock_prediction_result = {"prediction": "상승", "confidence": 0.8, "reason": "Good news"}
    mock_predict_service.predict_stock_movement.return_value = mock_prediction_result

    mock_user_service.get_user_by_telegram_id.return_value = None
    mock_new_user = User(id=2, telegram_id=telegram_id, username=f"tg_{telegram_id}")
    mock_user_service.create_user_from_telegram.return_value = mock_new_user

    # WHEN
    response = client.post("/predict", json=request_data)

    # THEN
    assert response.status_code == 200
    mock_user_service.get_user_by_telegram_id.assert_called_once_with(mock_db_session, telegram_id)
    mock_user_service.create_user_from_telegram.assert_called_once()
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    
    # Check that the correct user_id was used for the prediction history
    call_args = mock_db_session.add.call_args[0]
    assert len(call_args) > 0
    prediction_history_instance = call_args[0]
    assert isinstance(prediction_history_instance, PredictionHistory)
    assert prediction_history_instance.user_id == mock_new_user.id
    assert prediction_history_instance.symbol == symbol
    assert prediction_history_instance.prediction == "상승"
