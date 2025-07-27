import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from src.api.models.stock_master import StockMaster
from src.api.services.stock_service import StockService


def create_stock_master_data(db: Session):
    """테스트용 종목 마스터 데이터를 생성합니다."""
    stocks = [
        StockMaster(symbol="005930", name="삼성전자", market="KOSPI", corp_code="00126380"),
        StockMaster(symbol="035720", name="카카오", market="KOSPI", corp_code="00130000"),
        StockMaster(symbol="000660", name="SK하이닉스", market="KOSPI", corp_code="00164779"),
    ]
    db.add_all(stocks)
    db.commit()
    for stock in stocks:
        db.refresh(stock)
    return stocks


class TestStockMasterRouter:
    """stock_master 라우터 테스트"""

    def test_get_all_symbols(self, client: TestClient, db: Session):
        # Given
        create_stock_master_data(db)

        # When
        response = client.get("/symbols/")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"} in data

    def test_get_all_symbols_empty(self, client: TestClient):
        # Given: DB에 종목이 없음

        # When
        response = client.get("/symbols/")

        # Then
        assert response.status_code == 200
        assert response.json() == []

    def test_search_symbols_by_name(self, client: TestClient, db: Session):
        # Given
        create_stock_master_data(db)

        # When
        response = client.get("/symbols/search?query=삼성전자")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "005930"

    def test_search_symbols_by_symbol(self, client: TestClient, db: Session):
        # Given
        create_stock_master_data(db)

        # When
        response = client.get("/symbols/search?query=035720")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "카카오"

    def test_search_symbols_case_insensitive(self, client: TestClient, db: Session):
        # Given
        create_stock_master_data(db)

        # When
        response = client.get("/symbols/search?query=sk하이닉스")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "000660"

    def test_search_symbols_no_results(self, client: TestClient, db: Session):
        # Given
        create_stock_master_data(db)

        # When
        response = client.get("/symbols/search?query=없는종목")

        # Then
        assert response.status_code == 200
        assert response.json() == []

    def test_search_symbols_empty_query(self, client: TestClient):
        # When
        response = client.get("/symbols/search?query=")

        # Then
        assert response.status_code == 422  # FastAPI validation error for min_length=1

    def test_get_current_price_and_change_success(self, client: TestClient, db: Session):
        # Given
        symbol = "005930"
        # StockService.get_current_price_and_change를 모의하여 특정 값을 반환하도록 설정
        mock_price_data = {"current_price": 75000, "change": 1000, "change_rate": 1.35}
        
        # StockService 의존성 오버라이드를 위한 mock
        mock_stock_service = MagicMock(spec=StockService)
        mock_stock_service.get_current_price_and_change.return_value = mock_price_data
        
        # FastAPI 앱의 의존성 주입 오버라이드
        from src.api.routers.stock_master import get_stock_service
        from src.api.main import app
        app.dependency_overrides[get_stock_service] = lambda: mock_stock_service

        # When
        response = client.get(f"/symbols/{symbol}/current_price_and_change")

        # Then
        assert response.status_code == 200
        assert response.json() == mock_price_data
        mock_stock_service.get_current_price_and_change.assert_called_once_with(symbol, db)
        
        # 오버라이드 해제
        del app.dependency_overrides[get_stock_service]

    def test_get_current_price_and_change_not_found(self, client: TestClient, db: Session):
        # Given
        symbol = "NONEXISTENT"
        # StockService.get_current_price_and_change가 None을 반환하도록 모의
        mock_stock_service = MagicMock(spec=StockService)
        mock_stock_service.get_current_price_and_change.return_value = None

        from src.api.routers.stock_master import get_stock_service
        from src.api.main import app
        app.dependency_overrides[get_stock_service] = lambda: mock_stock_service

        # When
        response = client.get(f"/symbols/{symbol}/current_price_and_change")

        # Then
        assert response.status_code == 404
        assert response.json() == {"detail": "Stock price data not found"}
        mock_stock_service.get_current_price_and_change.assert_called_once_with(symbol, db)
        
        # 오버라이드 해제
        del app.dependency_overrides[get_stock_service]
