import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.common.models.user import User
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice
from src.common.models.prediction_history import PredictionHistory
from datetime import datetime, timedelta
from uuid import uuid4

def test_prediction_history_e2e(client: TestClient, real_db: Session):
    # 1. Setup: Insert StockMaster and DailyPrice data
    symbol = "005930"
    stock_name = "삼성전자"
    
    # Insert StockMaster data
    stock_master = StockMaster(symbol=symbol, name=stock_name, market="KOSPI")
    real_db.add(stock_master)
    real_db.commit()

    # Insert DailyPrice data (at least 20 days for prediction logic)
    today = datetime.utcnow().date()
    for i in range(40, 0, -1): # 40 days of data
        date = today - timedelta(days=i)
        daily_price = DailyPrice(
            symbol=symbol,
            date=date,
            open=10000 + i * 100,
            high=10200 + i * 100,
            low=9800 + i * 100,
            close=10100 + i * 100,
            volume=100000 + i * 1000
        )
        real_db.add(daily_price)
    real_db.commit()

    # 2. Create a test user
    unique_id = uuid4().hex
    telegram_id = int(f"123{unique_id[:7]}", 16) # Generate a unique telegram_id
    username = f"e2e_user_{unique_id}"
    password = "e2e_password"
    email = f"e2e_{unique_id}@test.com"

    # Register user (this will also create the user in DB if not exists)
    response = client.post("/api/v1/users/register", json={
        "username": username,
        "email": email,
        "password": password,
        "telegram_id": telegram_id # Pass telegram_id during registration
    })
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == username

    # 3. Test /predict command (API direct call)
    predict_response = client.post("/api/v1/predict", json={
        "symbol": symbol,
        "telegram_id": telegram_id
    })
    assert predict_response.status_code == 200
    predict_result = predict_response.json()
    assert predict_result["symbol"] == symbol
    assert "prediction" in predict_result
    assert "confidence" in predict_result
    assert "reason" in predict_result

    # Verify prediction history in DB
    user = real_db.query(User).filter(User.telegram_id == telegram_id).first()
    assert user is not None
    
    history_entry = real_db.query(PredictionHistory).filter(
        PredictionHistory.user_id == user.id,
        PredictionHistory.symbol == symbol
    ).order_by(PredictionHistory.created_at.desc()).first()

    assert history_entry is not None
    assert history_entry.user_id == user.id
    assert history_entry.symbol == symbol
    assert history_entry.prediction == predict_result["prediction"]

    print(f"Prediction history for {symbol} saved successfully for user {telegram_id}")

    # 4. Test natural language command (simulated bot call - same API endpoint)
    # Simulate another prediction for the same user/symbol
    predict_response_2 = client.post("/api/v1/predict", json={
        "symbol": symbol,
        "telegram_id": telegram_id
    })
    assert predict_response_2.status_code == 200

    # Verify that a second history entry was created
    history_entries = real_db.query(PredictionHistory).filter(
        PredictionHistory.user_id == user.id,
        PredictionHistory.symbol == symbol
    ).order_by(PredictionHistory.created_at.desc()).all()

    assert len(history_entries) == 2
    assert history_entries[0].prediction == predict_response_2.json()["prediction"]
    assert history_entries[1].prediction == predict_result["prediction"]

    print("E2E prediction history test completed successfully.")
