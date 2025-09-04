import httpx
from telegram import Update
from telegram.ext import ContextTypes
from src.common.utils.http_client import get_retry_client
from src.common.database.db_connector import get_db
from src.common.services.stock_master_service import StockMasterService
import re

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /predict [종목명 또는 종목코드]")
        return

    input_text = context.args[0]
    user_id = str(update.effective_user.id)
    symbol = None
    stock_name = None

    # 입력이 숫자로만 이루어져 있는지 확인하여 종목코드인지 종목명인지 추측
    if re.match(r'^\d+$', input_text):
        symbol = input_text
    else:
        stock_name = input_text

    db_session_gen = get_db()
    db = next(db_session_gen)
    try:
        stock_master_service = StockMasterService()
        
        if stock_name:
            stock = stock_master_service.get_stock_by_name(stock_name, db)
            if not stock:
                await update.message.reply_text(f"'{stock_name}'에 해당하는 종목을 찾을 수 없습니다.")
                return
            symbol = stock.symbol
            stock_name = stock.name # 정확한 종목명으로 업데이트
        else: # symbol로 종목명을 조회
            stock = stock_master_service.get_stock_by_symbol(symbol, db)
            if stock:
                stock_name = stock.name

    finally:
        next(db_session_gen, None)

    if not symbol:
        await update.message.reply_text(f"'{input_text}'에 해당하는 종목을 찾을 수 없습니다.")
        return

    try:
        async with get_retry_client() as client:
            response = await client.post("/api/v1/predict", json={"symbol": symbol, "telegram_id": user_id})
            response.raise_for_status()

            data = response.json()
            display_name = stock_name if stock_name else symbol
            msg = f"[예측 결과] {display_name}({symbol}): {data.get('prediction', 'N/A')}\n사유: {data.get('reason', '')}"
            await update.message.reply_text(msg)

    except httpx.HTTPStatusError as e:
        await update.message.reply_text(f"주가 예측 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (오류 코드: {e.response.status_code})")
    except httpx.RequestError:
        await update.message.reply_text("주가 예측 중 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
    except Exception as e:
        await update.message.reply_text(f"주가 예측 중 알 수 없는 오류가 발생했습니다: {e}")
