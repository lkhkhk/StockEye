import pytest
import httpx
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.bot.handlers.predict import predict_command
from src.bot.handlers.natural import natural_message_handler

# --- Constants ---
API_URL = f"http://stockeye-api:8000/api/v1"
TEST_USER_ID_PREDICT = 12345
TEST_USER_ID_NATURAL = 54321

# --- Fixtures ---

@pytest.fixture(scope="module", autouse=True)
async def setup_e2e_environment():
    """E2E 테스트 모듈 시작 시 DB를 초기화하고 환경 변수를 설정합니다."""
    print("\n--- E2E 테스트 환경 설정 시작 ---")
    # 1. DB 초기화 및 시딩
    async with httpx.AsyncClient() as client:
        try:
            print("DB 초기화 및 데이터 시딩을 요청합니다...")
            response = await client.post(f"{API_URL}/admin/debug/reset-database", timeout=20)
            response.raise_for_status()
            print(f"DB 초기화 완료: {response.json()}")
        except httpx.RequestError as e:
            pytest.fail(f"API 서버 연결 실패: {e}. 테스트를 진행할 수 없습니다.")

    # 2. 환경 변수 설정
    os.environ["API_HOST"] = "stockeye-api"
    
    yield
    
    # 3. 테스트 종료 후 정리
    del os.environ["API_HOST"]
    print("\n--- E2E 테스트 환경 설정 종료 ---")

@pytest.fixture
def mock_update_context():
    """Mock Update 및 Context 객체를 생성합니다."""
    update = MagicMock()
    context = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.effective_user = MagicMock()
    return update, context

# --- Helper Functions ---

async def get_prediction_history(user_id):
    """API를 통해 특정 사용자의 예측 이력을 가져옵니다."""
    async with httpx.AsyncClient() as client:
        await asyncio.sleep(0.5) # DB 반영 시간 대기
        response = await client.get(f"{API_URL}/prediction/history/{user_id}", timeout=10)
        response.raise_for_status()
        return response.json()

# --- E2E Tests ---

@pytest.mark.asyncio
async def test_predict_command_e2e(mock_update_context):
    """E2E Test: /predict 명령어가 예측을 수행하고 이력을 올바르게 저장하는지 검증합니다."""
    # Given
    update, context = mock_update_context
    symbol = "005930"  # 삼성전자
    user_id = TEST_USER_ID_PREDICT
    update.effective_user.id = user_id
    context.args = [symbol]

    # When
    print(f"\n[E2E] Executing /predict for user {user_id}...")
    await predict_command(update, context)

    # Then
    update.message.reply_text.assert_called_once()
    bot_response = update.message.reply_text.call_args[0][0]
    print(f"[E2E] Bot response: {bot_response}")
    assert "예측 결과" in bot_response
    assert "예측 불가" not in bot_response

    history_response = await get_prediction_history(user_id) # 변수명 변경
    print(f"[E2E] History for user {user_id}: {history_response}")
    assert len(history_response['history']) > 0 # 'history' 키의 리스트 길이 확인
    assert history_response['history'][0]["symbol"] == symbol
    assert history_response['history'][0]["telegram_id"] == user_id

@pytest.mark.asyncio
async def test_natural_handler_e2e(mock_update_context):
    """E2E Test: 자연어 처리가 예측을 수행하고 이력을 올바르게 저장하는지 검증합니다."""
    # Given
    update, context = mock_update_context
    user_id = TEST_USER_ID_NATURAL
    update.effective_user.id = user_id
    update.message.text = "삼성전자 주가 예측해줘"

    # When
    print(f"\n[E2E] Executing natural language query for user {user_id}...")
    await natural_message_handler(update, context)

    # Then
    update.message.reply_text.assert_called_once()
    bot_response = update.message.reply_text.call_args[0][0]
    print(f"[E2E] Bot response: {bot_response}")
    assert "예측 결과" in bot_response
    assert "찾을 수 없습니다" not in bot_response

    history_response = await get_prediction_history(user_id) # 변수명 변경
    print(f"[E2E] History for user {user_id}: {history_response}")
    assert len(history_response['history']) > 0 # 'history' 키의 리스트 길이 확인
    assert history_response['history'][0]["symbol"] == "005930" # 'history' 키의 리스트 첫 번째 요소 접근
    assert history_response['history'][0]["telegram_id"] == user_id