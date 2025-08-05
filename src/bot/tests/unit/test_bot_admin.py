import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes

from src.bot.handlers import admin
from src.bot.handlers.admin import API_URL

class TestBotAdmin:
    """관리자 봇 명령어 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.update = AsyncMock(spec=Update)
        self.context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        self.update.message = AsyncMock(spec=Message)
        self.update.message.reply_text = AsyncMock()
        self.context.bot = AsyncMock()
        self.context.bot.send_message = AsyncMock()
        self.update.effective_chat = MagicMock(spec=Chat)
        self.update.effective_chat.id = 12345
        self.update.effective_user = MagicMock(spec=User)
        self.update.effective_user.id = '12345'

    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.asyncio.create_task')
    @patch('src.bot.handlers.admin.ADMIN_ID', '12345')
    async def test_admin_update_master_success(self, mock_create_task):
        """종목마스터 갱신 성공 테스트"""
        await admin.admin_update_master(self.update, self.context)
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            text="종목마스터 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다."
        )
        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.http_client.session.post')
    async def test_run_update_master_and_notify_failure(self, mock_post):
        """종목마스터 갱신 실패(비동기) 테스트"""
        mock_post.side_effect = Exception("Test Error")
        await admin.run_update_master_and_notify(self.context, self.update.effective_chat.id)
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            text="오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.asyncio.create_task')
    @patch('src.bot.handlers.admin.ADMIN_ID', '12345')
    async def test_admin_update_price_success(self, mock_create_task):
        """일별시세 갱신 성공 테스트"""
        await admin.admin_update_price(self.update, self.context)
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            text="일별시세 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다."
        )
        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.common.http_client.session.post')
    async def test_run_update_price_and_notify_failure(self, mock_post):
        """일별시세 갱신 실패(비동기) 테스트"""
        mock_post.side_effect = Exception("Price Update Error")
        await admin.run_update_price_and_notify(self.context, self.update.effective_chat.id)
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            text="오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )

    @pytest.mark.asyncio
    @patch('src.common.http_client.session.get')
    @patch('src.bot.handlers.admin.ADMIN_ID', '12345')
    async def test_admin_show_schedules_success(self, mock_get):
        """스케줄러 상태 조회 성공 테스트"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jobs": [{"id": "sample_job", "next_run_time": "2025-01-20T10:01:00", "trigger": "interval[0:01:00]"}]
        }
        mock_get.return_value = mock_response
        await admin.admin_show_schedules(self.update, self.context)
        mock_get.assert_called_once_with(f"{API_URL}/admin/schedule/status", timeout=10)
        expected_message = "⏰ **스케줄러 잡 목록**\n\n- **ID:** `sample_job`\n  **다음 실행:** `2025-01-20T10:01:00`\n  **트리거:** `interval[0:01:00]`\n"
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id, text=expected_message, parse_mode='Markdown'
        )

    @pytest.mark.asyncio
    @patch('src.common.http_client.session.post')
    @patch('src.bot.handlers.admin.ADMIN_ID', '12345')
    async def test_admin_trigger_job_success(self, mock_post):
        """잡 수동 실행 성공 테스트"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"job_id": "update_master_job", "message": "Job 'update_master_job'가 수동으로 실행되었습니다."}
        mock_post.return_value = mock_response
        self.update.message.text = "/trigger_job update_master_job"
        await admin.admin_trigger_job(self.update, self.context)
        mock_post.assert_called_once_with(f"{API_URL}/admin/schedule/trigger/update_master_job", timeout=10)
        expected_message = "✅ 잡 실행 완료!\n🔧 잡 ID: update_master_job\n💬 메시지: Job 'update_master_job'가 수동으로 실행되었습니다."
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id, text=expected_message
        )

    @pytest.mark.asyncio
    @patch('src.common.http_client.session.post')
    @patch('src.bot.handlers.admin.ADMIN_ID', '12345')
    async def test_admin_trigger_job_invalid_job(self, mock_post):
        """존재하지 않는 잡 실행 테스트"""
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response
        self.update.message.text = "/trigger_job nonexistent_job"
        await admin.admin_trigger_job(self.update, self.context)
        mock_post.assert_called_once_with(f"{API_URL}/admin/schedule/trigger/nonexistent_job", timeout=10)
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id, text="❌ 잡을 찾을 수 없습니다: nonexistent_job"
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.ADMIN_ID', '12345')
    async def test_admin_trigger_job_no_job_id(self):
        """잡 ID가 없는 경우 테스트"""
        self.update.message.text = "/trigger_job"
        await admin.admin_trigger_job(self.update, self.context)
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id, text="❌ 사용법: /trigger_job job_id\n예시: /trigger_job update_master_job"
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.admin.ADMIN_ID', 'not_admin')
    async def test_admin_command_unauthorized(self):
        """관리자가 아닌 사용자가 관리자 명령어 시도"""
        await admin.admin_show_schedules(self.update, self.context) # admin_only가 적용된 함수로 변경
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id, text="관리자 전용 명령어입니다."
        )

    @pytest.mark.asyncio
    @patch('src.common.http_client.session.get')
    @patch('src.bot.handlers.admin.ADMIN_ID', '12345')
    async def test_admin_stats_success(self, mock_get):
        """관리자 통계 조회 성공 테스트"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"user_count": 5, "trade_count": 25, "prediction_count": 15}
        mock_get.return_value = mock_response
        await admin.admin_stats(self.update, self.context)
        mock_get.assert_called_once_with(f"{API_URL}/admin/admin_stats", timeout=10)
        expected_message = "📊 **시스템 통계**\n\n👥 사용자 수: 5명\n💰 모의매매 기록: 25건\n🔮 예측 기록: 15건"
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id, text=expected_message, parse_mode='Markdown'
        )
