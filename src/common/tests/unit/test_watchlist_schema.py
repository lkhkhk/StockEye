import pytest
from pydantic import ValidationError
from src.common.schemas.watchlist import (
    WatchlistBase,
    WatchlistCreate,
    Watchlist,
    WatchlistResponse,
)

def test_watchlist_base_valid():
    watchlist = WatchlistBase(user_id=1, symbol="AAPL")
    assert watchlist.user_id == 1
    assert watchlist.symbol == "AAPL"

def test_watchlist_base_missing_fields():
    with pytest.raises(ValidationError):
        WatchlistBase(user_id=1) # Missing symbol

def test_watchlist_create_valid():
    watchlist = WatchlistCreate(user_id=1, symbol="GOOG")
    assert watchlist.user_id == 1
    assert watchlist.symbol == "GOOG"

def test_watchlist_create_missing_fields():
    with pytest.raises(ValidationError):
        WatchlistCreate(symbol="MSFT") # Missing user_id

def test_watchlist_valid():
    # Watchlist model is typically used for ORM mapping, so it should work like WatchlistBase
    watchlist = Watchlist(user_id=1, symbol="TSLA")
    assert watchlist.user_id == 1
    assert watchlist.symbol == "TSLA"

def test_watchlist_response_valid():
    response = WatchlistResponse(watchlist=["AAPL", "GOOG", "MSFT"])
    assert response.watchlist == ["AAPL", "GOOG", "MSFT"]

def test_watchlist_response_empty():
    response = WatchlistResponse(watchlist=[])
    assert response.watchlist == []

def test_watchlist_response_invalid_content():
    with pytest.raises(ValidationError):
        WatchlistResponse(watchlist=["AAPL", 123]) # Invalid type in list
