import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.common.database.db_connector import get_db
from src.common.models.user import User
from src.common.models.price_alert import PriceAlert
from src.common.models.stock_master import StockMaster
from src.common.utils.password_utils import get_password_hash

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def db_session(real_db):
    yield real_db

@pytest.fixture(scope="function", autouse=True)
def override_get_db_dependency(db_session: Session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_price_alerts_includes_stock_name_and_change_percent(client: TestClient, db_session: Session):
    # Given: User, Stock, and Alert
    # Create User
    user = User(username="test_alert_user", email="alert@test.com", hashed_password=get_password_hash("password"), role="user")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Create Stock
    symbol = "005930"
    stock_name = "Samsung Electronics"
    stock = db_session.query(StockMaster).filter_by(symbol=symbol).first()
    if not stock:
        stock = StockMaster(symbol=symbol, name=stock_name, market="KOSPI")
        db_session.add(stock)
        db_session.commit()
    
    # Create Alert
    alert = PriceAlert(
        user_id=user.id,
        symbol=symbol,
        target_price=80000.0,
        condition="gte",
        change_percent=5.0,
        change_type="up"
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    
    # Login to get token
    login_response = client.post("/api/v1/users/login", json={"username": "test_alert_user", "password": "password"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # When: Get Alerts
    response = client.get("/api/v1/price-alerts/", headers=headers)
    
    # Then: Verify Response
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) >= 1
    
    target_alert = next((a for a in alerts if a["id"] == alert.id), None)
    assert target_alert is not None
    assert target_alert["symbol"] == symbol
    assert target_alert["change_percent"] == 5.0
    assert target_alert["stock_name"] == stock.name # This is what we added!
