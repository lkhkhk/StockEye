# src/api/tests/integration/test_api_prediction_history_integration.py
"""
API 통합 테스트: 주가 예측 이력 API

이 파일은 `/prediction/history` 엔드포인트에 대한 통합 테스트를 포함합니다.
`TestClient`를 사용하여 API 요청을 보내고, `real_db` fixture를 통해 실제 데이터베이스와의
상호작용을 검증합니다. 서비스나 다른 외부 API 호출에 대한 모의(Mock)는 사용하지 않습니다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from src.api.tests.helpers import create_test_user
from src.common.models.prediction_history import PredictionHistory


class TestPredictionHistoryRouter:
    """
    `/prediction/history` 라우터에 대한 통합 테스트 클래스.
    """

    @pytest.fixture(autouse=True)
    def setup_test_data(self, real_db: Session):
        """
        각 테스트 실행 전, `prediction_history` 테이블을 초기화하는 Fixture.

        - **목적**: 테스트 간의 독립성을 보장하기 위해, 매 테스트 시작 전에
                  모든 예측 이력 데이터를 삭제합니다.
        - **적용**: `autouse=True`로 설정되어 이 클래스의 모든 테스트 메서드에 자동으로 적용됩니다.
        """
        real_db.query(PredictionHistory).delete()
        real_db.commit()

    def _create_prediction_history(self, real_db: Session, user_id: int, symbol: str, prediction: str, created_at: datetime) -> PredictionHistory:
        """
        테스트용 예측 이력 데이터를 생성하는 헬퍼 메서드.

        - **목적**: 테스트 시나리오에 필요한 예측 이력 데이터를 DB에 생성합니다.
        - **반환**: 생성된 `PredictionHistory` 모델 객체를 반환합니다.
        """
        history = PredictionHistory(
            user_id=user_id,
            symbol=symbol,
            prediction=prediction,
            created_at=created_at
        )
        real_db.add(history)
        real_db.commit() # 데이터를 즉시 DB에 반영
        real_db.refresh(history)
        return history

    def test_get_prediction_history_success(self, client: TestClient, real_db: Session):
        """
        - **테스트 대상**: `GET /api/v1/prediction/history/{telegram_id}`
        - **목적**: 특정 사용자의 주가 예측 이력을 성공적으로 조회하는지 확인합니다.
        - **시나리오**:
            - 테스트용 사용자와 두 개의 예측 이력을 생성합니다.
            - 해당 사용자의 ID로 API를 호출합니다.
            - 200 OK 응답과 함께 2개의 이력이 최신순으로 정렬되어 반환되는지 확인합니다.
        - **Mock 대상**: 없음
        """
        # Given: 테스트 사용자 및 예측 이력 데이터 생성
        user = create_test_user(real_db, telegram_id=12345)
        self._create_prediction_history(real_db, user.id, "005930", "상승", datetime(2023, 1, 1, 10, 0, 0))
        self._create_prediction_history(real_db, user.id, "035720", "하락", datetime(2023, 1, 2, 11, 0, 0))

        # When: API 호출
        response = client.get(f"/api/v1/prediction/history/{user.telegram_id}")

        # Then: 결과 검증
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["history"]) == 2
        assert data["history"][0]["symbol"] == "035720"  # 최신 데이터가 먼저 오는지 확인

    def test_get_prediction_history_not_found_user(self, client: TestClient):
        """
        - **테스트 대상**: `GET /api/v1/prediction/history/{telegram_id}`
        - **목적**: 존재하지 않는 사용자에 대해 API 호출 시, 빈 목록을 정상적으로 반환하는지 확인합니다.
        - **시나리오**:
            - 존재하지 않는 사용자 ID(99999)로 API를 호출합니다.
            - 200 OK 응답과 함께 빈 이력 목록이 반환되는지 확인합니다.
        - **Mock 대상**: 없음
        """
        # When: 존재하지 않는 사용자 ID로 API 호출
        response = client.get("/api/v1/prediction/history/99999")

        # Then: 404 Not Found 대신 200 OK와 빈 리스트를 반환하는 것이 현재 정책
        assert response.status_code == 200
        assert response.json() == {"history": [], "total_count": 0, "page": 1, "page_size": 10}

    def test_get_prediction_history_empty(self, client: TestClient, real_db: Session):
        """
        - **테스트 대상**: `GET /api/v1/prediction/history/{telegram_id}`
        - **목적**: 예측 이력이 없는 사용자에 대해 API 호출 시, 빈 목록을 정상적으로 반환하는지 확인합니다.
        - **시나리오**:
            - 테스트 사용자를 생성하지만 예측 이력은 생성하지 않습니다.
            - 해당 사용자의 ID로 API를 호출합니다.
            - 200 OK 응답과 함께 빈 이력 목록이 반환되는지 확인합니다.
        - **Mock 대상**: 없음
        """
        # Given: 사용자만 생성
        user = create_test_user(real_db, telegram_id=12345)

        # When: API 호출
        response = client.get(f"/api/v1/prediction/history/{user.telegram_id}")

        # Then: 결과 검증
        assert response.status_code == 200
        assert response.json() == {"history": [], "total_count": 0, "page": 1, "page_size": 10}

    def test_get_prediction_history_pagination(self, client: TestClient, real_db: Session):
        """
        - **테스트 대상**: `GET /api/v1/prediction/history/{telegram_id}`
        - **목적**: 페이지네이션(페이지 번호, 페이지 크기) 기능이 정상적으로 동작하는지 확인합니다.
        - **시나리오**:
            - 14개의 예측 이력 데이터를 생성합니다.
            - 첫 번째 페이지(크기 5)를 요청하고, 5개의 데이터가 최신순으로 반환되는지 확인합니다.
            - 두 번째 페이지(크기 5)를 요청하고, 다음 5개의 데이터가 최신순으로 반환되는지 확인합니다.
        - **Mock 대상**: 없음
        """
        # Given: 14개의 테스트 데이터 생성
        user = create_test_user(real_db, telegram_id=12345)
        for i in range(1, 15):
            self._create_prediction_history(real_db, user.id, f"SYMBOL{i:02d}", "상승", datetime(2023, 1, i, 10, 0, 0))

        # When: 1페이지 요청 (페이지 크기 5)
        response_page1 = client.get(f"/api/v1/prediction/history/{user.telegram_id}?page=1&page_size=5")

        # Then: 1페이지 결과 검증
        assert response_page1.status_code == 200
        data1 = response_page1.json()
        assert data1["total_count"] == 14
        assert data1["page"] == 1
        assert len(data1["history"]) == 5
        assert data1["history"][0]["symbol"] == "SYMBOL14"

        # When: 2페이지 요청 (페이지 크기 5)
        response_page2 = client.get(f"/api/v1/prediction/history/{user.telegram_id}?page=2&page_size=5")

        # Then: 2페이지 결과 검증
        assert response_page2.status_code == 200
        data2 = response_page2.json()
        assert data2["total_count"] == 14
        assert data2["page"] == 2
        assert len(data2["history"]) == 5
        assert data2["history"][0]["symbol"] == "SYMBOL09"

    def test_get_prediction_history_filter_by_symbol(self, client: TestClient, real_db: Session):
        """
        - **테스트 대상**: `GET /api/v1/prediction/history/{telegram_id}`
        - **목적**: 특정 종목 코드로 예측 이력을 필터링하는 기능이 정상적으로 동작하는지 확인합니다.
        - **시나리오**:
            - 여러 종목의 예측 이력을 생성합니다.
            - 특정 종목 코드(`005930`)를 쿼리 파라미터로 전달하여 API를 호출합니다.
            - 해당 종목의 이력만 반환되는지 확인합니다.
        - **Mock 대상**: 없음
        """
        # Given: 다양한 예측 이력 데이터 생성
        user = create_test_user(real_db, telegram_id=12345)
        self._create_prediction_history(real_db, user.id, "005930", "상승", datetime(2023, 1, 1))
        self._create_prediction_history(real_db, user.id, "035720", "하락", datetime(2023, 1, 2))
        self._create_prediction_history(real_db, user.id, "005930", "유지", datetime(2023, 1, 3))

        # When: 특정 종목 코드로 필터링하여 API 호출
        response = client.get(f"/api/v1/prediction/history/{user.telegram_id}?symbol=005930")

        # Then: 결과 검증
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert all(r["symbol"] == "005930" for r in data["history"])

    def test_get_prediction_history_filter_by_prediction(self, client: TestClient, real_db: Session):
        """
        - **테스트 대상**: `GET /api/v1/prediction/history/{telegram_id}`
        - **목적**: 특정 예측 결과로 이력을 필터링하는 기능이 정상적으로 동작하는지 확인합니다.
        - **시나리오**:
            - 여러 예측 결과(상승, 하락, 유지)를 포함하는 이력을 생성합니다.
            - 특정 예측 결과(`상승`)를 쿼리 파라미터로 전달하여 API를 호출합니다.
            - 해당 예측 결과의 이력만 반환되는지 확인합니다.
        - **Mock 대상**: 없음
        """
        # Given: 다양한 예측 이력 데이터 생성
        user = create_test_user(real_db, telegram_id=12345)
        self._create_prediction_history(real_db, user.id, "005930", "상승", datetime(2023, 1, 1))
        self._create_prediction_history(real_db, user.id, "035720", "하락", datetime(2023, 1, 2))
        self._create_prediction_history(real_db, user.id, "005930", "유지", datetime(2023, 1, 3))

        # When: 특정 예측 결과로 필터링하여 API 호출
        response = client.get(f"/api/v1/prediction/history/{user.telegram_id}?prediction=상승")

        # Then: 결과 검증
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["history"][0]["prediction"] == "상승"

    def test_get_prediction_history_filter_by_symbol_and_prediction(self, client: TestClient, real_db: Session):
        """
        - **테스트 대상**: `GET /api/v1/prediction/history/{telegram_id}`
        - **목적**: 종목 코드와 예측 결과를 동시에 사용하여 이력을 필터링하는 기능이 정상 동작하는지 확인합니다.
        - **시나리오**:
            - 여러 예측 이력을 생성합니다.
            - 특정 종목 코드와 예측 결과를 쿼리 파라미터로 전달하여 API를 호출합니다.
            - 두 조건을 모두 만족하는 이력만 반환되는지 확인합니다.
        - **Mock 대상**: 없음
        """
        # Given: 다양한 예측 이력 데이터 생성
        user = create_test_user(real_db, telegram_id=12345)
        self._create_prediction_history(real_db, user.id, "005930", "상승", datetime(2023, 1, 1))
        self._create_prediction_history(real_db, user.id, "035720", "하락", datetime(2023, 1, 2))
        self._create_prediction_history(real_db, user.id, "005930", "유지", datetime(2023, 1, 3))

        # When: 종목 코드와 예측 결과로 필터링하여 API 호출
        response = client.get(f"/api/v1/prediction/history/{user.telegram_id}?symbol=005930&prediction=유지")

        # Then: 결과 검증
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["history"][0]["symbol"] == "005930"
        assert data["history"][0]["prediction"] == "유지"