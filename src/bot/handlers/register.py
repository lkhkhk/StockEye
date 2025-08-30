import httpx
from telegram import Update
from telegram.ext import ContextTypes
from src.common.utils.http_client import get_retry_client

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """텔레그램 ID를 시스템에 등록합니다."""
    telegram_id = str(update.effective_chat.id)
    print(f"Attempting to register user: {telegram_id}")
    try:
        async with get_retry_client() as client:
            print("Client obtained. Making PUT request...")
            response = await client.put(
                "/api/v1/users/telegram_register",
                json={"telegram_id": telegram_id, "is_active": True}
            )
            print(f"PUT request status: {response.status_code}")
            response.raise_for_status()
            await update.message.reply_text("알림 등록이 완료되었습니다. 이제부터 주가 알림을 받을 수 있습니다.")
    except httpx.HTTPStatusError as e:
        error_message = e.response.json().get("detail", f"HTTP 오류 {e.response.status_code}")
        await update.message.reply_text(f"등록 중 오류가 발생했습니다: {error_message}")
    except httpx.RequestError:
        await update.message.reply_text("등록 중 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
    except Exception:
        await update.message.reply_text("등록 중 알 수 없는 오류가 발생했습니다.")

async def unregister_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """시스템에서 텔레그램 ID를 비활성화합니다."""
    telegram_id = str(update.effective_chat.id)
    try:
        async with get_retry_client() as client:
            response = await client.put(
                "/api/v1/users/telegram_register",
                json={"telegram_id": telegram_id, "is_active": False}
            )
            response.raise_for_status()
            await update.message.reply_text("알림을 비활성화했습니다. 더 이상 주가 알림을 받지 않습니다.")
    except httpx.HTTPStatusError as e:
        error_message = e.response.json().get("detail", f"HTTP 오류 {e.response.status_code}")
        await update.message.reply_text(f"알림 비활성화 중 오류가 발생했습니다: {error_message}")
    except httpx.RequestError:
        await update.message.reply_text("알림 비활성화 중 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
    except Exception:
        await update.message.reply_text("알림 비활성화 중 알 수 없는 오류가 발생했습니다.")