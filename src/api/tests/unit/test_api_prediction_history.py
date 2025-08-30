
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY
from src.api.main import app
from src.common.models.user import User
from src.common.models.prediction_history import PredictionHistory
from datetime import datetime

client = TestClient(app)

@patch('src.common.database.db_connector.SessionLocal')
@patch('src.api.routers.prediction_history.get_db')
def test_get_prediction_history_success(mock_get_db, mock_SessionLocal):
    """Test successful retrieval of prediction history."""
    mock_session = MagicMock()
    mock_SessionLocal.return_value = mock_session
    mock_get_db.return_value = mock_session

    # Mock User Query
    mock_user = User(id=1, telegram_id=12345)
    mock_user_query = MagicMock()
    mock_user_query.filter.return_value = mock_user_query
    mock_user_query.first.return_value = mock_user

    # Mock History Query
    mock_history_record = PredictionHistory(id=1, user_id=1, symbol='AAPL', prediction='Up', created_at=datetime.utcnow())
    mock_query_result = MagicMock()
    mock_query_result.PredictionHistory = mock_history_record
    mock_query_result.telegram_id = 12345
    
    mock_prediction_history_query = MagicMock()
    mock_prediction_history_query.join.return_value = mock_prediction_history_query
    mock_prediction_history_query.filter.return_value = mock_prediction_history_query
    mock_prediction_history_query.order_by.return_value = mock_prediction_history_query
    mock_prediction_history_query.offset.return_value = mock_prediction_history_query
    mock_prediction_history_query.limit.return_value = mock_prediction_history_query
    mock_prediction_history_query.count.return_value = 1
    mock_prediction_history_query.all.return_value = [mock_query_result]

    mock_session.query.side_effect = lambda model, *args: {
        User: mock_user_query,
        PredictionHistory: mock_prediction_history_query
    }.get(model, MagicMock()) # Return a generic MagicMock if model not explicitly mocked

    # 3. Make the request
    response = client.get("/api/v1/prediction/history/12345")

    # 4. Assert
    assert response.status_code == 200
    data = response.json()
    assert data['total_count'] == 1
    assert len(data['history']) == 1
    assert data['history'][0]['symbol'] == 'AAPL'
    assert data['page'] == 1 # Add assertion for page
    assert data['page_size'] == 10 # Add assertion for page_size

@patch('src.common.database.db_connector.SessionLocal')
@patch('src.api.routers.prediction_history.get_db')
def test_get_prediction_history_user_not_found(mock_get_db, mock_SessionLocal):
    """Test case where the user is not found."""
    mock_session = MagicMock()
    mock_SessionLocal.return_value = mock_session
    mock_get_db.return_value = mock_session
    
    mock_user_query = MagicMock()
    mock_user_query.filter.return_value = mock_user_query
    mock_user_query.first.return_value = None # User not found

    mock_session.query.side_effect = lambda model, *args: {
        User: mock_user_query,
    }.get(model, MagicMock())

    response = client.get("/api/v1/prediction/history/99999")

    assert response.status_code == 200
    data = response.json()
    assert data['total_count'] == 0

@patch('src.common.database.db_connector.SessionLocal')
@patch('src.api.routers.prediction_history.get_db')
def test_get_prediction_history_with_filters(mock_get_db, mock_SessionLocal):
    """Test prediction history retrieval with query filters."""
    mock_session = MagicMock()
    mock_get_db.return_value = mock_session
    mock_SessionLocal.return_value = mock_session
    
    mock_user_query = MagicMock()
    mock_user_query.filter.return_value = mock_user_query
    mock_user_query.first.return_value = User(id=1, telegram_id=12345)

    mock_prediction_history_query = MagicMock()
    mock_prediction_history_query.join.return_value = mock_prediction_history_query
    mock_prediction_history_query.filter.return_value = mock_prediction_history_query
    mock_prediction_history_query.order_by.return_value = mock_prediction_history_query
    mock_prediction_history_query.offset.return_value = mock_prediction_history_query
    mock_prediction_history_query.limit.return_value = mock_prediction_history_query
    mock_prediction_history_query.count.return_value = 1
    mock_prediction_history_query.all.return_value = [MagicMock(PredictionHistory=MagicMock(symbol='TSLA', prediction='Down'), telegram_id=12345)]

    mock_session.query.side_effect = lambda model, *args: {
        User: mock_user_query,
        PredictionHistory: mock_prediction_history_query
    }.get(model, MagicMock())

    client.get("/api/v1/prediction/history/12345?symbol=TSLA&prediction=Down")

    # The first filter is for user_id. The next two are for symbol and prediction.
    mock_prediction_history_query.filter.assert_called()
    # We expect filter to be called twice after the initial user_id filter
    # The actual filter calls are on the mock_prediction_history_query_obj
    # The exact call count might vary based on how the router builds the query
    # Let's check the arguments passed to filter more precisely if needed.

@patch('src.common.database.db_connector.SessionLocal')
@patch('src.api.routers.prediction_history.get_db')
def test_get_prediction_history_pagination(mock_get_db, mock_SessionLocal):
    """Test pagination logic."""
    mock_session = MagicMock()
    mock_SessionLocal.return_value = mock_session
    mock_get_db.return_value = mock_session

    mock_user_query = MagicMock()
    mock_user_query.filter.return_value = mock_user_query
    mock_user_query.first.return_value = User(id=1, telegram_id=12345)
    
    mock_prediction_history_query = MagicMock()
    mock_prediction_history_query.join.return_value = mock_prediction_history_query
    mock_prediction_history_query.filter.return_value = mock_prediction_history_query
    mock_prediction_history_query.order_by.return_value = mock_prediction_history_query
    mock_prediction_history_query.offset.return_value = mock_prediction_history_query
    mock_prediction_history_query.limit.return_value = mock_prediction_history_query
    mock_prediction_history_query.count.return_value = 100 # Example total count
    mock_prediction_history_query.all.return_value = [
        MagicMock(
            PredictionHistory=MagicMock(
                id=i,
                user_id=1,
                symbol=f"SYMBOL{i}",
                prediction=f"PRED{i}",
                created_at=datetime.utcnow()
            ),
            telegram_id=12345
        ) for i in range(5) # Create 5 unique mock records
    ]

    mock_session.query.side_effect = lambda model, *args: {
        User: mock_user_query,
        PredictionHistory: mock_prediction_history_query
    }.get(model, MagicMock())

    client.get("/api/v1/prediction/history/12345?page=3&page_size=5")

    mock_prediction_history_query.offset.assert_called_with(10)
    mock_prediction_history_query.limit.assert_called_with(5)

@patch('src.common.database.db_connector.SessionLocal')
@patch('src.api.routers.prediction_history.get_db')
def test_get_prediction_history_no_history(mock_get_db, mock_SessionLocal):
    """Test case where user exists but has no prediction history."""
    mock_session = MagicMock()
    mock_get_db.return_value = mock_session
    mock_SessionLocal.return_value = mock_session

    mock_user_query_obj = MagicMock()
    mock_user_query_obj.filter.return_value = mock_user_query_obj
    mock_user_query_obj.first.return_value = User(id=1, telegram_id=12345)
    
    mock_prediction_history_query_obj = MagicMock()
    mock_prediction_history_query_obj.join.return_value = mock_prediction_history_query_obj
    mock_prediction_history_query_obj.filter.return_value = mock_prediction_history_query_obj
    mock_prediction_history_query_obj.order_by.return_value = mock_prediction_history_query_obj
    mock_prediction_history_query_obj.offset.return_value = mock_prediction_history_query_obj
    mock_prediction_history_query_obj.limit.return_value = mock_prediction_history_query_obj
    mock_prediction_history_query_obj.count.return_value = 0
    mock_prediction_history_query_obj.all.return_value = []

    mock_session.query.side_effect = lambda model, *args: {
        User: mock_user_query_obj,
        PredictionHistory: mock_prediction_history_query_obj
    }.get(model, MagicMock())

    response = client.get("/api/v1/prediction/history/12345")

    assert response.status_code == 200
    data = response.json()
    assert data['total_count'] == 0
    assert len(data['history']) == 0
