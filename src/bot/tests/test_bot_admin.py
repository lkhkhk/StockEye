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
    admin_stats,
    API_URL
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
        
        # Mock context.bot.send_message 설정
        self.context.bot = AsyncMock()
        self.context.bot.send_message = AsyncMock()
        
        # effective_chat.id 모의
        self.update.effective_chat = MagicMock(spec=Chat)
        self.update.effective_chat.id = 12345 # 테스트용 chat_id

    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.run_update_master_and_notify')
    async def test_admin_update_master_success(self, mock_run_update_master_and_notify):
        """종목마스터 갱신 성공 테스트"""
        await admin_update_master(self.update, self.context)
        
        self.context.bot.send_message.assert_called_once_with(chat_id=self.update.effective_chat.id, text="종목마스터 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다.")
        mock_run_update_master_and_notify.assert_called_once_with(self.context, self.update.effective_chat.id)

    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.run_update_master_and_notify')
    async def test_admin_update_master_failure(self, mock_run_update_master_and_notify):
        """종목마스터 갱신 실패 테스트"""
        mock_run_update_master_and_notify.side_effect = Exception("Test Error")

        await admin_update_master(self.update, self.context)
        
        self.context.bot.send_message.assert_called_once_with(chat_id=self.update.effective_chat.id, text="종목마스터 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다.")
        mock_run_update_master_and_notify.assert_called_once_with(self.context, self.update.effective_chat.id)

    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.run_update_price_and_notify')
    async def test_admin_update_price_success(self, mock_run_update_price_and_notify):
        """일별시세 갱신 성공 테스트"""
        await admin_update_price(self.update, self.context)
        
        self.context.bot.send_message.assert_called_once_with(chat_id=self.update.effective_chat.id, text="일별시세 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다.")
        mock_run_update_price_and_notify.assert_called_once_with(self.context, self.update.effective_chat.id)
    
    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.session.get')
    async def test_admin_show_schedules_success(self, mock_get):
        """스케줄러 상태 조회 성공 테스트"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [ # API 응답이 리스트 형태
            {
                "id": "sample_job",
                "next_run_time": "2025-01-20T10:01:00",
                "trigger": "interval[0:01:00]"
            }
        ]
        mock_get.return_value = mock_response
        
        await admin_show_schedules(self.update, self.context)
        
        mock_get.assert_called_once_with(f"{API_URL}/admin/schedules", timeout=10)
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "스케줄러 잡 목록" in call_args
        assert "sample_job" in call_args
    
    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.session.post')
    async def test_admin_trigger_job_success(self, mock_post):
        """잡 수동 실행 성공 테스트"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "Job 'update_master_job'가 수동으로 실행되었습니다."
        }
        mock_post.return_value = mock_response
        
        self.update.message.text = "/trigger_job update_master_job"
        
        await admin_trigger_job(self.update, self.context)
        
        mock_post.assert_called_once_with(f"{API_URL}/admin/trigger-job/update_master_job", timeout=10)
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "✅ 잡 실행 완료!" in call_args
        assert "🔧 잡 ID: Job 'update_master_job'가 수동으로 실행되었습니다." in call_args
    
    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.session.post')
    async def test_admin_trigger_job_invalid_job(self, mock_post):
        """존재하지 않는 잡 실행 테스트"""
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response
        
        self.update.message.text = "/trigger_job nonexistent_job"
        
        await admin_trigger_job(self.update, self.context)
        
        mock_post.assert_called_once_with(f"{API_URL}/admin/trigger-job/nonexistent_job", timeout=10)
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "❌ 잡을 찾을 수 없습니다: nonexistent_job" in call_args
    
    @pytest.mark.asyncio
    async def test_admin_trigger_job_no_job_id(self):
        """잡 ID가 없는 경우 테스트"""
        self.update.message.text = "/trigger_job"
        
        await admin_trigger_job(self.update, self.context)
        
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "❌ 사용법: /trigger_job job_id" in call_args
    
    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.session.get')
    async def test_admin_stats_success(self, mock_get):
        """관리자 통계 조회 성공 테스트"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_users": 5,
            "total_simulated_trades": 25,
            "total_predictions": 15
        }
        mock_get.return_value = mock_response
        
        await admin_stats(self.update, self.context)
        
        mock_get.assert_called_once_with(f"{API_URL}/admin/stats", timeout=10)
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0][0]
        assert "📊 **시스템 통계**" in call_args
        assert "👥 사용자 수: 5명" in call_args
        assert "💰 모의매매 기록: 25건" in call_args
        assert "🔮 예측 기록: 15건" in call_args