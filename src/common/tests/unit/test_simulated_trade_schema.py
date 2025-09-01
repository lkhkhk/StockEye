import pytest
from pydantic import ValidationError
from datetime import datetime
from src.common.schemas.simulated_trade import (
    SimulatedTradeItem,
    SimulatedTradeResponse,
    TradeStatistics,
    TradeHistoryResponse,
)

def test_simulated_trade_item_valid():
    # Test buy trade
    buy_trade = SimulatedTradeItem(user_id=1, symbol="AAPL", trade_type="buy", price=150.0, quantity=10)
    assert buy_trade.user_id == 1
    assert buy_trade.symbol == "AAPL"
    assert buy_trade.trade_type == "buy"
    assert buy_trade.price == 150.0
    assert buy_trade.quantity == 10

    # Test sell trade
    sell_trade = SimulatedTradeItem(user_id=2, symbol="GOOG", trade_type="sell", price=2000.0, quantity=5)
    assert sell_trade.user_id == 2
    assert sell_trade.symbol == "GOOG"
    assert sell_trade.trade_type == "sell"
    assert sell_trade.price == 2000.0
    assert sell_trade.quantity == 5

def test_simulated_trade_item_invalid_trade_type():
    with pytest.raises(ValidationError) as exc_info:
        SimulatedTradeItem(user_id=1, symbol="AAPL", trade_type="hold", price=150.0, quantity=10)
    assert "trade_type" in str(exc_info.value)
    assert "Input should be 'buy' or 'sell'" in str(exc_info.value)

def test_simulated_trade_item_missing_fields():
    with pytest.raises(ValidationError):
        SimulatedTradeItem(user_id=1, symbol="AAPL", trade_type="buy", price=150.0) # Missing quantity

def test_simulated_trade_response_valid():
    now = datetime.now()
    # Test with minimum required fields
    response = SimulatedTradeResponse(
        trade_id=1, user_id=1, symbol="AAPL", trade_type="buy", price=150.0, quantity=10, trade_time=now
    )
    assert response.trade_id == 1
    assert response.user_id == 1
    assert response.symbol == "AAPL"
    assert response.trade_type == "buy"
    assert response.price == 150.0
    assert response.quantity == 10
    assert response.trade_time == now
    assert response.profit_loss is None
    assert response.profit_rate is None
    assert response.current_price is None

    # Test with all fields
    response = SimulatedTradeResponse(
        trade_id=2, user_id=2, symbol="GOOG", trade_type="sell", price=2000.0, quantity=5, trade_time=now,
        profit_loss=100.0, profit_rate=5.0, current_price=2100.0
    )
    assert response.trade_id == 2
    assert response.user_id == 2
    assert response.symbol == "GOOG"
    assert response.trade_type == "sell"
    assert response.price == 2000.0
    assert response.quantity == 5
    assert response.trade_time == now
    assert response.profit_loss == 100.0
    assert response.profit_rate == 5.0
    assert response.current_price == 2100.0

def test_simulated_trade_response_missing_fields():
    with pytest.raises(ValidationError):
        SimulatedTradeResponse(trade_id=1, user_id=1, symbol="AAPL", trade_type="buy", price=150.0) # Missing quantity, trade_time

def test_trade_statistics_valid():
    stats = TradeStatistics(total_trades=10, total_profit_loss=500.0, profitable_trades=7, win_rate=0.7)
    assert stats.total_trades == 10
    assert stats.total_profit_loss == 500.0
    assert stats.profitable_trades == 7
    assert stats.win_rate == 0.7

def test_trade_statistics_missing_fields():
    with pytest.raises(ValidationError):
        TradeStatistics(total_trades=10, total_profit_loss=500.0, profitable_trades=7) # Missing win_rate

def test_trade_history_response_valid():
    now = datetime.now()
    trade1 = SimulatedTradeResponse(trade_id=1, user_id=1, symbol="AAPL", trade_type="buy", price=150.0, quantity=10, trade_time=now)
    trade2 = SimulatedTradeResponse(trade_id=2, user_id=1, symbol="GOOG", trade_type="sell", price=2000.0, quantity=5, trade_time=now)
    stats = TradeStatistics(total_trades=2, total_profit_loss=100.0, profitable_trades=1, win_rate=0.5)

    history = TradeHistoryResponse(trades=[trade1, trade2], statistics=stats)
    assert len(history.trades) == 2
    assert history.trades[0].symbol == "AAPL"
    assert history.statistics.total_trades == 2

def test_trade_history_response_empty_trades():
    stats = TradeStatistics(total_trades=0, total_profit_loss=0.0, profitable_trades=0, win_rate=0.0)
    history = TradeHistoryResponse(trades=[], statistics=stats)
    assert len(history.trades) == 0
    assert history.statistics.total_trades == 0

def test_trade_history_response_missing_fields():
    with pytest.raises(ValidationError):
        TradeHistoryResponse(trades=[]) # Missing statistics
