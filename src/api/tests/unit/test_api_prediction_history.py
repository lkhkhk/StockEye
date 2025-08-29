
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY
from src.api.main import app
from src.common.models.user import User
from src.common.models.prediction_history import PredictionHistory
from datetime import datetime

client = TestClient(app)

@patch('src.api.routers.prediction_history.get_db')
def test_get_prediction_history_success(mock_get_db):
    """Test successful retrieval of prediction history."""
    mock_session = MagicMock()
    mock_get_db.return_value = mock_session

    # 1. Mock User Query: This is the key part.
    # We mock that query(User).filter(ANY).first() returns our mock_user.
    mock_user = User(id=1, telegram_id=12345)
    mock_session.query(User).filter.return_value.first.return_value = mock_user

    # 2. Mock History Query
    mock_history_record = PredictionHistory(id=1, user_id=1, symbol='AAPL', prediction='Up', created_at=datetime.utcnow())
    mock_query_result = MagicMock()
    mock_query_result.PredictionHistory = mock_history_record
    mock_query_result.telegram_id = 12345
    
    # Mock the chain of calls for the history query
    mock_history_query = MagicMock()
    mock_session.query(PredictionHistory).filter.return_value = mock_history_query
    mock_history_query.count.return_value = 1

    # Mock the final joined query
    mock_joined_query = MagicMock()
    mock_session.query(PredictionHistory, User.telegram_id).join.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value = mock_joined_query
    mock_joined_query.all.return_value = [mock_query_result]

    # 3. Make the request
    response = client.get("/api/v1/prediction/history/12345")

    # 4. Assert
    assert response.status_code == 200
    data = response.json()
    assert data['total_count'] == 1
    assert len(data['history']) == 1
    assert data['history'][0]['symbol'] == 'AAPL'

@patch('src.api.routers.prediction_history.get_db')
def test_get_prediction_history_user_not_found(mock_get_db):
    """Test case where the user is not found."""
    mock_session = MagicMock()
    mock_get_db.return_value = mock_session
    # This time, the user query should return None
    mock_session.query(User).filter.return_value.first.return_value = None

    response = client.get("/api/v1/prediction/history/99999")

    assert response.status_code == 200
    data = response.json()
    assert data['total_count'] == 0

@patch('src.api.routers.prediction_history.get_db')
def test_get_prediction_history_with_filters(mock_get_db):
    """Test prediction history retrieval with query filters."""
    mock_session = MagicMock()
    mock_get_db.return_value = mock_session
    
    mock_user = User(id=1, telegram_id=12345)
    mock_session.query(User).filter.return_value.first.return_value = mock_user
    
    mock_history_query = MagicMock()
    mock_session.query(PredictionHistory).filter.return_value = mock_history_query

    client.get("/api/v1/prediction/history/12345?symbol=TSLA&prediction=Down")

    # The first filter is for user_id. The next two are for symbol and prediction.
    assert mock_history_query.filter.call_count == 2

@patch('src.api.routers.prediction_history.get_db')
def test_get_prediction_history_pagination(mock_get_db):
    """Test pagination logic."""
    mock_session = MagicMock()
    mock_get_db.return_value = mock_session

    mock_user = User(id=1, telegram_id=12345)
    mock_session.query(User).filter.return_value.first.return_value = mock_user
    
    # Mock the final joined query chain to check for offset and limit
    mock_joined_query_chain = mock_session.query(PredictionHistory, User.telegram_id).join.return_value.filter.return_value.order_by.return_value
    
    client.get("/api/v1/prediction/history/12345?page=3&page_size=5")

    mock_joined_query_chain.offset.assert_called_with(10)
    mock_joined_query_chain.offset.return_value.limit.assert_called_with(5)

@patch('src.api.routers.prediction_history.get_db')
def test_get_prediction_history_no_history(mock_get_db):
    """Test case where user exists but has no prediction history."""
    mock_session = MagicMock()
    mock_get_db.return_value = mock_session

    mock_user = User(id=1, telegram_id=12345)
    mock_session.query(User).filter.return_value.first.return_value = mock_user
    
    # History query should return 0 count and empty list
    mock_history_query = MagicMock()
    mock_session.query(PredictionHistory).filter.return_value = mock_history_query
    mock_history_query.count.return_value = 0

    mock_joined_query = MagicMock()
    mock_session.query(PredictionHistory, User.telegram_id).join.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value = mock_joined_query
    mock_joined_query.all.return_value = []

    response = client.get("/api/v1/prediction/history/12345")

    assert response.status_code == 200
    data = response.json()
    assert data['total_count'] == 0
    assert len(data['history']) == 0
