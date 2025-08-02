import os
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from src.common.http_client import session
import httpx

API_URL = os.getenv("API_URL", "http://api_service:8000")
PAGE_SIZE = 10

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def _get_symbols_message_and_keyboard(symbols_data: dict, offset: int):
    items = symbols_data.get('items', [])
    total_count = symbols_data.get('total_count', 0)

    if not items:
        return "등록된 종목이 없습니다.", None

    # 각 종목에 대한 버튼 생성
    stock_buttons = []
    for item in items:
        button_text = f"{item['symbol']} {item['name']}"
        if item.get('market'):
            button_text += f" ({item['market']})"
        stock_buttons.append([InlineKeyboardButton(button_text, callback_data=f"symbol_info_{item['symbol']}")])

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
    msg = f"[종목 목록] (총 {total_count}개)\n페이지: {current_page}/{total_pages}\n\n원하는 종목을 선택하거나 페이지를 이동하세요."

    # 종목 버튼과 페이지네이션 버튼을 결합
    keyboard = stock_buttons
    if pagination_buttons:
        keyboard.append(pagination_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    return msg, reply_markup

async def _get_search_results_message_and_keyboard(search_data: dict, query_str: str, offset: int):
    items = search_data.get('items', [])
    total_count = search_data.get('total_count', 0)

    if not items:
        return "검색 결과가 없습니다.", None

    # 각 종목에 대한 버튼 생성
    stock_buttons = []
    for item in items:
        button_text = f"{item['symbol']} {item['name']}"
        if item.get('market'):
            button_text += f" ({item['market']})"
        stock_buttons.append([InlineKeyboardButton(button_text, callback_data=f"symbol_info_{item['symbol']}")])

    current_page = (offset // PAGE_SIZE) + 1
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE

    # 페이지네이션 버튼 생성
    pagination_buttons = []
    if offset > 0:
        pagination_buttons.append(InlineKeyboardButton("맨앞", callback_data=f"symbols_search_page_{query_str}_0"))
        pagination_buttons.append(InlineKeyboardButton("이전", callback_data=f"symbols_search_page_{query_str}_{offset - PAGE_SIZE}"))
    if offset + PAGE_SIZE < total_count:
        pagination_buttons.append(InlineKeyboardButton("다음", callback_data=f"symbols_search_page_{query_str}_{offset + PAGE_SIZE}"))
        pagination_buttons.append(InlineKeyboardButton("맨뒤", callback_data=f"symbols_search_page_{query_str}_{(total_pages - 1) * PAGE_SIZE}"))

    # 메시지 텍스트
    msg = f"'{query_str}' 검색 결과 (총 {total_count}개)\n페이지: {current_page}/{total_pages}\n\n원하는 종목을 선택하거나 페이지를 이동하세요."

    # 종목 버튼과 페이지네이션 버튼을 결합
    keyboard = stock_buttons
    if pagination_buttons:
        keyboard.append(pagination_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    return msg, reply_markup

async def symbols_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"symbols_command received context.args: {context.args}")
    reply_target = update.message if update.message else update.callback_query.message

    if context.args: # If arguments are provided, treat as a search
        await symbols_search_command(update, context)
        return

    # Original logic for fetching all symbols if no arguments
    user_id = update.effective_user.id
    current_offset = context.user_data.get('symbols_offset', 0)

    try:
        response = await session.get(f"{API_URL}/symbols/?limit={PAGE_SIZE}&offset={current_offset}", timeout=10)
        logger.info(f"API Response Status: {response.status_code}")
        logger.info(f"API Response Text: {response.text}")
        
        if response.status_code == 200:
            symbols_data = response.json()
            logger.info(f"API Response JSON: {symbols_data}")
            
            msg, reply_markup = await _get_symbols_message_and_keyboard(symbols_data, current_offset)
            await reply_target.reply_text(msg, reply_markup=reply_markup)
        else:
            logger.error(f"종목 목록 조회 실패: API 응답 코드 {response.status_code}, 응답 본문: {response.text}")
            await reply_target.reply_text(f"종목 목록 조회 실패: API 응답 코드 {response.status_code}")
    except Exception as e:
        logger.error(f"Unknown Error in symbols_command: {e}", exc_info=True)
        await reply_target.reply_text(f"종목 목록 조회 실패: 알 수 없는 오류가 발생했습니다.")

async def symbols_pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    new_offset = int(query.data.replace("symbols_page_", ""))
    context.user_data['symbols_offset'] = new_offset

    try:
        response = await session.get(f"{API_URL}/symbols/?limit={PAGE_SIZE}&offset={new_offset}", timeout=10)
        logger.info(f"API Response Status (pagination): {response.status_code}")
        logger.info(f"API Response Text (pagination): {response.text}")

        if response.status_code == 200:
            symbols_data = response.json()
            logger.info(f"API Response JSON (pagination): {symbols_data}")

            msg, reply_markup = await _get_symbols_message_and_keyboard(symbols_data, new_offset)
            await query.edit_message_text(msg, reply_markup=reply_markup)
        else:
            await query.edit_message_text(f"페이지 이동 실패: API 응답 코드 {response.status_code}")
    except Exception as e:
        logger.error(f"Unknown Error in symbols_pagination_callback: {e}", exc_info=True)
        await query.edit_message_text(f"페이지 이동 실패: 알 수 없는 오류가 발생했습니다.")

async def symbol_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    symbol = query.data.replace("symbol_info_", "")
    context.args = [symbol]

    # symbol_info_command를 호출하여 로직을 재사용
    await symbol_info_command(update, context)

async def symbols_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_target = update.message if update.message else update.callback_query.message

    query_str = ""
    if context.args:
        query_str = context.args[0]

    current_offset = context.user_data.get(f'symbols_search_offset_{query_str}', 0)

    try:
        response = await session.get(f"{API_URL}/symbols/search", params={"query": query_str, "limit": PAGE_SIZE, "offset": current_offset}, timeout=10)
        logger.info(f"API Response Status (search): {response.status_code}")
        logger.info(f"API Response Text (search): {response.text}")

        if response.status_code == 200:
            search_data = response.json()
            logger.info(f"API Response JSON (search): {search_data}")

            msg, reply_markup = await _get_search_results_message_and_keyboard(search_data, query_str, current_offset)
            await reply_target.reply_text(msg, reply_markup=reply_markup)
        else:
            logger.error(f"종목 검색 실패: API 응답 코드 {response.status_code}, 응답 본문: {response.text}")
            await reply_target.reply_text(f"종목 검색 실패: API 응답 코드 {response.status_code}")
    except httpx.RequestError as e:
        await reply_target.reply_text(f"종목 검색 실패: API 요청 오류가 발생했습니다.")
    except Exception as e:
        logger.error(f"Unknown Error in symbols_search_command: {e}", exc_info=True)
        await reply_target.reply_text(f"종목 검색 실패: 알 수 없는 오류가 발생했습니다.")

async def symbols_search_pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # callback_data 형식: symbols_search_page_{query_str}_{offset}
    parts = query.data.split('_')
    query_str = parts[3]
    new_offset = int(parts[4])
    
    context.user_data[f'symbols_search_offset_{query_str}'] = new_offset

    try:
        response = await session.get(f"{API_URL}/symbols/search", params={"query": query_str, "limit": PAGE_SIZE, "offset": new_offset}, timeout=10)
        logger.info(f"API Response Status (search pagination): {response.status_code}")
        logger.info(f"API Response Text (search pagination): {response.text}")

        if response.status_code == 200:
            search_data = response.json()
            logger.info(f"API Response JSON (search pagination): {search_data}")

            msg, reply_markup = await _get_search_results_message_and_keyboard(search_data, query_str, new_offset)
            await query.edit_message_text(msg, reply_markup=reply_markup)
        else:
            await query.edit_message_text(f"검색 페이지 이동 실패: API 응답 코드 {response.status_code}")
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
        response = await session.get(f"{API_URL}/symbols/search", params={"query": query_str, "limit": 5000, "offset": 0}, timeout=10) # 첫 페이지 검색
        if response.status_code == 200:
            search_data = response.json()
            items = search_data.get('items', [])
            total_count = search_data.get('total_count', 0)
            
            if not items:
                await reply_target.reply_text("해당 종목을 찾을 수 없습니다.")
                return

            # 정확히 일치하는 종목을 찾기 위한 필터링
            exact_match = [item for item in items if item['symbol'].lower() == query_str.lower() or item['name'].lower() == query_str.lower()]

            if exact_match and len(exact_match) == 1:
                # 정확히 일치하는 단일 종목 정보 표시
                info = exact_match[0]
                msg = f"[종목 상세]\n코드: {info['symbol']}\n이름: {info['name']}\n시장: {info.get('market','')}"
                await reply_target.reply_text(msg)
            else:
                # 부분 일치 또는 여러 결과가 나온 경우 리스트 표시
                msg, reply_markup = await _get_search_results_message_and_keyboard(search_data, query_str, 0)
                await reply_target.reply_text(msg, reply_markup=reply_markup)
        else:
            logger.error(f"종목 상세 조회 중 오류: API 응답 코드 {response.status_code}, 응답 본문: {response.text}")
            await reply_target.reply_text(f"종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: {response.status_code})")
    except httpx.RequestError as e:
        await reply_target.reply_text(f"종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 요청 오류)")
    except Exception as e:
        logger.error(f"Unknown Error in symbol_info_command: {e}", exc_info=True)
        await reply_target.reply_text(f"종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (알 수 없는 오류)")