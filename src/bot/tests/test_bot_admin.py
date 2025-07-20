import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.bot.handlers.admin import (
    admin_update_master, 
    admin_update_price, 
    admin_show_schedules, 
    admin_trigger_job, 
    admin_stats
)

class TestBotAdmin:
    """관리자 봇 명령어 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.update = AsyncMock(spec=Update)
        self.context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Mock message 설정
        self.update.message = AsyncMock(spec=Message)
        self.update.message.reply_text = AsyncMock()
        
    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.requests.post')
    async def test_admin_update_master_success(self, mock_post):
        """종목마스터 갱신 성공 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "updated_count": 10,
            "timestamp": "2025-01-20T10:00:00"
        }
        mock_post.return_value = mock_response
        
        # 함수 실행
        await admin_update_master(self.update, self.context)
        
        # 검증
        mock_post.assert_called_once_with("http://api:8000/admin/update_master")
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "✅ 종목마스터 갱신 완료!" in call_args
        assert "📊 처리된 종목: 10개" in call_args
    
    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.requests.post')
    async def test_admin_update_master_failure(self, mock_post):
        """종목마스터 갱신 실패 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        # 함수 실행
        await admin_update_master(self.update, self.context)
        
        # 검증
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "❌ 갱신 실패: 500" in call_args
    
    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.requests.post')
    async def test_admin_update_price_success(self, mock_post):
        """일별시세 갱신 성공 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "updated_count": 150,
            "timestamp": "2025-01-20T10:00:00"
        }
        mock_post.return_value = mock_response
        
        # 함수 실행
        await admin_update_price(self.update, self.context)
        
        # 검증
        mock_post.assert_called_once_with("http://api:8000/admin/update_price")
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "✅ 일별시세 갱신 완료!" in call_args
        assert "📊 처리된 데이터: 150개" in call_args
    
    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.requests.get')
    async def test_admin_show_schedules_success(self, mock_get):
        """스케줄러 상태 조회 성공 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": {
                "scheduler_running": True,
                "job_count": 3,
                "jobs": [
                    {
                        "id": "sample_job",
                        "next_run_time": "2025-01-20T10:01:00",
                        "trigger": "interval[0:01:00]"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        # 함수 실행
        await admin_show_schedules(self.update, self.context)
        
        # 검증
        mock_get.assert_called_once_with("http://api:8000/admin/schedule/status")
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "스케줄러 상태" in call_args
        assert "실행 상태: 실행중" in call_args
        assert "등록된 잡: 3개" in call_args
    
    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.requests.post')
    async def test_admin_trigger_job_success(self, mock_post):
        """잡 수동 실행 성공 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "update_master_job",
            "timestamp": "2025-01-20T10:00:00"
        }
        mock_post.return_value = mock_response
        
        # Mock message text 설정
        self.update.message.text = "/trigger_job update_master_job"
        
        # 함수 실행
        await admin_trigger_job(self.update, self.context)
        
        # 검증
        mock_post.assert_called_once_with("http://api:8000/admin/schedule/trigger/update_master_job")
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "✅ 잡 실행 완료!" in call_args
        assert "🔧 잡 ID: update_master_job" in call_args
    
    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.requests.post')
    async def test_admin_trigger_job_invalid_job(self, mock_post):
        """존재하지 않는 잡 실행 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response
        
        # Mock message text 설정
        self.update.message.text = "/trigger_job nonexistent_job"
        
        # 함수 실행
        await admin_trigger_job(self.update, self.context)
        
        # 검증
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "❌ 잡을 찾을 수 없습니다: nonexistent_job" in call_args
    
    @pytest.mark.asyncio
    async def test_admin_trigger_job_no_job_id(self):
        """잡 ID가 없는 경우 테스트"""
        # Mock message text 설정
        self.update.message.text = "/trigger_job"
        
        # 함수 실행
        await admin_trigger_job(self.update, self.context)
        
        # 검증
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "❌ 사용법: /trigger_job job_id" in call_args
    
    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.requests.get')
    async def test_admin_stats_success(self, mock_get):
        """관리자 통계 조회 성공 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "user_count": 5,
            "trade_count": 25,
            "prediction_count": 15
        }
        mock_get.return_value = mock_response
        
        # 함수 실행
        await admin_stats(self.update, self.context)
        
        # 검증
        mock_get.assert_called_once_with("http://api:8000/admin/admin_stats")
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "📊 **시스템 통계**" in call_args
        assert "👥 사용자 수: 5명" in call_args
        assert "💰 모의매매 기록: 25건" in call_args
        assert "🔮 예측 기록: 15건" in call_args 