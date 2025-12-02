import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.orm import Session
from src.api.main import app
from src.common.database.db_connector import get_db
from src.common.models.user import User
from src.common.models.stock_master import StockMaster
from src.common.models.watchlist import Watchlist
from src.api.routers.watchlist import router, get_user_service, get_stock_master_service
from src.common.schemas.watchlist import WatchlistCreate, Watchlist as WatchlistSchema
from src.common.services.user_service import UserService
from src.common.services.stock_master_service import StockMasterService

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
def mock_stock_master_service():
    service = MagicMock(spec=StockMasterService)
    yield service
    app.dependency_overrides.clear()

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    return user

@pytest.fixture
def mock_stock():
    stock = MagicMock(spec=StockMaster)
    stock.symbol = "005930"
    stock.name = "삼성전자"
    return stock

# --- POST /watchlist/add tests ---

@pytest.mark.asyncio
async def test_add_to_watchlist_success(client, mock_db_session, mock_user_service, mock_stock_master_service, mock_user, mock_stock):
    # GIVEN
    watchlist_item = {"user_id": mock_user.id, "symbol": mock_stock.symbol}

    mock_user_service.get_user_by_id.return_value = mock_user
    mock_stock_master_service.get_stock_by_symbol.return_value = mock_stock
    mock_db_session.query.return_value.filter.return_value.first.return_value = None # Not in watchlist yet

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_stock_master_service] = lambda: mock_stock_master_service

    # WHEN
    response = client.post("/watchlist/add", json=watchlist_item)

    # THEN
    assert response.status_code == 200
    assert response.json() == {"message": "종목이 관심 목록에 추가되었습니다."}
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, mock_user.id)
    mock_stock_master_service.get_stock_by_symbol.assert_called_once_with(mock_stock.symbol, mock_db_session)
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_add_to_watchlist_user_not_found(client, mock_db_session, mock_user_service, mock_stock_master_service, mock_stock):
    # GIVEN
    watchlist_item = {"user_id": 999, "symbol": mock_stock.symbol}

    mock_user_service.get_user_by_id.return_value = None # User not found

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_stock_master_service] = lambda: mock_stock_master_service

    # WHEN
    response = client.post("/watchlist/add", json=watchlist_item)

    # THEN
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, 999)
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_add_to_watchlist_stock_not_found(client, mock_db_session, mock_user_service, mock_stock_master_service, mock_user):
    # GIVEN
    watchlist_item = {"user_id": mock_user.id, "symbol": "NONEXIST"}

    mock_user_service.get_user_by_id.return_value = mock_user
    mock_stock_master_service.get_stock_by_symbol.return_value = None # Stock not found

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_stock_master_service] = lambda: mock_stock_master_service

    # WHEN
    response = client.post("/watchlist/add", json=watchlist_item)

    # THEN
    assert response.status_code == 404
    assert response.json() == {"detail": "Stock not found"}
    mock_stock_master_service.get_stock_by_symbol.assert_called_once_with("NONEXIST", mock_db_session)
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_add_to_watchlist_already_exists(client, mock_db_session, mock_user_service, mock_stock_master_service, mock_user, mock_stock):
    # GIVEN
    watchlist_item = {"user_id": mock_user.id, "symbol": mock_stock.symbol}

    mock_user_service.get_user_by_id.return_value = mock_user
    mock_stock_master_service.get_stock_by_symbol.return_value = mock_stock
    mock_db_session.query.return_value.filter.return_value.first.return_value = MagicMock(spec=Watchlist) # Already exists

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_stock_master_service] = lambda: mock_stock_master_service

    # WHEN
    response = client.post("/watchlist/add", json=watchlist_item)

    # THEN
    assert response.status_code == 200
    assert response.json() == {"message": "이미 관심 목록에 있는 종목입니다."}
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

# --- GET /watchlist/get/{user_id} tests ---

@pytest.mark.asyncio
async def test_get_watchlist_success_with_items(client, mock_db_session, mock_user_service, mock_user):
    # GIVEN
    mock_user_service.get_user_by_id.return_value = mock_user

    mock_watchlist_item1 = MagicMock(spec=Watchlist, symbol="005930")
    mock_watchlist_item2 = MagicMock(spec=Watchlist, symbol="000660")
    mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_watchlist_item1, mock_watchlist_item2]

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    # WHEN
    response = client.get(f"/watchlist/get/{mock_user.id}")

    # THEN
    assert response.status_code == 200
    assert response.json() == {"watchlist": ["005930", "000660"]}
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, mock_user.id)

@pytest.mark.asyncio
async def test_get_watchlist_success_no_items(client, mock_db_session, mock_user_service, mock_user):
    # GIVEN
    mock_user_service.get_user_by_id.return_value = mock_user
    mock_db_session.query.return_value.filter.return_value.all.return_value = [] # No items

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    # WHEN
    response = client.get(f"/watchlist/get/{mock_user.id}")

    # THEN
    assert response.status_code == 200
    assert response.json() == {"watchlist": []}
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, mock_user.id)

@pytest.mark.asyncio
async def test_get_watchlist_user_not_found(client, mock_db_session, mock_user_service):
    # GIVEN
    mock_user_service.get_user_by_id.return_value = None # User not found

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    # WHEN
    response = client.get(f"/watchlist/get/999")

    # THEN
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, 999)

# --- POST /watchlist/remove tests ---

@pytest.mark.asyncio
async def test_remove_from_watchlist_success(client, mock_db_session, mock_user_service, mock_user, mock_stock):
    # GIVEN
    watchlist_item = {"user_id": mock_user.id, "symbol": mock_stock.symbol}

    mock_user_service.get_user_by_id.return_value = mock_user
    mock_db_session.query.return_value.filter.return_value.first.return_value = MagicMock(spec=Watchlist) # Item exists

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    # WHEN
    response = client.post("/watchlist/remove", json=watchlist_item)

    # THEN
    assert response.status_code == 200
    assert response.json() == {"message": "종목이 관심 목록에서 제거되었습니다."}
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, mock_user.id)
    mock_db_session.delete.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_remove_from_watchlist_user_not_found(client, mock_db_session, mock_user_service, mock_stock):
    # GIVEN
    watchlist_item = {"user_id": 999, "symbol": mock_stock.symbol}

    mock_user_service.get_user_by_id.return_value = None # User not found

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    # WHEN
    response = client.post("/watchlist/remove", json=watchlist_item)

    # THEN
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    mock_user_service.get_user_by_id.assert_called_once_with(mock_db_session, 999)
    mock_db_session.delete.assert_not_called()
    mock_db_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_remove_from_watchlist_not_in_list(client, mock_db_session, mock_user_service, mock_user, mock_stock):
    # GIVEN
    watchlist_item = {"user_id": mock_user.id, "symbol": mock_stock.symbol}

    mock_user_service.get_user_by_id.return_value = mock_user
    mock_db_session.query.return_value.filter.return_value.first.return_value = None # Not in watchlist

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    # WHEN
    response = client.post("/watchlist/remove", json=watchlist_item)

    # THEN
    assert response.status_code == 200
    assert response.json() == {"message": "관심 목록에 없는 종목입니다."}
    mock_db_session.delete.assert_not_called()
    mock_db_session.commit.assert_not_called()
