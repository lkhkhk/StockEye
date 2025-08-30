import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
from sqlalchemy.orm import Session

# Import handler functions from your bot
from src.bot.handlers.alert import set_price_alert, alert_list, alert_remove
from src.common.models.stock_master import StockMaster
from src.common.database.db_connector import get_db

# Mock user and chat IDs for testing
TEST_USER_ID = 12345
TEST_CHAT_ID = 12345

@pytest.fixture(autouse=True)
def setup_environment():
    """Sets up environment variables for tests."""
    os.environ["API_HOST"] = "stockeye-api"
    yield
    # Clean up environment variables if necessary
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

@pytest.mark.asyncio
async def test_alert_scenario_e2e():
    """
    Tests the full alert scenario (set, list, remove) by directly calling handlers
    and interacting with the live API, DB, and Redis services.
    """
    symbol = "005930"  # Samsung Electronics

    # --- 1. Set a price alert ---
    # Mock Update and Context for set_price_alert
    update_set = MagicMock()
    context_set = MagicMock()
    update_set.effective_user.id = TEST_USER_ID
    update_set.message.reply_text = AsyncMock()
    context_set.args = [symbol, "80000", "이상"]

    print(f"\n[E2E] 1. Setting price alert for {symbol}...")
    await set_price_alert(update_set, context_set)

    # Verify the confirmation message
    update_set.message.reply_text.assert_called_once()
    call_args_set = update_set.message.reply_text.call_args[0][0]
    assert f"✅ '{symbol}'의 가격 알림을" in call_args_set
    assert "80000.0원 이상" in call_args_set
    print("[E2E] 1. Price alert set successfully.")

    # --- 2. List alerts to verify ---
    # Mock Update and Context for alert_list
    update_list = MagicMock()
    context_list = MagicMock()
    update_list.effective_user.id = TEST_USER_ID
    update_list.message.reply_text = AsyncMock()
    context_list.user_data = {} # Simulate user_data

    print(f"\n[E2E] 2. Listing alerts for user {TEST_USER_ID}...")
    await alert_list(update_list, context_list)

    # Verify the alert is listed
    update_list.message.reply_text.assert_called_once()
    call_args_list = update_list.message.reply_text.call_args[0][0]
    assert f"1. **삼성전자** ({symbol})" in call_args_list
    assert "80000.0원 이상" in call_args_list
    print("[E2E] 2. Alert listed successfully.")


    # --- 3. Remove the alert ---
    # Mock Update and Context for alert_remove
    update_remove = MagicMock()
    context_remove = MagicMock()
    update_remove.effective_user.id = TEST_USER_ID
    update_remove.message.reply_text = AsyncMock()
    # The user_data now contains the mapping from the alert_list call
    context_remove.user_data = context_list.user_data
    context_remove.args = ["1"] # The number of the alert to remove

    print(f"\n[E2E] 3. Removing alert #1 for user {TEST_USER_ID}...")
    await alert_remove(update_remove, context_remove)

    # Verify the removal confirmation
    update_remove.message.reply_text.assert_called_once()
    call_args_remove = update_remove.message.reply_text.call_args[0][0]
    assert f"알림 {alert_num}번이 삭제되었습니다." in call_args_remove
    print("[E2E] 3. Alert removed successfully.")


    # --- 4. List alerts again to verify removal ---
    # Mock Update and Context for the final alert_list
    update_final_list = MagicMock()
    context_final_list = MagicMock()
    update_final_list.effective_user.id = TEST_USER_ID
    update_final_list.message.reply_text = AsyncMock()
    # user_data would be updated after removal, so we use a fresh one
    context_final_list.user_data = {} 


    print(f"\n[E2E] 4. Listing alerts again for user {TEST_USER_ID}...")
    await alert_list(update_final_list, context_final_list)

    # Verify that no alerts are listed
    update_final_list.message.reply_text.assert_called_once_with("등록된 알림이 없습니다.")
    print("[E2E] 4. Verified that no alerts are listed. E2E test complete.")
