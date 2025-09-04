import pytest
from unittest.mock import AsyncMock, patch

from telegram import Update, User
from telegram.ext import ContextTypes

from src.bot.handlers.help import help_command

@pytest.mark.asyncio
@patch('os.getenv')
async def test_help_command_user(mock_getenv):
    """Tests the /help command for a regular user."""
    # 1. Setup Mocks
    mock_getenv.return_value = "admin_id" # Ensure user is not admin

    update = AsyncMock(spec=Update)
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    
    update.effective_user = AsyncMock(spec=User)
    update.effective_user.id = 12345 # A regular user ID

    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()

    # 2. Execute the handler
    await help_command(update, context)

    # 3. Verify the response
    update.message.reply_text.assert_called_once()
    sent_text = update.message.reply_text.call_args.args[0]

    expected_text = (
        "[StockEye 봇 도움말]\n"
        "\n"
        "**계정 관리**\n"
        "- /register : 알림 수신 동의 (텔레그램 알림 활성화)\n"
        "- /unregister : 알림 수신 동의 해제 (텔레그램 알림 비활성화)\n"
        "\n"
        "**주식 정보 조회**\n"
        "- /symbols : 전체 주식 종목 목록 조회\n"
        "- /symbols_search [키워드] : 키워드로 주식 종목 검색 (예: /symbols_search 삼성)\n"
        "- /symbol_info [종목코드] : 특정 종목 상세 정보 조회 (예: /symbol_info 005930)\n"
        "\n"
        "**주가 예측**\n"
        "- /predict [종목코드] : 특정 종목의 주가 등락 예측 (예: /predict 005930)\n"
        "\n"
        "**관심 종목**\n"
        "- /watchlist_add [종목코드] : 관심 종목 추가 (예: /watchlist_add 005930)\n"
        "- /watchlist_remove [종목코드] : 관심 종목 삭제 (예: /watchlist_remove 005930)\n"
        "- /watchlist_get : 나의 관심 종목 목록 조회\n"
        "\n"
        "**알림 관리**\n"
        "- /alert [명령] : 가격 및 공시 알림을 관리합니다.\n"
        "  - `add [종목명]`: 새 알림 추가\n"
        "  - `list`: 나의 알림 목록 보기\n"
        "  - `delete [번호]`: 알림 삭제\n"
        "  - `pause [번호]`: 알림 일시정지\n"
        "  - `resume [번호]`: 알림 다시시작\n"
        "\n"
        "**모의 거래**\n"
        "- /trade_simulate [buy|sell] [종목코드] [수량] [가격] : 모의 거래 기록 (예: /trade_simulate buy 005930 10 75000)\n"
        "- /trade_history : 나의 모의 거래 내역 조회\n"
        "\n"
        "**기타**\n"
        "- /start : 봇 시작 메시지\n"
        "- /help : 이 도움말 메시지\n"
        "\n"
        "**자연어 질의 예시:**\n"
        "- \"삼성전자 얼마야?\"\n"
        "- \"005930 예측해줘\"\n"
        "- \"카카오 오를까?\"\n"
    )

    assert sent_text == expected_text
