import pytest
from pydantic import ValidationError
from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate, PriceAlertRead
from src.common.models import StockMaster, User, PriceAlert
import datetime

def test_price_alert_base():
    # Test with valid data
    alert = PriceAlertCreate(symbol="AAPL", target_price=150.0, condition="gte")
    assert alert.symbol == "AAPL"
    assert alert.target_price == 150.0
    assert alert.condition == "gte"

    # Test with another valid data
    alert = PriceAlertCreate(symbol="GOOG", change_percent=-5, change_type="down", notify_on_disclosure=False)
    assert alert.symbol == "GOOG"
    assert alert.change_percent == -5
    assert alert.change_type == "down"
    assert alert.notify_on_disclosure is False

    # Test with invalid condition
    with pytest.raises(ValidationError):
        PriceAlertCreate(symbol="TSLA", condition="invalid_condition")

    # Test with missing symbol
    with pytest.raises(ValidationError):
        PriceAlertCreate(target_price=100.0)

def test_price_alert_create():
    # Test with valid data
    alert_data = {
        "symbol": "AMZN",
        "target_price": 3500.0,
        "condition": "lte",
        "is_active": False
    }
    alert = PriceAlertCreate(**alert_data)
    assert alert.symbol == "AMZN"
    assert alert.target_price == 3500.0
    assert alert.condition == "lte"
    assert alert.is_active is False

def test_price_alert_create_valid():
    # Test with minimum required fields
    alert = PriceAlertCreate(symbol="MSFT")
    assert alert.symbol == "MSFT"

def test_price_alert_read():
    now = datetime.datetime.now()
    alert_data = {
        "id": 1,
        "user_id": 1,
        "symbol": "NFLX",
        "target_price": 500.0,
        "condition": "gte",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "notify_on_disclosure": True,
        "stock_name": "Netflix Inc."
    }
    alert = PriceAlertRead(**alert_data)
    assert alert.id == 1
    assert alert.stock_name == "Netflix Inc."

def test_price_alert_update():
    # Test with valid data
    update_data = {
        "target_price": 160.0,
        "is_active": False
    }
    alert_update = PriceAlertUpdate(**update_data)
    assert alert_update.target_price == 160.0
    assert alert_update.is_active is False

    # Test with empty data
    alert_update_empty = PriceAlertUpdate()
    assert alert_update_empty.model_dump(exclude_unset=True) == {}