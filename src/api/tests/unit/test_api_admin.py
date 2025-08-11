import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from src.api.main import app 
from src.api.models.user import User

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    with patch('src.common.db_connector.get_db') as mock_get_db:
        mock_db = MagicMock(spec=Session)
        # Mock the query counts
        mock_db.query.return_value.count.side_effect = [5, 25, 15] # user_count, trade_count, prediction_count
        yield mock_db

@pytest.fixture
def mock_admin_user():
    return User(id=1, username="admin", email="admin@test.com", is_admin=True)

def test_admin_stats_success(mock_db_session, mock_admin_user):
    """관리자 통계 조회 성공 테스트"""
    with patch('src.api.auth.jwt_handler.get_current_active_admin_user', return_value=mock_admin_user):
        response = client.get("/api/v1/admin/admin_stats")
        assert response.status_code == 200
        assert response.json() == {
            "user_count": 5,
            "trade_count": 25,
            "prediction_count": 15
        }

def test_admin_stats_unauthorized():
    """관리자가 아닌 사용자가 통계 조회 시 401 오류 테스트"""
    with patch('src.api.auth.jwt_handler.get_current_active_admin_user', side_effect=Exception("Unauthorized")):
         response = client.get("/api/v1/admin/admin_stats")
         assert response.status_code == 401

@patch.dict('os.environ', {'APP_ENV': 'development'})
def test_reset_database_success_in_development(mock_db_session):
    """개발 환경에서 DB 초기화 성공 테스트"""
    with patch('src.api.routers.admin.seed_test_data') as mock_seed_data:
        response = client.post("/api/v1/admin/debug/reset-database")
        assert response.status_code == 200
        assert response.json() == {"message": "DB 초기화 및 데이터 시딩이 완료되었습니다."}
        mock_seed_data.assert_called_once()
        mock_db_session.commit.assert_called_once()

@patch.dict('os.environ', {'APP_ENV': 'production'})
def test_reset_database_forbidden_in_production():
    """운영 환경에서 DB 초기화 시 403 오류 테스트"""
    response = client.post("/api/v1/admin/debug/reset-database")
    assert response.status_code == 403
    assert response.json() == {"detail": "이 기능은 개발 환경에서만 사용할 수 있습니다."}
