import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.orm import Session
from src.api.main import app
from src.common.database.db_connector import get_db
from src.common.models.user import User
from src.common.models.simulated_trade import SimulatedTrade
from src.common.schemas.simulated_trade import SimulatedTradeItem
from src.api.routers.simulated_trade import router, get_market_data_service, get_user_service
from src.common.services.market_data_service import MarketDataService
from src.api.services.user_service import UserService
from datetime import datetime, timedelta

# Include the router in the test app
app.include_router(router)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_db_session():
    db = MagicMock(spec=Session)
    yield db
    app.dependency_overrides.clear()

@pytest.fixture
def mock_user_service():
    service = MagicMock(spec=UserService)
    yield service
    app.dependency_overrides.clear()

@pytest.fixture
def mock_market_data_service():
    service = MagicMock(spec=MarketDataService)
    yield service
    app.dependency_overrides.clear()

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    return user

# --- POST /trade/simulate tests ---

@pytest.mark.asyncio
async def test_simulate_trade_buy_success(client, mock_db_session, mock_user_service, mock_market_data_service, mock_user):
    # GIVEN
    trade_item = SimulatedTradeItem(user_id=mock_user.id, symbol="005930", trade_type="buy", price=80000.0, quantity=10)

    mock_user_service.get_user_by_id.return_value = mock_user
    mock_market_data_service.get_current_price_and_change.return_value = {"current_price": 80000.0}

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_market_data_service] = lambda: mock_market_data_service

    # WHEN
    response = client.post("/trade/simulate", json=trade_item.model_dump())

    # THEN
    assert response.status_code == 200
    assert response.json() == {"message": "모의매매 기록 완료"}
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, mock_user.id)
    mock_market_data_service.get_current_price_and_change.assert_called_once_with(trade_item.symbol, mock_db_session)
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_simulate_trade_sell_success(client, mock_db_session, mock_user_service, mock_market_data_service, mock_user):
    # GIVEN
    trade_item = SimulatedTradeItem(user_id=mock_user.id, symbol="005930", trade_type="sell", price=85000.0, quantity=10)

    mock_user_service.get_user_by_id.return_value = mock_user
    mock_market_data_service.get_current_price_and_change.return_value = {"current_price": 85000.0}

    # Mock a previous buy trade for profit/loss calculation
    mock_buy_trade = MagicMock(spec=SimulatedTrade, price=80000.0)
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_buy_trade

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_market_data_service] = lambda: mock_market_data_service

    # WHEN
    response = client.post("/trade/simulate", json=trade_item.model_dump())

    # THEN
    assert response.status_code == 200
    assert response.json() == {"message": "모의매매 기록 완료"}
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, mock_user.id)
    mock_market_data_service.get_current_price_and_change.assert_called_once_with(trade_item.symbol, mock_db_session)
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

    # Verify profit/loss calculation
    added_trade = mock_db_session.add.call_args[0][0]
    assert added_trade.profit_loss == (85000.0 - 80000.0) * 10
    assert added_trade.profit_rate == ((85000.0 - 80000.0) / 80000.0) * 100

@pytest.mark.asyncio
async def test_simulate_trade_user_not_found(client, mock_db_session, mock_user_service, mock_market_data_service):
    # GIVEN
    trade_item = SimulatedTradeItem(user_id=999, symbol="005930", trade_type="buy", price=80000.0, quantity=10)

    mock_user_service.get_user_by_id.return_value = None # User not found

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_market_data_service] = lambda: mock_market_data_service

    # WHEN
    response = client.post("/trade/simulate", json=trade_item.model_dump())

    # THEN
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, trade_item.user_id)
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

# --- GET /trade/history/{user_id} tests ---

@pytest.mark.asyncio
async def test_get_trade_history_success_with_trades(client, mock_db_session, mock_user_service, mock_user):
    # GIVEN
    mock_user_service.get_user_by_id.return_value = mock_user

    # Mock some trade history
    trade1 = MagicMock(spec=SimulatedTrade, trade_id=1, user_id=mock_user.id, symbol="005930", trade_type="buy", price=80000.0, quantity=10, trade_time=datetime.utcnow() - timedelta(days=1), profit_loss=None, profit_rate=None, current_price=80000.0)
    trade2 = MagicMock(spec=SimulatedTrade, trade_id=2, user_id=mock_user.id, symbol="005930", trade_type="sell", price=85000.0, quantity=10, trade_time=datetime.utcnow(), profit_loss=50000.0, profit_rate=6.25, current_price=85000.0)
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [trade2, trade1]

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    # WHEN
    response = client.get(f"/trade/history/{mock_user.id}")

    # THEN
    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json["trades"]) == 2
    assert response_json["statistics"]["total_trades"] == 2
    assert response_json["statistics"]["total_profit_loss"] == 50000.0
    assert response_json["statistics"]["profitable_trades"] == 1
    assert response_json["statistics"]["win_rate"] == 50.0
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, mock_user.id)

@pytest.mark.asyncio
async def test_get_trade_history_success_no_trades(client, mock_db_session, mock_user_service, mock_user):
    # GIVEN
    mock_user_service.get_user_by_id.return_value = mock_user
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [] # No trades

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    # WHEN
    response = client.get(f"/trade/history/{mock_user.id}")

    # THEN
    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json["trades"]) == 0
    assert response_json["statistics"]["total_trades"] == 0
    assert response_json["statistics"]["total_profit_loss"] == 0
    assert response_json["statistics"]["profitable_trades"] == 0
    assert response_json["statistics"]["win_rate"] == 0.0
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, mock_user.id)

@pytest.mark.asyncio
async def test_get_trade_history_user_not_found(client, mock_db_session, mock_user_service):
    # GIVEN
    mock_user_service.get_user_by_id.return_value = None # User not found

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    # WHEN
    response = client.get(f"/trade/history/999")

    # THEN
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, 999)
