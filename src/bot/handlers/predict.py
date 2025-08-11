import httpx
from telegram import Update
from telegram.ext import ContextTypes
from src.common.http_client import get_retry_client

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /predict [종목코드] 예: /predict 005930")
        return
        
    symbol = context.args[0]
    user_id = str(update.effective_user.id)
    
    try:
        async with get_retry_client() as client:
            # get_retry_client가 base_url을 포함하므로, 여기서는 경로만 지정합니다.
            response = await client.post("/api/v1/predict", json={"symbol": symbol, "telegram_id": user_id})
            response.raise_for_status()  # 4xx 또는 5xx 응답 코드에 대해 예외를 발생시킵니다.
            
            data = response.json()
            msg = f"[예측 결과] {symbol}: {data.get('prediction', 'N/A')}\n사유: {data.get('reason', '')}"
            await update.message.reply_text(msg)
            
    except httpx.HTTPStatusError as e:
        # API가 오류 응답을 반환한 경우
        await update.message.reply_text(f"주가 예측 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (오류 코드: {e.response.status_code})")
    except httpx.RequestError:
        # 네트워크 연결 오류 등
        await update.message.reply_text("주가 예측 중 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
    except Exception:
        # 기타 예상치 못한 오류
        await update.message.reply_text("주가 예측 중 알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")