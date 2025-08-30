import pytest
from fastapi import FastAPI, Depends # Import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from src.api.routers.admin import router, get_db, get_current_active_admin_user # Import actual dependencies
from src.common.models.user import User
from src.common.models.simulated_trade import SimulatedTrade
from src.common.models.prediction_history import PredictionHistory

# Create a FastAPI app instance
app = FastAPI()
app.include_router(router) # Include the admin router

# Create a TestClient for the FastAPI app
client = TestClient(app) # Use app here

# Mock dependencies
@pytest.fixture
def mock_get_db():
    db_mock = MagicMock(spec=Session)
    yield db_mock

@pytest.fixture
def mock_get_current_active_admin_user():
    user_mock = MagicMock(spec=User)
    user_mock.username = "admin_user"
    yield user_mock

class TestAdminRouter:

    def test_admin_stats(self, mock_get_current_active_admin_user, mock_get_db):
        # GIVEN
        db_instance = mock_get_db # Use the mock directly
        db_instance.query.return_value.count.side_effect = [10, 5, 20] # user, trade, prediction counts

        # Override dependencies
        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

        # WHEN
        response = client.get("/admin/admin_stats") # Corrected path

        # THEN
        assert response.status_code == 200
        assert response.json() == {
            "user_count": 10,
            "trade_count": 5,
            "prediction_count": 20
        }
        db_instance.query.assert_any_call(User)
        db_instance.query.assert_any_call(SimulatedTrade)
        db_instance.query.assert_any_call(PredictionHistory)

        # Clean up overrides
        app.dependency_overrides = {}
