import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.query import Query # Import Query for type hinting

from src.api.routers.stock_master import router as stock_master_router, get_stock_master_service
from src.common.database.db_connector import get_db
from src.common.models.stock_master import StockMaster
from src.common.services.stock_master_service import StockMasterService

# --- Test Setup ---

app = FastAPI()

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_stock_master_service():
    return MagicMock(spec=StockMasterService)

@pytest.fixture
def client(mock_db_session, mock_stock_master_service):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_stock_master_service] = lambda: mock_stock_master_service
    app.include_router(stock_master_router)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()

# --- Test Cases ---

@pytest.mark.asyncio
async def test_get_all_symbols_success(client, mock_db_session):
    # GIVEN
    mock_query = MagicMock(spec=Query)
    mock_db_session.query.return_value = mock_query
    mock_query.count.return_value = 2
    stock1 = MagicMock(spec=StockMaster)
    stock1.symbol = "005930"
    stock1.name = "삼성전자"
    stock1.market = "KOSPI"
    stock2 = MagicMock(spec=StockMaster)
    stock2.symbol = "000660"
    stock2.name = "SK하이닉스"
    stock2.market = "KOSPI"
    mock_query.offset.return_value.limit.return_value.all.return_value = [stock1, stock2]

    # WHEN
    response = client.get("/symbols")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["symbol"] == "005930"
    mock_db_session.query.assert_called_with(StockMaster) # Changed from assert_called_once_with
    mock_query.count.assert_called_once()
    mock_query.offset.assert_called_once_with(0)
    mock_query.offset.return_value.limit.assert_called_once_with(10)

@pytest.mark.asyncio
async def test_get_all_symbols_pagination(client, mock_db_session):
    # GIVEN
    mock_query = MagicMock(spec=Query)
    mock_db_session.query.return_value = mock_query
    mock_query.count.return_value = 100
    stock1 = MagicMock(spec=StockMaster)
    stock1.symbol = "005930"
    stock1.name = "삼성전자"
    stock1.market = "KOSPI"
    mock_query.offset.return_value.limit.return_value.all.return_value = [stock1]

    # WHEN
    response = client.get("/symbols?limit=1&offset=0")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 100
    assert len(data["items"]) == 1
    assert data["items"][0]["symbol"] == "005930"
    mock_db_session.query.assert_called_with(StockMaster) # Changed from assert_called_once_with
    mock_query.count.assert_called_once()
    mock_query.offset.assert_called_once_with(0)
    mock_query.offset.return_value.limit.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_search_symbols_success(client, mock_db_session, mock_stock_master_service):
    # GIVEN
    stock1 = MagicMock(spec=StockMaster)
    stock1.symbol = "005930"
    stock1.name = "삼성전자"
    stock1.market = "KOSPI"
    mock_stock_master_service.search_stocks.return_value = [stock1]
    
    mock_query_filter = MagicMock(spec=Query)
    mock_db_session.query.return_value = mock_query_filter
    mock_query_filter.filter.return_value = mock_query_filter # Allow chaining .filter()
    mock_query_filter.filter.return_value.count.return_value = 1 # For total_count

    # WHEN
    response = client.get("/symbols/search?query=삼성")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["symbol"] == "005930"
    mock_stock_master_service.search_stocks.assert_called_once_with("삼성", mock_db_session, limit=10, offset=0) # Changed to keyword args
    mock_db_session.query.assert_called_once_with(StockMaster)
    mock_query_filter.filter.assert_called_once() # Check filter was called
    mock_query_filter.filter.return_value.count.assert_called_once() # Check count was called

@pytest.mark.asyncio
async def test_search_symbols_no_results(client, mock_db_session, mock_stock_master_service):
    # GIVEN
    mock_stock_master_service.search_stocks.return_value = []
    
    mock_query_filter = MagicMock(spec=Query)
    mock_db_session.query.return_value = mock_query_filter
    mock_query_filter.filter.return_value = mock_query_filter # Allow chaining .filter()
    mock_query_filter.filter.return_value.count.return_value = 0 # For total_count

    # WHEN
    response = client.get("/symbols/search?query=없는종목")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 0
    assert len(data["items"]) == 0
    mock_stock_master_service.search_stocks.assert_called_once_with("없는종목", mock_db_session, limit=10, offset=0) # Changed to keyword args
    mock_db_session.query.assert_called_once_with(StockMaster)
    mock_query_filter.filter.assert_called_once() # Check filter was called
    mock_query_filter.filter.return_value.count.assert_called_once() # Check count was called

@pytest.mark.asyncio
async def test_get_symbol_by_code_success(client, mock_stock_master_service):
    # GIVEN
    stock = MagicMock(spec=StockMaster)
    stock.symbol = "005930"
    stock.name = "삼성전자"
    stock.market = "KOSPI"
    mock_stock_master_service.get_stock_by_symbol.return_value = stock

    # WHEN
    response = client.get("/symbols/005930") # Calling the new endpoint

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "005930"
    assert data["name"] == "삼성전자"
    assert data["market"] == "KOSPI" # Added market assertion
    mock_stock_master_service.get_stock_by_symbol.assert_called_once()


@pytest.mark.asyncio
async def test_get_symbol_by_code_not_found(client, mock_stock_master_service):
    # GIVEN
    mock_stock_master_service.get_stock_by_symbol.return_value = None

    # WHEN
    response = client.get("/symbols/없는코드") # Calling the new endpoint

    # THEN
    assert response.status_code == 404
    assert response.json()["detail"] == "종목을 찾을 수 없습니다."
    mock_stock_master_service.get_stock_by_symbol.assert_called_once()

@pytest.mark.asyncio
async def test_get_all_symbols_service_exception(client, mock_db_session):
    # GIVEN
    mock_query = MagicMock(spec=Query)
    mock_db_session.query.return_value = mock_query
    mock_query.count.side_effect = Exception("Service error")

    # WHEN
    response = client.get("/symbols")

    # THEN
    # THEN
    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    mock_db_session.query.assert_called_once_with(StockMaster)
    mock_query.count.assert_called_once() # Check count was called

@pytest.mark.asyncio
async def test_search_symbols_service_exception(client, mock_db_session, mock_stock_master_service):
    # GIVEN
    mock_stock_master_service.search_stocks.side_effect = Exception("Service error")
    
    # Mock the count part as well, as it's called before search_stocks in the router
    mock_query_filter = MagicMock(spec=Query)
    mock_db_session.query.return_value = mock_query_filter
    mock_query_filter.filter.return_value = mock_query_filter
    mock_query_filter.filter.return_value.count.return_value = 0 # Doesn't matter for this test

    # WHEN
    response = client.get("/symbols/search?query=삼성")

    # THEN
    # THEN
    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    mock_stock_master_service.search_stocks.assert_called_once_with("삼성", mock_db_session, limit=10, offset=0) # Changed to keyword args

@pytest.mark.asyncio
async def test_get_symbol_by_code_service_exception(client, mock_stock_master_service):
    # GIVEN
    mock_stock_master_service.get_stock_by_symbol.side_effect = Exception("Service error")

    # WHEN
    response = client.get("/symbols/005930") # Calling the new endpoint

    # THEN
    # THEN
    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    mock_stock_master_service.get_stock_by_symbol.assert_called_once()