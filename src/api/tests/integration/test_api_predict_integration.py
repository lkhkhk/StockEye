import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src.api.tests.helpers import create_test_user
from src.common.models.prediction_history import PredictionHistory
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice

@pytest.fixture(scope="function")
def setup_predict_integration_test_data(real_db: Session):
    """Set up data for predict integration test."""
    # Clean up previous data
    real_db.query(PredictionHistory).delete()
    real_db.query(DailyPrice).delete()
    real_db.query(StockMaster).filter(StockMaster.symbol == "005930").delete()
    real_db.commit()

    # Create stock master data
    stock_master = StockMaster(symbol="005930", name="삼성전자", market="KOSPI")
    real_db.add(stock_master)
    real_db.commit()

    # Create daily price data for the last 40 days
    today = datetime.utcnow().date()
    for i in range(40, 0, -1):
        date = today - timedelta(days=i)
        daily_price = DailyPrice(
            symbol="005930",
            date=date,
            open=70000 + i * 100,
            high=71000 + i * 100,
            low=69000 + i * 100,
            close=70500 + i * 100,
            volume=1000000 + i * 1000,
        )
        real_db.add(daily_price)
    real_db.commit()

def test_predict_api_success_and_history_creation(client: TestClient, real_db: Session, setup_predict_integration_test_data):
    """
    Test the /api/v1/predict endpoint for a successful prediction and history creation.
    """
    # Given
    telegram_id = 98765
    user = create_test_user(real_db, telegram_id=telegram_id)
    symbol = "005930"

    # When
    response = client.post("/api/v1/predict", json={"symbol": symbol, "telegram_id": telegram_id})

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert "prediction" in data
    assert "confidence" in data
    assert "reason" in data

    # Verify history
    history = real_db.query(PredictionHistory).filter_by(user_id=user.id, symbol=symbol).first()
    assert history is not None
    assert history.prediction == data["prediction"]