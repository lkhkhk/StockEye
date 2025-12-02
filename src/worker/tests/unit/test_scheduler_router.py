import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from fastapi import FastAPI

from src.worker.routers.scheduler import router, TriggerJobRequest, HistoricalPriceUpdateRequest


# Create a test app
app = FastAPI()
app.include_router(router, prefix="/api/v1")
client = TestClient(app)


class TestSchedulerRouter:
    """Scheduler Router 엔드포인트 테스트"""

    @patch('src.worker.routers.scheduler.scheduler')
    def test_get_scheduler_status_running(self, mock_scheduler):
        """스케줄러 상태 조회 - 실행 중"""
        # GIVEN
        mock_scheduler.running = True
        
        # Mock job objects
        mock_job1 = MagicMock()
        mock_job1.id = "update_stock_master_job"
        mock_job1.name = "종목 마스터 갱신"
        mock_job1.next_run_time = datetime(2025, 12, 2, 7, 0, 0, tzinfo=timezone.utc)
        mock_job1.trigger = "cron[hour='7', minute='0']"
        
        mock_job2 = MagicMock()
        mock_job2.id = "check_price_alerts_job"
        mock_job2.name = "가격 알림 확인"
        mock_job2.next_run_time = datetime(2025, 12, 2, 19, 15, 0, tzinfo=timezone.utc)
        mock_job2.trigger = "interval[0:01:00]"
        
        mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]

        # WHEN
        response = client.get("/api/v1/scheduler/status")

        # THEN
        assert response.status_code == 200
        data = response.json()
        assert data["is_running"] is True
        assert len(data["jobs"]) == 2
        assert data["jobs"][0]["id"] == "update_stock_master_job"
        assert data["jobs"][0]["name"] == "종목 마스터 갱신"
        assert data["jobs"][1]["id"] == "check_price_alerts_job"
        mock_scheduler.get_jobs.assert_called_once()

    @patch('src.worker.routers.scheduler.scheduler')
    def test_get_scheduler_status_not_running(self, mock_scheduler):
        """스케줄러 상태 조회 - 실행 중이 아님"""
        # GIVEN
        mock_scheduler.running = False

        # WHEN
        response = client.get("/api/v1/scheduler/status")

        # THEN
        assert response.status_code == 200
        data = response.json()
        assert data["is_running"] is False
        assert data["jobs"] == []

    @patch('src.worker.routers.scheduler.scheduler')
    def test_trigger_scheduler_job_success(self, mock_scheduler):
        """스케줄러 작업 수동 트리거 - 성공"""
        # GIVEN
        mock_job = MagicMock()
        mock_job.id = "check_price_alerts_job"
        mock_job.name = "가격 알림 확인"
        mock_job.next_run_time = datetime(2025, 12, 2, 19, 15, 0, tzinfo=timezone.utc)
        mock_job.kwargs = {}
        mock_job.modify = MagicMock()
        
        mock_scheduler.get_job.return_value = mock_job

        # WHEN
        response = client.post(
            "/api/v1/scheduler/trigger/check_price_alerts_job",
            json={"chat_id": 12345}
        )

        # THEN
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "check_price_alerts_job"
        assert "triggered to run now" in data["message"]
        assert "triggered_at" in data
        
        mock_scheduler.get_job.assert_called_once_with("check_price_alerts_job")
        mock_job.modify.assert_called_once()
        
        # Verify chat_id was added to kwargs
        call_kwargs = mock_job.modify.call_args[1]
        assert call_kwargs["kwargs"]["chat_id"] == 12345

    @patch('src.worker.routers.scheduler.scheduler')
    def test_trigger_scheduler_job_not_found(self, mock_scheduler):
        """스케줄러 작업 수동 트리거 - 작업을 찾을 수 없음"""
        # GIVEN
        mock_scheduler.get_job.return_value = None

        # WHEN
        response = client.post(
            "/api/v1/scheduler/trigger/nonexistent_job",
            json={"chat_id": 12345}
        )

        # THEN
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
        mock_scheduler.get_job.assert_called_once_with("nonexistent_job")

    @patch('src.worker.routers.scheduler.scheduler')
    def test_trigger_scheduler_job_without_chat_id(self, mock_scheduler):
        """스케줄러 작업 수동 트리거 - chat_id 없이"""
        # GIVEN
        mock_job = MagicMock()
        mock_job.id = "update_stock_master_job"
        mock_job.next_run_time = datetime(2025, 12, 2, 7, 0, 0, tzinfo=timezone.utc)
        mock_job.kwargs = {}
        mock_job.modify = MagicMock()
        
        mock_scheduler.get_job.return_value = mock_job

        # WHEN
        response = client.post(
            "/api/v1/scheduler/trigger/update_stock_master_job",
            json={}
        )

        # THEN
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "update_stock_master_job"
        
        # Verify kwargs were not modified (no chat_id added)
        call_kwargs = mock_job.modify.call_args[1]
        assert "chat_id" not in call_kwargs["kwargs"]

    @patch('src.worker.main.run_historical_price_update_task')
    @patch('src.worker.routers.scheduler.asyncio.create_task')
    def test_trigger_historical_prices_update_success(self, mock_create_task, mock_run_task):
        """과거 일별 시세 갱신 트리거 - 성공"""
        # GIVEN
        request_data = {
            "chat_id": 12345,
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "stock_identifier": "005930"
        }

        # WHEN
        response = client.post(
            "/api/v1/scheduler/trigger_historical_prices_update",
            json=request_data
        )

        # THEN
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "triggered"
        assert "성공적으로 트리거" in data["message"]
        
        # Verify asyncio.create_task was called
        mock_create_task.assert_called_once()

    def test_trigger_historical_prices_update_invalid_date_format(self):
        """과거 일별 시세 갱신 트리거 - 잘못된 날짜 형식"""
        # GIVEN
        request_data = {
            "chat_id": 12345,
            "start_date": "invalid-date",
            "end_date": "2023-12-31"
        }

        # WHEN
        response = client.post(
            "/api/v1/scheduler/trigger_historical_prices_update",
            json=request_data
        )

        # THEN
        assert response.status_code == 400
        assert "날짜 형식" in response.json()["detail"]

    @patch('src.worker.main.run_historical_price_update_task')
    @patch('src.worker.routers.scheduler.asyncio.create_task')
    def test_trigger_historical_prices_update_without_stock_identifier(self, mock_create_task, mock_run_task):
        """과거 일별 시세 갱신 트리거 - stock_identifier 없이 (전체 종목)"""
        # GIVEN
        request_data = {
            "chat_id": 12345,
            "start_date": "2023-01-01",
            "end_date": "2023-12-31"
        }

        # WHEN
        response = client.post(
            "/api/v1/scheduler/trigger_historical_prices_update",
            json=request_data
        )

        # THEN
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "triggered"
        mock_create_task.assert_called_once()
