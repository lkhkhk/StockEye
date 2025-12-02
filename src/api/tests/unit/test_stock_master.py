import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from sqlalchemy.orm import Session

# Explicitly import the module to be tested for coverage
from src.api.routers import stock_master

from src.api.routers.stock_master import router as stock_master_router, get_stock_master_service, get_market_data_service
from src.common.database.db_connector import get_db
from src.common.models.stock_master import StockMaster
from src.common.services.stock_master_service import StockMasterService
from src.common.services.market_data_service import MarketDataService

# Create a new FastAPI app instance for testing this router
app = FastAPI()

# Mock dependencies
@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_stock_master_service():
    return MagicMock(spec=StockMasterService)

@pytest.fixture
def mock_market_data_service():
    return MagicMock(spec=MarketDataService)

# Apply dependencies and include the router
@pytest.fixture
def client(mock_db_session, mock_stock_master_service, mock_market_data_service):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_stock_master_service] = lambda: mock_stock_master_service
    app.dependency_overrides[get_market_data_service] = lambda: mock_market_data_service
    app.include_router(stock_master_router)
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()

# --- Test Cases ---

def test_get_all_symbols_success(client, mock_db_session):
    # GIVEN
    mock_stocks = [StockMaster(symbol="005930", name="삼성전자", market="KOSPI")]
    mock_db_session.query.return_value.count.return_value = 1
    mock_db_session.query.return_value.offset.return_value.limit.return_value.all.return_value = mock_stocks

    # WHEN
    response = client.get("/symbols/?limit=1&offset=0")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["symbol"] == "005930"

def test_search_symbols_success(client, mock_stock_master_service, mock_db_session):
    # GIVEN
    query = "삼성"
    mock_stocks = [StockMaster(symbol="005930", name="삼성전자", market="KOSPI")]
    mock_stock_master_service.search_stocks.return_value = mock_stocks
    # Mock the count query as well
    mock_db_session.query.return_value.filter.return_value.count.return_value = 1

    # WHEN
    response = client.get(f"/symbols/search?query={query}")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "삼성전자"
    mock_stock_master_service.search_stocks.assert_called_once_with(query, mock_db_session, limit=10, offset=0)

def test_search_symbols_no_result(client, mock_stock_master_service, mock_db_session):
    # GIVEN
    query = "없는종목"
    mock_stock_master_service.search_stocks.return_value = []
    mock_db_session.query.return_value.filter.return_value.count.return_value = 0

    # WHEN
    response = client.get(f"/symbols/search?query={query}")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 0
    assert len(data["items"]) == 0

def test_get_current_price_and_change_api_success(client, mock_market_data_service):
    # GIVEN
    symbol = "005930"
    price_data = {"current_price": 80000, "change": 1000, "change_percent": 1.26}
    mock_market_data_service.get_current_price_and_change.return_value = price_data

    # WHEN
    response = client.get(f"/symbols/{symbol}/current_price_and_change")

    # THEN
    assert response.status_code == 200
    assert response.json() == price_data
    mock_market_data_service.get_current_price_and_change.assert_called_once()

def test_get_current_price_and_change_api_not_found(client, mock_market_data_service):
    # GIVEN
    symbol = "999999"
    mock_market_data_service.get_current_price_and_change.return_value = None

    # WHEN
    response = client.get(f"/symbols/{symbol}/current_price_and_change")

    # THEN
    assert response.status_code == 404
    assert response.json() == {"detail": "Stock price data not found"}