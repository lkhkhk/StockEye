import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from src.bot.handlers.admin import (
    admin_only,
    admin_command,
    health_command,
    admin_update_master,
    run_update_master_and_notify,
    admin_stats,
)

# Helper to create a mock response
def create_mock_response(status_code, json_data=None, text_data=""):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json = AsyncMock(return_value=json_data)
    mock_response.text = text_data
    mock_response.request = MagicMock()

    def raise_for_status():
        if mock_response.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP Error {mock_response.status_code}", 
                request=mock_response.request, 
                response=mock_response
            )
    mock_response.raise_for_status = MagicMock(side_effect=raise_for_status)
    return mock_response


@pytest.mark.asyncio
async def test_admin_only_decorator_not_admin():
    """admin_only 데코레이터: 관리자가 아닌 경우"""
    mock_func = AsyncMock()
    decorated_func = admin_only(mock_func)
    update = AsyncMock()
    update.effective_user.id = 12345
    context = AsyncMock()

    with patch('src.bot.handlers.admin.ADMIN_ID', '54321'):
        await decorated_func(update, context)

        context.bot.send_message.assert_called_once_with(
            chat_id=update.effective_chat.id, text="관리자 전용 명령어입니다."
        )
        mock_func.assert_not_called()

@pytest.mark.asyncio
async def test_admin_only_decorator_is_admin():
    """admin_only 데코레이터: 관리자인 경우"""
    mock_func = AsyncMock()
    decorated_func = admin_only(mock_func)
    update = AsyncMock()
    admin_user_id = 12345
    update.effective_user.id = admin_user_id
    context = AsyncMock()

    with patch('src.bot.handlers.admin.ADMIN_ID', str(admin_user_id)):
        await decorated_func(update, context)
        mock_func.assert_called_once_with(update, context)

@pytest.mark.asyncio
async def test_admin_command_as_admin():
    """/admin 명령어 (관리자 권한) 테스트"""
    update = AsyncMock()
    context = AsyncMock()
    update.effective_user.id = 12345

    with patch('src.bot.handlers.admin.ADMIN_ID', '12345'):
        await admin_command(update, context)
        update.message.reply_text.assert_called_once()
        sent_text = update.message.reply_text.call_args[0][0]
        assert "[관리자 전용 명령어 안내]" in sent_text

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get')
async def test_health_command_success(mock_get):
    """/health 명령어 성공 테스트"""
    update = AsyncMock()
    context = AsyncMock()
    mock_get.return_value = create_mock_response(200, {"status": "ok"})

    await health_command(update, context)
    update.message.reply_text.assert_called_once_with("서비스 상태: ok")

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get')
async def test_health_command_failure_http_error(mock_get):
    """/health 명령어 실패 (HTTP 오류) 테스트"""
    update = AsyncMock()
    context = AsyncMock()
    mock_get.return_value = create_mock_response(500)
    
    await health_command(update, context)
    update.message.reply_text.assert_called_once_with("헬스체크에 실패했습니다. 서버 상태를 확인해주세요.")

@pytest.mark.asyncio
async def test_admin_update_master_starts_task():
    """/update_master 명령어: 비동기 작업 시작 테스트"""
    update = AsyncMock()
    context = AsyncMock()

    with patch('asyncio.create_task') as mock_create_task:
        await admin_update_master(update, context)
        context.bot.send_message.assert_called_once_with(
            chat_id=update.effective_chat.id, text="종목마스터 갱신을 시작합니다. 완료되면 결과를 안내드리겠습니다."
        )
        mock_create_task.assert_called_once()

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post')
async def test_run_update_master_and_notify_success(mock_post):
    """run_update_master_and_notify 비동기 작업 성공 테스트"""
    context = AsyncMock()
    chat_id = 12345
    mock_post.return_value = create_mock_response(200, {"updated_count": 10, "timestamp": "2025-08-12"})

    await run_update_master_and_notify(context, chat_id)
    context.bot.send_message.assert_called_once()
    sent_text = context.bot.send_message.call_args[1]['text']
    assert "✅ 종목마스터 갱신 완료!" in sent_text

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post')
async def test_run_update_master_and_notify_failure(mock_post):
    """run_update_master_and_notify 비동기 작업 실패 테스트"""
    context = AsyncMock()
    chat_id = 12345
    mock_post.return_value = create_mock_response(500)

    await run_update_master_and_notify(context, chat_id)
    context.bot.send_message.assert_called_once_with(chat_id=chat_id, text="❌ 갱신 실패: 500")

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get')
async def test_admin_stats_success(mock_get):
    """/admin_stats 명령어 성공 테스트"""
    update = AsyncMock()
    context = AsyncMock()
    stats_data = {"user_count": 100, "trade_count": 50, "prediction_count": 200}
    mock_get.return_value = create_mock_response(200, stats_data)

    await admin_stats(update, context)
    update.message.reply_text.assert_called_once()
    sent_text = update.message.reply_text.call_args[0][0]
    assert "📊 **시스템 통계**" in sent_text

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get')
async def test_admin_stats_failure(mock_get):
    """/admin_stats 명령어 실패 테스트"""
    update = AsyncMock()
    context = AsyncMock()
    mock_get.return_value = create_mock_response(500)

    await admin_stats(update, context)
    update.message.reply_text.assert_called_once_with("❌ 조회 실패: 500")
