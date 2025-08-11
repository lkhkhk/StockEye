import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes
import os

# 테스트 대상 핸들러 임포트
from src.bot.handlers.help import help_command

# ADMIN_ID를 테스트용으로 설정 (실제 환경 변수와 분리)
TEST_ADMIN_ID = "123456789"

class TestHelpHandler:
    def setup_method(self):
        """각 테스트 메서드 실행 전에 호출되어 mock 객체들을 초기화합니다."""
        self.update = AsyncMock(spec=Update)
        self.context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Mock message 및 reply_text 설정
        self.update.message = AsyncMock(spec=Message)
        self.update.message.reply_text = AsyncMock()
        
        # Mock effective_chat 설정
        self.update.effective_chat = MagicMock(spec=Chat)
        self.update.effective_chat.id = 12345 # 테스트용 chat_id

        # Mock effective_user 설정
        self.update.effective_user = MagicMock(spec=User)
        
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"TELEGRAM_ADMIN_ID": TEST_ADMIN_ID}) # 환경 변수 패치
    async def test_help_command_user(self):
        """일반 사용자가 /help 명령어를 입력했을 때 올바른 도움말을 받는지 테스트합니다."""
        self.update.effective_user.id = "987654321" # 일반 사용자 ID
        
        await help_command(self.update, self.context)
        
        # reply_text의 호출 인자를 캡처하여 예상되는 문자열과 비교
        self.update.message.reply_text.assert_called_once()
        called_text = self.update.message.reply_text.call_args[0][0]
        assert "[StockEye 봇 도움말]" in called_text
        assert "/register" in called_text
        assert "[관리자 전용 명령어 안내]" not in called_text

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"TELEGRAM_ADMIN_ID": TEST_ADMIN_ID}) # 환경 변수 패치
    async def test_help_command_admin(self):
        """관리자가 /help 명령어를 입력했을 때 관리자용 도움말을 받는지 테스트합니다."""
        self.update.effective_user.id = TEST_ADMIN_ID # 관리자 ID
        
        await help_command(self.update, self.context)
        
        # reply_text의 호출 인자를 캡처하여 예상되는 문자열과 비교
        self.update.message.reply_text.assert_called_once()
        called_text = self.update.message.reply_text.call_args[0][0]
        assert "[StockEye 봇 도움말]" in called_text
        assert "/register" in called_text
        assert "[관리자 전용]" in called_text
