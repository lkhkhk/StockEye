import pytest
import httpx
import asyncio
import os
import time

# Define the base URL for the bot service (assuming it's exposed on localhost for testing)
BOT_WEBHOOK_URL = os.getenv("BOT_WEBHOOK_URL", "http://stockseye-bot:8001")



async def send_telegram_message(text: str, chat_id: int = 12345):
    """Simulates sending a Telegram message to the bot's webhook."""
    payload = {
        "update_id": 123456789,
        "message": {
            "message_id": 123,
            "from": {
                "id": chat_id,
                "is_bot": False,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "language_code": "en"
            },
            "chat": {
                "id": chat_id,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "type": "private"
            },
            "date": int(time.time()),
            "text": text
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BOT_WEBHOOK_URL}/webhook", json=payload, timeout=10)
        response.raise_for_status() # Raise an exception for 4xx/5xx responses
        return response

async def get_bot_response_from_logs(chat_id: int, expected_text_substring: str, timeout: int = 10):
    """Fetches bot logs and checks for a specific response for a given chat_id."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        # This is a simplified approach. In a real scenario, you might need a more robust log parsing mechanism
        # or a dedicated endpoint on the bot for testing responses.
        log_command = f"docker compose logs bot --tail 100"
        result = os.popen(log_command).read()
        
        # Look for patterns indicating the bot sent a message to the user
        # This pattern needs to be refined based on actual bot logging for outgoing messages
        # For now, we'll just check if the expected text appears anywhere in the logs
        if expected_text_substring in result and f"chat_id={chat_id}" in result:
            return True
        await asyncio.sleep(1)
    return False

@pytest.mark.asyncio
async def test_start_command_e2e():
    """Test the /start command end-to-end with actual bot and API services."""
    chat_id = 12345
    command = "/start"
    expected_response_substring = "안녕하세요! 텔레그램 봇이 정상 동작합니다."

    print(f"\nSending command: {command} to chat_id: {chat_id}")
    await send_telegram_message(command, chat_id)

    print(f"Checking bot logs for response: '{expected_response_substring}' for chat_id: {chat_id}")
    assert await get_bot_response_from_logs(chat_id, expected_response_substring), f"Bot did not respond with expected text for {command}"

# Add more E2E tests for other commands here

@pytest.mark.asyncio
async def test_alert_scenario_e2e():
    """Test the full alert scenario: set, list, and remove."""
    chat_id = 54321 # Use a different chat_id to avoid conflicts
    symbol = "005930" # Samsung Electronics

    # 1. Set a price alert
    set_command = f"/set_price {symbol} 80000 이상"
    expected_set_response = f"'{symbol}'의 가격 알림을 '80,000원 이상'(으)로 설정했습니다."
    print(f"\nSending command: {set_command} to chat_id: {chat_id}")
    await send_telegram_message(set_command, chat_id)
    print(f"Checking bot logs for response: '{expected_set_response}' for chat_id: {chat_id}")
    assert await get_bot_response_from_logs(chat_id, expected_set_response), f"Bot did not respond correctly for {set_command}"

    # 2. List alerts to verify
    list_command = "/alert_list"
    expected_list_response = f"- 1. {symbol}"
    print(f"\nSending command: {list_command} to chat_id: {chat_id}")
    await send_telegram_message(list_command, chat_id)
    print(f"Checking bot logs for response containing: '{expected_list_response}' for chat_id: {chat_id}")
    assert await get_bot_response_from_logs(chat_id, expected_list_response), f"Bot did not list the alert correctly for {list_command}"

    # 3. Remove the alert
    remove_command = "/alert_remove 1"
    expected_remove_response = f"알림 번호 1 ({symbol}) 삭제 완료"
    print(f"\nSending command: {remove_command} to chat_id: {chat_id}")
    await send_telegram_message(remove_command, chat_id)
    print(f"Checking bot logs for response: '{expected_remove_response}' for chat_id: {chat_id}")
    assert await get_bot_response_from_logs(chat_id, expected_remove_response), f"Bot did not respond correctly for {remove_command}"

    # 4. List alerts again to verify removal
    expected_final_list_response = "등록된 알림이 없습니다."
    print(f"\nSending command: {list_command} to chat_id: {chat_id}")
    await send_telegram_message(list_command, chat_id)
    print(f"Checking bot logs for response: '{expected_final_list_response}' for chat_id: {chat_id}")
    assert await get_bot_response_from_logs(chat_id, expected_final_list_response), f"Bot did not confirm alert removal correctly for {list_command}"

