import pytest
from fastapi import FastAPI, Depends # Import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.orm import Session
from src.api.routers.admin import router, get_db, get_current_active_admin_user, get_stock_service # Import actual dependencies
from src.common.models.user import User
from src.common.models.simulated_trade import SimulatedTrade
from src.common.models.prediction_history import PredictionHistory
from src.common.services.stock_service import StockService # Import StockService

# FastAPI 앱 인스턴스 생성
app = FastAPI()
app.include_router(router) # 관리자 라우터 포함

# FastAPI 앱을 위한 TestClient 생성
client = TestClient(app) # 여기에 앱 사용

# 의존성 모의
@pytest.fixture
def mock_get_db():
    # MOCK: get_db 의존성
    # MagicMock: SQLAlchemy Session 객체를 모의합니다. 동기적으로 동작합니다.
    db_mock = MagicMock(spec=Session)
    yield db_mock

@pytest.fixture
def mock_get_current_active_admin_user():
    # MOCK: get_current_active_admin_user 의존성
    # MagicMock: User 모델 객체를 모의합니다. 동기적으로 동작합니다.
    user_mock = MagicMock(spec=User)
    user_mock.username = "admin_user"
    yield user_mock

class TestAdminRouter:

    def test_admin_stats(self, mock_get_current_active_admin_user, mock_get_db):
        # GIVEN
        # mock_get_db 픽스처에서 반환된 모의 DB 세션 인스턴스를 사용합니다.
        db_instance = mock_get_db 
        # db_instance.query().count() 호출 시 반환될 값을 설정합니다.
        # User, SimulatedTrade, PredictionHistory 순서로 호출될 것으로 예상합니다.
        db_instance.query.return_value.count.side_effect = [10, 5, 20] # user, trade, prediction counts

        # FastAPI의 의존성 주입을 오버라이드하여 실제 함수 대신 모의 객체를 사용하도록 설정합니다.
        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

        # WHEN
        response = client.get("/admin/admin_stats") 

        # THEN
        assert response.status_code == 200
        assert response.json() == {
            "user_count": 10,
            "trade_count": 5,
            "prediction_count": 20
        }
        # db_instance.query (MagicMock)가 User, SimulatedTrade, PredictionHistory 모델로 호출되었는지 확인합니다.
        db_instance.query.assert_any_call(User)
        db_instance.query.assert_any_call(SimulatedTrade)
        db_instance.query.assert_any_call(PredictionHistory)

        # 테스트 후 의존성 오버라이드를 정리하여 다른 테스트에 영향을 주지 않도록 합니다.
        app.dependency_overrides = {}

    @pytest.mark.asyncio 
    @patch('src.api.routers.admin.get_db') # MOCK: get_db 의존성
    @patch('src.api.routers.admin.get_current_active_admin_user') # MOCK: get_current_active_admin_user 의존성
    @patch('src.api.routers.admin.StockService') # MOCK: src.api.routers.admin.StockService 클래스
    async def test_update_master_success(self, mock_StockService_class, mock_get_current_active_admin_user, mock_get_db):
        # GIVEN
        # mock_get_db 픽스처에서 반환된 모의 DB 세션 인스턴스를 사용합니다.
        db_instance = mock_get_db 

        # MOCK: StockService 인스턴스
        # MagicMock: StockService 클래스의 인스턴스를 모의합니다. 동기적으로 동작합니다.
        mock_stock_service_instance = MagicMock(spec=StockService) 
        # mock_stock_service_instance.update_stock_master (AsyncMock) 호출 시 반환될 값을 설정합니다.
        mock_stock_service_instance.update_stock_master.return_value = AsyncMock(return_value={"success": True, "updated_count": 100})
        # StockService() 생성자 호출 시 mock_stock_service_instance가 반환되도록 설정합니다.
        mock_StockService_class.return_value = mock_stock_service_instance 

        # FastAPI의 의존성 주입을 오버라이드하여 실제 함수 대신 모의 객체를 사용하도록 설정합니다.
        app.dependency_overrides[get_db] = lambda: db_instance
        app.dependency_overrides[get_current_active_admin_user] = lambda: mock_get_current_active_admin_user

        # WHEN
        response = client.post("/admin/update_master")

        # THEN
        assert response.status_code == 200
        assert response.json()["message"] == "종목마스터 갱신 완료"
        assert response.json()["updated_count"] == 100
        assert "timestamp" in response.json()

        # mock_stock_service_instance.update_stock_master (AsyncMock)이 올바른 인자로 한 번 호출되었는지 확인합니다.
        mock_stock_service_instance.update_stock_master.assert_called_once_with(db_instance)

        # 테스트 후 의존성 오버라이드를 정리하여 다른 테스트에 영향을 주지 않도록 합니다.
        app.dependency_overrides = {}