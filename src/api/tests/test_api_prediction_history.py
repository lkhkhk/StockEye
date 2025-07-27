import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.tests.helpers import create_test_user
from src.api.models.prediction_history import PredictionHistory
from datetime import datetime


class TestPredictionHistoryRouter:
    """예측 이력 라우터 테스트"""

    @pytest.fixture(autouse=True)
    def setup_test_data(self, db: Session):
        # 각 테스트 메서드 실행 전에 PredictionHistory 테이블을 비웁니다.
        db.query(PredictionHistory).delete()
        db.commit()

    def _create_prediction_history(self, db: Session, user_id: int, symbol: str, prediction: str, created_at: datetime):
        history = PredictionHistory(
            user_id=user_id,
            symbol=symbol,
            prediction=prediction,
            created_at=created_at
        )
        db.add(history)
        db.flush() # commit 대신 flush 사용
        db.refresh(history) # ID가 할당되었는지 확인
        return history

    def test_get_prediction_history_success(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        self._create_prediction_history(db, user.id, "005930", "상승", datetime(2023, 1, 1, 10, 0, 0))
        self._create_prediction_history(db, user.id, "035720", "하락", datetime(2023, 1, 2, 11, 0, 0))

        # When
        response = client.get(f"/prediction/history/{user.id}")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["history"]) == 2
        assert data["history"][0]["symbol"] == "035720" # 최신순 정렬

    def test_get_prediction_history_not_found_user(self, client: TestClient):
        # When
        response = client.get("/prediction/history/99999")

        # Then
        assert response.status_code == 200 # 현재 라우터는 user_id가 없어도 200을 반환하고 빈 리스트를 줍니다.
        assert response.json() == {"history": [], "total_count": 0, "page": 1, "page_size": 10}

    def test_get_prediction_history_empty(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)

        # When
        response = client.get(f"/prediction/history/{user.id}")

        # Then
        assert response.status_code == 200
        assert response.json() == {"history": [], "total_count": 0, "page": 1, "page_size": 10}

    def test_get_prediction_history_pagination(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        for i in range(1, 15):
            self._create_prediction_history(db, user.id, f"SYMBOL{i:02d}", "상승", datetime(2023, 1, i, 10, 0, 0))

        # When: Page 1, size 5
        response = client.get(f"/prediction/history/{user.id}?page=1&page_size=5")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 14
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["history"]) == 5
        assert data["history"][0]["symbol"] == "SYMBOL14" # 최신순

        # When: Page 2, size 5
        response = client.get(f"/prediction/history/{user.id}?page=2&page_size=5")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 14
        assert data["page"] == 2
        assert data["page_size"] == 5
        assert len(data["history"]) == 5
        assert data["history"][0]["symbol"] == "SYMBOL09"

    def test_get_prediction_history_filter_by_symbol(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        self._create_prediction_history(db, user.id, "005930", "상승", datetime(2023, 1, 1))
        self._create_prediction_history(db, user.id, "035720", "하락", datetime(2023, 1, 2))
        self._create_prediction_history(db, user.id, "005930", "유지", datetime(2023, 1, 3))

        # When
        response = client.get(f"/prediction/history/{user.id}?symbol=005930")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["history"]) == 2
        assert all(r["symbol"] == "005930" for r in data["history"])

    def test_get_prediction_history_filter_by_prediction(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        self._create_prediction_history(db, user.id, "005930", "상승", datetime(2023, 1, 1))
        self._create_prediction_history(db, user.id, "035720", "하락", datetime(2023, 1, 2))
        self._create_prediction_history(db, user.id, "005930", "유지", datetime(2023, 1, 3))

        # When
        response = client.get(f"/prediction/history/{user.id}?prediction=상승")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["history"]) == 1
        assert data["history"][0]["prediction"] == "상승"

    def test_get_prediction_history_filter_by_symbol_and_prediction(self, client: TestClient, db: Session):
        # Given
        user = create_test_user(db)
        self._create_prediction_history(db, user.id, "005930", "상승", datetime(2023, 1, 1))
        self._create_prediction_history(db, user.id, "035720", "하락", datetime(2023, 1, 2))
        self._create_prediction_history(db, user.id, "005930", "유지", datetime(2023, 1, 3))

        # When
        response = client.get(f"/prediction/history/{user.id}?symbol=005930&prediction=유지")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["history"]) == 1
        assert data["history"][0]["symbol"] == "005930"
        assert data["history"][0]["prediction"] == "유지"