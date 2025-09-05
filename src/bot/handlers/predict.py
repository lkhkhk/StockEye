import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler
from telegram.ext import filters as Filters
from src.common.utils.http_client import get_retry_client
from src.common.database.db_connector import get_db
from src.common.services.stock_master_service import StockMasterService
import re
import logging
from datetime import datetime
import os

# Import from symbols.py for consistency
from src.bot.handlers.symbols import PAGE_SIZE, _api_search_symbols, _get_search_results_message_and_keyboard
from src.common.utils.callback_parser import parse_pagination_callback_data

logger = logging.getLogger(__name__)

async def _execute_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str, stock_name: str):
    """Helper function to execute the prediction API call and handle responses."""
    user_id = str(update.effective_user.id)
    display_name = stock_name if stock_name else symbol
    message = update.message or update.callback_query.message

    logger.debug(f"_execute_prediction called for symbol: {symbol}, stock_name: {stock_name}")

    try:
        async with get_retry_client() as client:
            api_host = os.getenv("API_HOST", "localhost")
            api_url = f"http://{api_host}:8000/api/v1"
            logger.debug(f"Calling API: {api_url}/predict with symbol={symbol}, telegram_id={user_id}")
            response = await client.post(f"{api_url}/predict", json={"symbol": symbol, "telegram_id": user_id})
            response.raise_for_status()
            data = response.json()
            logger.debug(f"API response data: {data}")
            msg = f"[예측 결과] {display_name}({symbol}): {data.get('prediction', 'N/A')}\n사유: {data.get('reason', '')}"
            await message.reply_text(msg)

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTPStatusError in _execute_prediction: {e.response.status_code} - {e.response.text}", exc_info=True)
        try:
            error_data = e.response.json()
            error_detail = error_data.get("detail", "")
        except Exception:
            error_detail = e.response.text
        
        if "분석에 필요한 데이터" in error_detail and "부족합니다" in error_detail:
            keyboard = [
                [
                    InlineKeyboardButton("예, 실행", callback_data=f"upd:{symbol}"),
                    InlineKeyboardButton("아니오", callback_data="predict_cancel"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text(
                f"'{display_name}' 종목의 예측에 필요한 데이터가 부족합니다. 과거 시세를 다운로드하고 다시 예측할까요?",
                reply_markup=reply_markup
            )
        else:
            await message.reply_text(f"주가 예측 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (오류 코드: {e.response.status_code})")
    except httpx.RequestError as e:
        logger.error(f"Network error in _execute_prediction: {e}", exc_info=True)
        await message.reply_text("주가 예측 중 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in _execute_prediction: {e}", exc_info=True)
        await message.reply_text(f"주가 예측 중 알 수 없는 오류가 발생했습니다.")

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /predict [종목명 또는 종목코드]")
        return

    input_text = context.args[0]
    symbol = None
    stock_name = None

    db_session_gen = get_db()
    db = next(db_session_gen)
    try:
        stock_master_service = StockMasterService()
        
        if re.match(r'^\d+$', input_text): # Input is likely a symbol
            symbol = input_text
            stock = stock_master_service.get_stock_by_symbol(symbol, db)
            if stock:
                stock_name = stock.name
            else:
                await update.message.reply_text(f"'{input_text}'에 해당하는 종목을 찾을 수 없습니다.")
                return
        else: # Input is likely a name, use API search for consistency and multiple results
            # Use _api_search_symbols from symbols.py
            search_data = await _api_search_symbols(input_text, PAGE_SIZE, 0)
            search_results = search_data.get("items", [])
            total_count = search_data.get("total_count", 0)

            if not search_results:
                await update.message.reply_text(f"'{input_text}'에 해당하는 종목을 찾을 수 없습니다.")
                return
            elif total_count > 1: # Multiple results, show selection buttons with pagination
                # Reuse _get_search_results_message_and_keyboard from symbols.py
                msg, reply_markup = await _get_search_results_message_and_keyboard(search_data, input_text, 0, pagination_callback_prefix="predict_search_page")
                
                # Modify callback_data for predict-specific selection
                new_keyboard = []
                for row in reply_markup.inline_keyboard:
                    new_row = []
                    for button in row:
                        if button.callback_data and button.callback_data.startswith("symbol_info_"):
                            # Change symbol_info_SYMBOL to predict_select_stock:SYMBOL
                            new_callback_data = button.callback_data.replace("symbol_info_", "sel:")
                            new_row.append(InlineKeyboardButton(button.text, callback_data=new_callback_data))
                        elif button.callback_data and button.callback_data.startswith("predict_search_page:"):
                            # These are already in the correct format, just copy
                            new_row.append(button)
                        else:
                            # This handles original symbols_search_page_ buttons from _get_search_results_message_and_keyboard
                            # if they were not correctly prefixed (should not happen with new code)
                            parts = button.callback_data.split('_')
                            if len(parts) == 3 and parts[0] == "symbols_search_page":
                                query_str_part = parts[1]
                                offset_part = parts[2]
                                new_callback_data = f"predict_search_page:{query_str_part}:{offset_part}"
                                new_row.append(InlineKeyboardButton(button.text, callback_data=new_callback_data))
                            else:
                                new_row.append(button)
                    new_keyboard.append(new_row)
                
                reply_markup = InlineKeyboardMarkup(new_keyboard)

                await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
                return
            else: # Exactly one result found by name search
                stock = search_results[0]
                symbol = stock['symbol']
                stock_name = stock['name']

    finally:
        next(db_session_gen, None)

    if not symbol:
        # This case should ideally not be reached if previous checks are thorough
        await update.message.reply_text(f"'{input_text}'에 해당하는 종목을 찾을 수 없습니다.")
        return

    await _execute_prediction(update, context, symbol, stock_name)

async def predict_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    
    callback_data = query.data
    
    if callback_data.startswith("upd:"):
        try:
            _, symbol = callback_data.split(":", 1)
        except ValueError:
            logger.error(f"Invalid callback_data format: {callback_data}")
            await query.edit_message_text(text="오류: 잘못된 콜백 데이터입니다.")
            return

        # Retrieve stock_name using the symbol
        db_session_gen = get_db()
        db = next(db_session_gen)
        stock_master_service = StockMasterService()
        stock = stock_master_service.get_stock_by_symbol(symbol, db)
        stock_name = stock.name if stock else symbol # Fallback to symbol if name not found
        next(db_session_gen, None) # Close DB session

        context.user_data['pending_prediction'] = {'symbol': symbol, 'name': stock_name}
        
        await query.edit_message_text(text=f"'{stock_name}'의 과거 시세 데이터 다운로드를 요청했습니다. 완료되면 자동으로 예측을 실행합니다.")
        
        try:
            from .admin import get_auth_token
            token = await get_auth_token(update.effective_chat.id)
            if not token:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="오류: 인증 토큰을 얻을 수 없습니다.")
                return

            headers = {"Authorization": f"Bearer {token}"}
            async with get_retry_client() as client:
                api_host = os.getenv("API_HOST", "localhost")
                api_url = f"http://{api_host}:8000/api/v1"
                response = await client.post(
                    f"{api_url}/admin/update_historical_prices",
                    headers=headers,
                    json={
                        "start_date": "1990-01-01",
                        "end_date": datetime.now().strftime('%Y-%m-%d'),
                        "stock_identifier": symbol,
                        "chat_id": update.effective_chat.id
                    },
                    timeout=30
                )
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to trigger historical data update: {e}", exc_info=True)
            await context.bot.send_message(chat_id=update.effective_chat.id, text="데이터 업데이트 시작에 실패했습니다.")

    elif callback_data == "predict_cancel":
        await query.edit_message_text(text="취소되었습니다.")

    elif callback_data.startswith("sel:"):
        try:
            _, symbol = callback_data.split(":", 1) # Only symbol is in callback_data
        except ValueError:
            logger.error(f"Invalid callback_data format: {callback_data}")
            await query.edit_message_text(text="오류: 잘못된 콜백 데이터입니다.")
            return
        
        # Retrieve stock_name using the symbol
        db_session_gen = get_db()
        db = next(db_session_gen)
        stock_master_service = StockMasterService()
        stock = stock_master_service.get_stock_by_symbol(symbol, db)
        stock_name = stock.name if stock else symbol # Fallback to symbol if name not found
        next(db_session_gen, None) # Close DB session

        await query.edit_message_text(text=f"'{stock_name}' 종목을 선택했습니다. 예측을 진행합니다.")
        await _execute_prediction(update, context, symbol, stock_name)

    elif callback_data.startswith("predict_search_page:"):
        try:
            # Use the common parser
            query_str, new_offset = parse_pagination_callback_data(callback_data, "predict_search_page")
        except ValueError as e:
            logger.error(f"Error parsing pagination callback data: {e}")
            await query.edit_message_text(text="오류: 잘못된 페이지네이션 데이터입니다.")
            return

        # Use _api_search_symbols from symbols.py
        search_data = await _api_search_symbols(query_str, PAGE_SIZE, new_offset)
        
        # Reuse _get_search_results_message_and_keyboard from symbols.py
        msg, reply_markup = await _get_search_results_message_and_keyboard(search_data, query_str, new_offset, pagination_callback_prefix="predict_search_page")

        # Modify callback_data for predict-specific selection
        new_keyboard = []
        if reply_markup:
            for row in reply_markup.inline_keyboard:
                new_row = []
                for button in row:
                    if button.callback_data and button.callback_data.startswith("symbol_info_"):
                        new_callback_data = button.callback_data.replace("symbol_info_", "sel:")
                        new_row.append(InlineKeyboardButton(button.text, callback_data=new_callback_data))
                    elif button.callback_data and button.callback_data.startswith("predict_search_page:"):
                        # These are already in the correct format, just copy
                        new_row.append(button)
                    else:
                        # This handles original symbols_search_page_ buttons from _get_search_results_message_and_keyboard
                        # if they were not correctly prefixed (should not happen with new code)
                        # This part is likely redundant now that _get_search_results_message_and_keyboard is updated
                        parts = button.callback_data.split('_')
                        if len(parts) == 3 and parts[0] == "symbols_search_page":
                            query_str_part = parts[1]
                            offset_part = parts[2]
                            new_callback_data = f"predict_search_page:{query_str_part}:{offset_part}"
                            new_row.append(InlineKeyboardButton(button.text, callback_data=new_callback_data))
                        else:
                            new_row.append(button)
                new_keyboard.append(new_row)
            reply_markup = InlineKeyboardMarkup(new_keyboard)

        await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def rerun_prediction_on_completion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("rerun_prediction_on_completion handler started.")
    if not update.message or not update.message.text:
        logger.debug("Handler exiting: No message or text.")
        return

    logger.debug(f"Received message text: {update.message.text}")

    pending_prediction = context.user_data.get('pending_prediction')
    if not pending_prediction:
        logger.debug("Handler exiting: No pending prediction found in user_data.")
        return
    
    logger.debug(f"Found pending prediction: {pending_prediction}")

    # Check if the message is a successful completion notification
    is_completion_message = "과거 일별 시세 갱신" in update.message.text and \
                            "작업 완료" in update.message.text and \
                            "성공" in update.message.text

    if not is_completion_message:
        logger.debug("Handler exiting: Message is not a completion notification.")
        return

    logger.debug("Message is a completion notification. Proceeding to parse.")
    
    # Extract the stock identifier (symbol) from the completion message
    match = re.search(r'\*\*과거 일별 시세 갱신 \((?:.*?):(.+?)\)\*\*', update.message.text)
    if not match:
        logger.debug(f"Regex did not match. Regex: r'\*\*과거 일별 시세 갱신 \((?:.*?):(.+?)\)\*\*'")
        return

    completed_stock_identifier_in_message = match.group(1)
    logger.debug(f"Regex matched. Extracted symbol: {completed_stock_identifier_in_message}")

    # Get the stock symbol from pending_prediction
    pending_stock_symbol = pending_prediction.get('symbol')

    # Only proceed if the completed stock identifier matches the pending stock symbol
    if completed_stock_identifier_in_message == pending_stock_symbol:
        logger.info(f"Symbols match! Re-running prediction for {pending_stock_symbol} for user {update.effective_chat.id}")
        symbol = pending_stock_symbol
        stock_name = pending_prediction.get('name')

        # Clear the state
        del context.user_data['pending_prediction']
        logger.debug("Cleared pending_prediction from user_data.")

        # Re-run the prediction
        await _execute_prediction(update, context, symbol, stock_name)
    else:
        logger.warning(
            f"Symbol mismatch. Pending: {pending_stock_symbol}, Completed: {completed_stock_identifier_in_message}"
        )

def get_predict_handlers():
    return [
        CommandHandler("predict", predict_command),
        CallbackQueryHandler(predict_callback_handler, pattern="^predict_"),
        CallbackQueryHandler(predict_callback_handler, pattern="^sel:"), # Handle stock selection
        CallbackQueryHandler(predict_callback_handler, pattern="^upd:"), # Handle update confirmation
        CallbackQueryHandler(predict_callback_handler, pattern="^predict_search_page:"), # Handle pagination for search results
    ]