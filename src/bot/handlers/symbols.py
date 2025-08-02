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

    msg = "[종목 목록]\n" + "\n".join([
        f"{item['symbol']} {item['name']} ({item['market']})" if item.get('market') else f"{item['symbol']} {item['name']}"
        for item in items
    ])

    current_page = (offset // PAGE_SIZE) + 1
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE

    msg += f"\n\n페이지: {current_page}/{total_pages} (총 {total_count}개)"

    keyboard_buttons = []
    if offset > 0:
        keyboard_buttons.append(InlineKeyboardButton("맨앞", callback_data="symbols_page_0"))
        keyboard_buttons.append(InlineKeyboardButton("이전", callback_data=f"symbols_page_{offset - PAGE_SIZE}"))
    if offset + PAGE_SIZE < total_count:
        keyboard_buttons.append(InlineKeyboardButton("다음", callback_data=f"symbols_page_{offset + PAGE_SIZE}"))
        keyboard_buttons.append(InlineKeyboardButton("맨뒤", callback_data=f"symbols_page_{(total_pages - 1) * PAGE_SIZE}"))

    reply_markup = InlineKeyboardMarkup([keyboard_buttons]) if keyboard_buttons else None
    return msg, reply_markup

async def symbols_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            await update.message.reply_text(msg, reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"종목 목록 조회 실패: API 응답 코드 {response.status_code}")
    except Exception as e:
        logger.error(f"Unknown Error in symbols_command: {e}", exc_info=True)
        await update.message.reply_text(f"종목 목록 조회 실패: 알 수 없는 오류가 발생했습니다.")

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

async def symbols_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /symbols_search [키워드] 예: /symbols_search 삼성")
        return
    query = context.args[0]
    try:
        response = await session.get(f"{API_URL}/symbols/search", params={"query": query}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if not data:
                await update.message.reply_text("검색 결과가 없습니다.")
                return
            msg = "[종목 검색 결과]\n" + "\n".join([f"{item['symbol']} {item['name']} ({item.get('market','')})" for item in data])
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"종목 검색 실패: API 응답 코드 {response.status_code}")
    except httpx.RequestError as e:
        await update.message.reply_text(f"종목 검색 실패: API 요청 오류가 발생했습니다.")
    except Exception as e:
        await update.message.reply_text(f"종목 검색 실패: 알 수 없는 오류가 발생했습니다.")

async def symbol_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /symbol_info [종목코드] 예: /symbol_info 005930")
        return
    symbol = context.args[0]
    try:
        response = await session.get(f"{API_URL}/symbols/search", params={"query": symbol}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if not data:
                await update.message.reply_text("해당 종목을 찾을 수 없습니다.")
                return
            info = data[0]
            msg = f"[종목 상세]\n코드: {info['symbol']}\n이름: {info['name']}\n시장: {info.get('market','')}"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 응답 코드: {response.status_code})")
    except httpx.RequestError as e:
        await update.message.reply_text(f"종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (API 요청 오류)")
    except Exception as e:
        await update.message.reply_text(f"종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (알 수 없는 오류)") 