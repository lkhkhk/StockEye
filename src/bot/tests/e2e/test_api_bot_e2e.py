import pytest
from unittest.mock import AsyncMock, MagicMock
import os
import httpx
from src.bot.handlers.alert import set_price_alert, list_alerts, delete_alert
from src.common.models.stock_master import StockMaster
from src.common.database.db_connector import get_db
from sqlalchemy.orm import Session

# Mock user and chat IDs for testing
TEST_USER_ID = 12345
TEST_CHAT_ID = 12345
API_HOST = "stockeye-api"
API_URL = f"http://{API_HOST}:8000/api/v1"

@pytest.fixture(autouse=True)
def setup_environment():
    """Sets up environment variables for tests."""
    os.environ["API_HOST"] = API_HOST
    yield
    # Clean up environment variables if necessary
    if "API_HOST" in os.environ:
        del os.environ["API_HOST"]

@pytest.fixture(autouse=True)
def setup_stock_data():
    db: Session = next(get_db())
    # Check if stock already exists to prevent duplicates on multiple test runs
    if not db.query(StockMaster).filter(StockMaster.symbol == "005930").first():
        samsung = StockMaster(symbol="005930", name="삼성전자", market="KOSPI")
        db.add(samsung)
        db.commit()
        db.refresh(samsung)
    db.close()
    yield

async def get_auth_token():
    """Helper to register/login user and get auth token"""
    async with httpx.AsyncClient() as client:
        # 1. Register/Ensure user exists
        payload = {"telegram_id": str(TEST_USER_ID), "is_active": True}
        await client.put(f"{API_URL}/users/telegram_register", json=payload)
        
        # 2. Login
        login_payload = {"username": f"tg_{TEST_USER_ID}", "password": "telegram_user_password"}
        response = await client.post(f"{API_URL}/users/login", json=login_payload)
        if response.status_code == 200:
            return response.json()['access_token']
        raise Exception(f"Login failed: {response.text}")

@pytest.mark.asyncio
async def test_alert_scenario_e2e():
    """
    Tests the full alert scenario (set, list, remove) by directly calling handlers
    and interacting with the live API.
    """
    symbol = "005930"  # Samsung Electronics
    auth_token = await get_auth_token()

    # Create a single MagicMock for context and initialize user_data
    context_mock = MagicMock()
    context_mock.user_data = {'auth_token': auth_token}

    # --- 1. Set a price alert ---
    # Mock Update for set_price_alert
    update_set = MagicMock()
    update_set.effective_user.id = TEST_USER_ID
    update_set.message.text = "80000 이상"
    update_set.message.reply_text = AsyncMock()
    
    # set_price_alert expects symbol in user_data (from conversation state)
    context_mock.user_data['alert_symbol'] = symbol

    print(f"\n[E2E] 1. Setting price alert for {symbol}...")
    await set_price_alert(update_set, context_mock)

    # Verify the confirmation message
    update_set.message.reply_text.assert_called_once()
    call_args_set = update_set.message.reply_text.call_args[0][0]
    assert f"✅ '{symbol}'의 가격 알림을" in call_args_set
    assert "80,000원 이상으로" in call_args_set
    print("[E2E] 1. Price alert set successfully.")

    # --- 2. List alerts to verify ---
    # Mock Update for list_alerts
    update_list = MagicMock()
    update_list.effective_user.id = TEST_USER_ID
    update_list.effective_message.reply_text = AsyncMock() # list_alerts uses effective_message

    print(f"\n[E2E] 2. Listing alerts for user {TEST_USER_ID}...")
    await list_alerts(update_list, context_mock)

    # Verify the alert is listed
    update_list.effective_message.reply_text.assert_called_once()
    call_args_list = update_list.effective_message.reply_text.call_args.kwargs['text']
    assert f"삼성전자 ({symbol})" in call_args_list
    assert "80,000원 이상" in call_args_list
    print("[E2E] 2. Alert listed successfully.")

    # Extract alert ID from context.user_data['alert_map']
    alert_map = context_mock.user_data.get('alert_map')
    assert alert_map is not None
    # Assuming it's the first alert, key should be '1'
    assert '1' in alert_map
    alert_id = alert_map['1']['id']
    print(f"[E2E] Found alert ID: {alert_id}")

    # --- 3. Remove the alert ---
    # Mock Update for delete_alert
    update_remove = MagicMock()
    update_remove.effective_user.id = TEST_USER_ID
    update_remove.message.reply_text = AsyncMock()
    update_remove.effective_message.reply_text = AsyncMock() # delete_alert calls list_alerts at the end
    
    context_mock.args = ["delete", "1"] # delete_alert expects args[1] to be the number

    print(f"\n[E2E] 3. Removing alert #1 for user {TEST_USER_ID}...")
    await delete_alert(update_remove, context_mock)

    # Verify the removal confirmation
    update_remove.message.reply_text.assert_called_once()
    call_args_remove = update_remove.message.reply_text.call_args[0][0]
    assert f"가격 알림 1번이 삭제되었습니다." in call_args_remove
    print("[E2E] 3. Alert removed successfully.")

    # --- 4. List alerts again to verify removal ---
    # Mock Update for the final list_alerts
    update_final_list = MagicMock()
    update_final_list.effective_user.id = TEST_USER_ID
    update_final_list.effective_message.reply_text = AsyncMock()

    print(f"\n[E2E] 4. Listing alerts again for user {TEST_USER_ID}...")
    await list_alerts(update_final_list, context_mock)

    # Verify that no alerts are listed
    # list_alerts calls effective_message.reply_text with "등록된 알림이 없습니다." if empty
    # Note: delete_alert calls list_alerts at the end, so we might need to check that too if we reused the mock, 
    # but here we use a new mock update_final_list.
    
    # Wait, list_alerts is called with update_final_list.
    update_final_list.effective_message.reply_text.assert_called_once()
    call_args_final = update_final_list.effective_message.reply_text.call_args.kwargs['text']
    assert "등록된 알림이 없습니다." in call_args_final
    print("[E2E] 4. Verified that no alerts are listed. E2E test complete.")
