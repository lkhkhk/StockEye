import pytest
from pydantic import ValidationError
from src.common.schemas.predict import StockPredictionRequest, StockPredictionResponse

def test_stock_prediction_request_valid():
    # Test with only required fields
    request_data = {"symbol": "AAPL"}
    request = StockPredictionRequest(**request_data)
    assert request.symbol == "AAPL"
    assert request.telegram_id is None

    # Test with all fields
    request_data = {"symbol": "GOOG", "telegram_id": 12345}
    request = StockPredictionRequest(**request_data)
    assert request.symbol == "GOOG"
    assert request.telegram_id == 12345

def test_stock_prediction_request_missing_symbol():
    # Test missing required 'symbol'
    request_data = {"telegram_id": 12345}
    with pytest.raises(ValidationError) as exc_info:
        StockPredictionRequest(**request_data)
    assert "symbol" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)

def test_stock_prediction_response_valid():
    # Test valid response creation
    response_data = {
        "symbol": "MSFT",
        "prediction": "UP",
        "confidence": 85.5,
        "reason": "Strong earnings report"
    }
    response = StockPredictionResponse(**response_data)
    assert response.symbol == "MSFT"
    assert response.prediction == "UP"
    assert response.confidence == 85.5
    assert response.reason == "Strong earnings report"

def test_stock_prediction_response_missing_fields():
    # Test missing required 'prediction'
    response_data = {
        "symbol": "MSFT",
        "confidence": 85,
        "reason": "Strong earnings report"
    }
    with pytest.raises(ValidationError) as exc_info:
        StockPredictionResponse(**response_data)
    assert "prediction" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)

    # Test missing required 'confidence'
    response_data = {
        "symbol": "MSFT",
        "prediction": "UP",
        "reason": "Strong earnings report"
    }
    with pytest.raises(ValidationError) as exc_info:
        StockPredictionResponse(**response_data)
    assert "confidence" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)

    # Test missing required 'reason'
    response_data = {
        "symbol": "MSFT",
        "prediction": "UP",
        "confidence": 85
    }
    with pytest.raises(ValidationError) as exc_info:
        StockPredictionResponse(**response_data)
    assert "reason" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)

def test_stock_prediction_response_invalid_data_types():
    # Test invalid confidence type
    response_data = {
        "symbol": "MSFT",
        "prediction": "UP",
        "confidence": "high", # Invalid type
        "reason": "Strong earnings report"
    }
    with pytest.raises(ValidationError) as exc_info:
        StockPredictionResponse(**response_data)
    assert "confidence" in str(exc_info.value)
    assert "Input should be a valid number" in str(exc_info.value)

    # Test invalid symbol type (e.g., int instead of str)
    response_data = {
        "symbol": 123, # Invalid type
        "prediction": "UP",
        "confidence": 85,
        "reason": "Strong earnings report"
    }
    with pytest.raises(ValidationError) as exc_info:
        StockPredictionResponse(**response_data)
    assert "symbol" in str(exc_info.value)
    assert "Input should be a valid string" in str(exc_info.value)