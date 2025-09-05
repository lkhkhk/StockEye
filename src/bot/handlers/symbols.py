import os
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from src.common.utils.http_client import get_retry_client
import httpx

API_HOST = os.getenv("API_HOST", "localhost")
API_URL = f"http://{API_HOST}:8000/api/v1"
PAGE_SIZE = 10

logger = logging.getLogger(__name__)

# =====================================================================================
# Internal API Helper Functions (for easier testing)
# =====================================================================================

async def _api_get_symbols(limit: int, offset: int, auth_token: str = None) -> dict:
    """Helper to call the get all symbols API."""
    async with get_retry_client(auth_token=auth_token) as client:
        response = await client.get(f"{API_URL}/symbols/?limit={limit}&offset={offset}", timeout=10)
        response.raise_for_status()
        # httpx.Response.json() is a sync method, not awaitable.
        return response.json()

async def _api_search_symbols(query: str, limit: int, offset: int, auth_token: str = None) -> dict:
    """Helper to call the search symbols API."""
    async with get_retry_client(auth_token=auth_token) as client:
        response = await client.get(f"{API_URL}/symbols/search", params={"query": query, "limit": limit, "offset": offset}, timeout=10)
        response.raise_for_status()
        # httpx.Response.json() is a sync method, not awaitable.
        return response.json()

async def _api_get_symbol_by_code(symbol_code: str, auth_token: str = None) -> dict:
    """Helper to call the get symbol by code API."""
    async with get_retry_client(auth_token=auth_token) as client:
        response = await client.get(f"{API_URL}/symbols/{symbol_code}", timeout=10)
        response.raise_for_status()
        return response.json()

# =====================================================================================
# Helper Functions for Message and Keyboard Generation
# =====================================================================================

async def _get_symbols_message_and_keyboard(symbols_data: dict, offset: int):
    items = symbols_data.get('items', [])
    total_count = symbols_data.get('total_count', 0)

    if not items:
        return "등록된 종목이 없습니다.", None

    # 각 종목에 대한 버튼 생성
    stock_buttons = []
    stock_list_text = "" # New variable to hold the list of stocks
    for item in items:
        button_text = f"{item['symbol']} {item['name']}"
        if item.get('market'):
            button_text += f" ({item['market']})"
        stock_buttons.append([InlineKeyboardButton(button_text, callback_data=f"symbol_info_{item['symbol']}")])
        stock_list_text += f"- {item['symbol']} {item['name']}"
        if item.get('market'):
            stock_list_text += f" ({item['market']})"
        stock_list_text += "\n"

    current_page = (offset // PAGE_SIZE) + 1
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE

    # 페이지네이션 버튼 생성
    pagination_buttons = []
    if offset > 0:
        pagination_buttons.append(InlineKeyboardButton("맨앞", callback_data="symbols_page_0"))
        pagination_buttons.append(InlineKeyboardButton("이전", callback_data=f"symbols_page_{offset - PAGE_SIZE}"))
    if offset + PAGE_SIZE < total_count:
        pagination_buttons.append(InlineKeyboardButton("다음", callback_data=f"symbols_page_{offset + PAGE_SIZE}"))
        pagination_buttons.append(InlineKeyboardButton("맨뒤", callback_data=f"symbols_page_{(total_pages - 1) * PAGE_SIZE}"))

    # 메시지 텍스트
    msg = f"[종목 목록] (총 {total_count}개)\n페이지: {current_page}/{total_pages}\n\n{stock_list_text}\n원하는 종목을 선택하거나 페이지를 이동하세요."

    # 종목 버튼과 페이지네이션 버튼을 결합
    keyboard = stock_buttons
    if pagination_buttons:
        keyboard.append(pagination_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    return msg, reply_markup

async def _get_search_results_message_and_keyboard(search_data: dict, query_str: str, offset: int, pagination_callback_prefix: str = "symbols_search_page"):
    items = search_data.get('items', [])
    total_count = search_data.get('total_count', 0)

    if not items:
        return "검색 결과가 없습니다.", None

    # 검색 결과가 1개이고, 쿼리와 정확히 일치하는 경우 상세 정보 표시
    if total_count == 1 and (items[0]['symbol'] == query_str or items[0]['name'] == query_str):
        info = items[0]
        msg = f"[종목 상세]\n코드: {info['symbol']}\n이름: {info['name']}\n시장: {info.get('market','')}"
        return msg, None

    # 각 종목에 대한 버튼 생성
    stock_buttons = []
    stock_list_text = "" # New variable to hold the list of stocks
    for item in items:
        button_text = f"{item['symbol']} {item['name']}"
        if item.get('market'):
            button_text += f" ({item['market']})"
        stock_buttons.append([InlineKeyboardButton(button_text, callback_data=f"symbol_info_{item['symbol']}")])
        stock_list_text += f"- {item['symbol']} {item['name']}\n" # Add to the list text

    current_page = (offset // PAGE_SIZE) + 1
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE

    # 페이지네이션 버튼 생성
    pagination_buttons = []
    if offset > 0:
        pagination_buttons.append(InlineKeyboardButton("맨앞", callback_data=f"{pagination_callback_prefix}:{query_str}:0"))
        pagination_buttons.append(InlineKeyboardButton("이전", callback_data=f"{pagination_callback_prefix}:{query_str}:{offset - PAGE_SIZE}"))
    if offset + PAGE_SIZE < total_count:
        pagination_buttons.append(InlineKeyboardButton("다음", callback_data=f"{pagination_callback_prefix}:{query_str}:{offset + PAGE_SIZE}"))
        pagination_buttons.append(InlineKeyboardButton("맨뒤", callback_data=f"{pagination_callback_prefix}:{query_str}:{(total_pages - 1) * PAGE_SIZE}"))

    # 메시지 텍스트
    msg = f"'{query_str}' 검색 결과 (총 {total_count}개)\n페이지: {current_page}/{total_pages}\n\n{stock_list_text}\n원하는 종목을 선택하거나 페이지를 이동하세요."

    # 종목 버튼과 페이지네이션 버튼을 결합
    keyboard = stock_buttons
    if pagination_buttons:
        keyboard.append(pagination_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    return msg, reply_markup

# =====================================================================================
# Command Handlers
# =====================================================================================

async def symbols_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"symbols_command received context.args: {context.args}")
    reply_target = update.message if update.message else update.callback_query.message

    if context.args: # If arguments are provided, treat as a search
        await symbols_search_command(update, context)
        return

    # Original logic for fetching all symbols if no arguments
    user_id = update.effective_user.id # This is not used in this handler, but kept for consistency
    current_offset = context.user_data.get('symbols_offset', 0)

    try:
        symbols_data = await _api_get_symbols(PAGE_SIZE, current_offset)
        
        msg, reply_markup = await _get_symbols_message_and_keyboard(symbols_data, current_offset)
        await reply_target.reply_text(msg, reply_markup=reply_markup)
    except httpx.HTTPStatusError as e:
        logger.error(f"종목 목록 조회 실패: API 응답 코드 {e.response.status_code}, 응답 본문: {e.response.text}")
        await reply_target.reply_text(f"종목 목록 조회 실패: API 응답 코드 {e.response.status_code}")
    except Exception as e:
        logger.error(f"Unknown Error in symbols_command: {e}", exc_info=True)
        await reply_target.reply_text(f"종목 목록 조회 실패: 알 수 없는 오류가 발생했습니다.")

async def symbols_pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    new_offset = int(query.data.replace("symbols_page_", ""))
    context.user_data['symbols_offset'] = new_offset

    try:
        symbols_data = await _api_get_symbols(PAGE_SIZE, new_offset)

        msg, reply_markup = await _get_symbols_message_and_keyboard(symbols_data, new_offset)
        await query.edit_message_text(msg, reply_markup=reply_markup)
    except httpx.HTTPStatusError as e:
        await query.edit_message_text(f"페이지 이동 실패: API 응답 코드 {e.response.status_code}")
    except Exception as e:
        logger.error(f"Unknown Error in symbols_pagination_callback: {e}", exc_info=True)
        await query.edit_message_text(f"페이지 이동 실패: 알 수 없는 오류가 발생했습니다.")

async def symbol_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    symbol = query.data.replace("symbol_info_", "")
    context.args = [symbol]

    # symbols_search_command를 호출하여 로직을 재사용
    await symbols_search_command(update, context)

async def symbols_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_target = update.message if update.message else update.callback_query.message

    query_str = ""
    if context.args:
        query_str = context.args[0]

    current_offset = context.user_data.get(f'symbols_search_offset_{query_str}', 0)

    try:
        search_data = await _api_search_symbols(query_str, PAGE_SIZE, current_offset)
        # Store total_count for future pagination checks
        context.user_data[f'symbols_search_total_count_{query_str}'] = search_data.get('total_count', 0)

        msg, reply_markup = await _get_search_results_message_and_keyboard(search_data, query_str, current_offset)
        await reply_target.reply_text(msg, reply_markup=reply_markup)
    except httpx.HTTPStatusError as e:
        await reply_target.reply_text(f"종목 검색 실패: API 응답 코드 {e.response.status_code}")
    except Exception as e:
        logger.error(f"Unknown Error in symbols_search_command: {e}", exc_info=True)
        await reply_target.reply_text(f"종목 검색 실패: 알 수 없는 오류가 발생했습니다.")

async def symbols_search_pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # callback_data 형식: symbols_search_page_{query_str}_{offset}
    # Use the common parser
    try:
        query_str, new_offset = parse_pagination_callback_data(query.data, "symbols_search_page")
    except ValueError as e:
        logger.error(f"Error parsing pagination callback data: {e}")
        await query.edit_message_text(text="오류: 잘못된 페이지네이션 데이터입니다.")
        return
    
    # Retrieve total_count from user_data
    total_count = context.user_data.get(f'symbols_search_total_count_{query_str}', 0)

    # Prevent API call if new_offset is beyond total_count
    if total_count > 0 and new_offset >= total_count:
        # Calculate the offset for the last valid page
        last_page_offset = (total_count - 1) // PAGE_SIZE * PAGE_SIZE
        
        # Fetch the last page's data
        search_data = await _api_search_symbols(query_str, PAGE_SIZE, last_page_offset)
        msg, reply_markup = await _get_search_results_message_and_keyboard(search_data, query_str, last_page_offset)
        await query.edit_message_text(msg, reply_markup=reply_markup)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="더 이상 결과가 없습니다.")
        return

    context.user_data[f'symbols_search_offset_{query_str}'] = new_offset

    try:
        search_data = await _api_search_symbols(query_str, PAGE_SIZE, new_offset)

        msg, reply_markup = await _get_search_results_message_and_keyboard(search_data, query_str, new_offset)
        await query.edit_message_text(msg, reply_markup=reply_markup)
    except httpx.HTTPStatusError as e:
        await query.edit_message_text(f"검색 페이지 이동 실패: API 응답 코드 {e.response.status_code}")
    except Exception as e:
        logger.error(f"Unknown Error in symbols_search_pagination_callback: {e}", exc_info=True)
        await query.edit_message_text(f"검색 페이지 이동 실패: 알 수 없는 오류가 발생했습니다.")

async def symbol_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 메시지를 보낼 대상 (Command 또는 CallbackQuery에 따라 다름)
    reply_target = update.message if update.message else update.callback_query.message

    if not context.args:
        await reply_target.reply_text("사용법: /symbol_info [종목코드 또는 종목명] 예: /symbol_info 005930 또는 /symbol_info 삼성전자")
        return
    
    query_str = context.args[0]

    try:
        # 종목 코드로 직접 조회 시도
        info = await _api_get_symbol_by_code(query_str)
        msg = f"[종목 상세]\n코드: {info['symbol']}\n이름: {info['name']}\n시장: {info.get('market','')}"
        await reply_target.reply_text(msg)

    except httpx.HTTPStatusError as e:
        # 종목 코드로 조회 실패 시, 이름으로 검색 시도
        if e.response.status_code == 404:
            try:
                search_data = await _api_search_symbols(query_str, PAGE_SIZE, 0) # 상위 PAGE_SIZE개 검색
                items = search_data.get('items', [])
                
                if not items:
                    await reply_target.reply_text("해당 종목을 찾을 수 없습니다.")
                    return

                msg, reply_markup = await _get_search_results_message_and_keyboard(search_data, query_str, 0)
                await reply_target.reply_text(msg, reply_markup=reply_markup)

            except httpx.HTTPStatusError as search_e:
                await reply_target.reply_text(f"종목 검색 중 오류가 발생했습니다. (API 응답 코드: {search_e.response.status_code})")
            except Exception as search_e:
                logger.error(f"Unknown Error in symbol_info_command after search: {search_e}", exc_info=True)
                await reply_target.reply_text(f"종목 검색 중 알 수 없는 오류가 발생했습니다.")
        else:
            await reply_target.reply_text(f"종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: {e.response.status_code})")
    except Exception as e:
        logger.error(f"Unknown Error in symbol_info_command: {e}", exc_info=True)
        await reply_target.reply_text(f"종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (알 수 없는 오류)")

def get_symbols_handlers():
    return [
        CommandHandler("symbols", symbols_command),
        CommandHandler("symbol_info", symbol_info_command),
        CallbackQueryHandler(symbols_pagination_callback, pattern="^symbols_page_"),
        CallbackQueryHandler(symbols_search_pagination_callback, pattern="^symbols_search_page_"),
        CallbackQueryHandler(symbol_info_callback, pattern="^symbol_info_"),
    ]