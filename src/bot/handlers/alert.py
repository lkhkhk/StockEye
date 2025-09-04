import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)

from src.common.utils.http_client import get_retry_client
from src.bot.decorators import ensure_user_registered

API_URL = "http://stockeye-api:8000/api/v1"
logger = logging.getLogger(__name__)

# Conversation states
(ASK_ALERT_TYPE, ASK_PRICE_CONDITION, ASK_PRICE_TARGET) = range(3)

# =====================================================================================
# API Helper Functions
# =====================================================================================

async def _api_get_price_alerts(auth_token: str) -> list:
    async with get_retry_client(auth_token=auth_token) as client:
        response = await client.get(f"{API_URL}/price-alerts/")
        response.raise_for_status()
        return response.json()

async def _api_get_disclosure_alerts(auth_token: str) -> list:
    async with get_retry_client(auth_token=auth_token) as client:
        response = await client.get(f"{API_URL}/disclosure-alerts/")
        response.raise_for_status()
        return response.json()

async def _api_search_stocks(query: str, auth_token: str = None) -> list:
    async with get_retry_client(auth_token=auth_token) as client:
        response = await client.get(f"{API_URL}/symbols/search", params={"query": query})
        response.raise_for_status()
        return response.json()

async def _api_create_disclosure_alert(symbol: str, auth_token: str):
    payload = {"symbol": symbol, "is_active": True}
    async with get_retry_client(auth_token=auth_token) as client:
        response = await client.post(f"{API_URL}/disclosure-alerts/", json=payload)
        response.raise_for_status()
        return response.json()

async def _api_create_price_alert(payload: dict, auth_token: str):
    async with get_retry_client(auth_token=auth_token) as client:
        response = await client.post(f"{API_URL}/price-alerts/", json=payload)
        response.raise_for_status()
        return response.json()

async def _api_update_price_alert_status(alert_id: int, is_active: bool, auth_token: str):
    async with get_retry_client(auth_token=auth_token) as client:
        endpoint = "pause" if not is_active else "resume"
        response = await client.put(f"{API_URL}/price-alerts/{alert_id}/{endpoint}")
        response.raise_for_status()
        return response.json()

async def _api_delete_price_alert(alert_id: int, auth_token: str):
    async with get_retry_client(auth_token=auth_token) as client:
        response = await client.delete(f"{API_URL}/price-alerts/{alert_id}")
        response.raise_for_status()
        return None

async def _api_update_disclosure_alert_status(alert_id: int, is_active: bool, auth_token: str):
    async with get_retry_client(auth_token=auth_token) as client:
        endpoint = "pause" if not is_active else "resume"
        response = await client.put(f"{API_URL}/disclosure-alerts/{alert_id}/{endpoint}")
        response.raise_for_status()
        return response.json()

async def _api_delete_disclosure_alert(alert_id: int, auth_token: str):
    async with get_retry_client(auth_token=auth_token) as client:
        response = await client.delete(f"{API_URL}/disclosure-alerts/{alert_id}")
        response.raise_for_status()
        return None

# =====================================================================================
# /alert Command Main Handler
# =====================================================================================

@ensure_user_registered
async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "🔔 **알림 관리**\n\n" 
            "다양한 조건으로 주식 알림을 설정하고 관리합니다.\n\n" 
            "**명령어 목록:**\n" 
            "- `/alert add [종목명]`: 특정 종목에 대한 가격 또는 공시 알림을 새로 추가합니다.\n" 
            "  (예: `/alert add 삼성전자`)\n" 
            "- `/alert list`: 내가 등록한 모든 알림의 목록과 활성 상태를 확인합니다.\n" 
            "- `/alert delete [번호]`: 목록의 특정 알림을 삭제합니다.\n" 
            "- `/alert pause [번호]`: 특정 알림을 일시적으로 중지합니다.\n" 
            "- `/alert resume [번호]`: 중지된 알림을 다시 시작합니다.",
            parse_mode='Markdown'
        )
        return

    sub_command = args[0].lower()
    
    if sub_command == 'list':
        await list_alerts(update, context)
        return
    elif sub_command == 'add':
        if len(args) < 2:
            await update.message.reply_text("검색할 종목명을 입력해주세요. 예: `/alert add 삼성전자`", parse_mode='Markdown')
            return
        context.args = args[1:]
        return await add_alert_search(update, context)
    elif sub_command == 'pause':
        await pause_alert(update, context)
        return
    elif sub_command == 'resume':
        await resume_alert(update, context)
        return
    elif sub_command == 'delete':
        await delete_alert(update, context)
        return
    else:
        await update.message.reply_text(f"알 수 없는 명령입니다: {sub_command}")
        return

# =====================================================================================
# /alert list
# =====================================================================================

async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int = None):
    auth_token = context.user_data.get('auth_token')
    try:
        price_alerts = await _api_get_price_alerts(auth_token)
        disclosure_alerts = await _api_get_disclosure_alerts(auth_token)

        if not price_alerts and not disclosure_alerts:
            text = "등록된 알림이 없습니다."
        else:
            message = "🔔 **나의 알림 목록**\n\n"
            alert_map = {}
            count = 1

            stock_names_map = {}
            symbols_to_fetch = set()

            if price_alerts:
                for alert in price_alerts:
                    stock_name = alert.get('stock_name')
                    if stock_name:
                        stock_names_map[alert['symbol']] = stock_name
                    else:
                        symbols_to_fetch.add(alert['symbol'])
            
            if disclosure_alerts:
                for alert in disclosure_alerts:
                    symbols_to_fetch.add(alert['symbol'])

            for symbol in symbols_to_fetch:
                stock_data = await _api_search_stocks(symbol, auth_token)
                if stock_data and stock_data.get('items'):
                    stock_names_map[symbol] = stock_data['items'][0]['name']
                else:
                    stock_names_map[symbol] = symbol

            if price_alerts:
                message += "**[가격 알림]**\n"
                for alert in price_alerts:
                    alert_map[str(count)] = {"id": alert['id'], "type": "price", "is_active": alert['is_active']}
                    status = "(활성)" if alert['is_active'] else "(비활성)"
                    stock_name = stock_names_map.get(alert['symbol'], alert['symbol'])
                    
                    if alert.get('target_price') is not None:
                        condition = {'gte': '이상', 'lte': '이하'}.get(alert['condition'], alert['condition'])
                        message += f"{count}. {stock_name} ({alert['symbol']}) - {alert['target_price']:,.0f}원 {condition} {status}\n"
                    elif alert.get('change_percent') is not None:
                        change_type = {'up': '상승', 'down': '하락'}.get(alert.get('change_type'), '')
                        message += f"{count}. {stock_name} ({alert['symbol']}) - {alert['change_percent']}% {change_type} 시 {status}\n"
                    else:
                        message += f"{count}. {stock_name} ({alert['symbol']}) - 알 수 없는 가격 조건 {status}\n"
                    count += 1

            if disclosure_alerts:
                message += "\n**[공시 알림]**\n"
                for alert in disclosure_alerts:
                    alert_map[str(count)] = {"id": alert['id'], "type": 'disclosure', "is_active": alert['is_active']}
                    status = "(활성)" if alert['is_active'] else "(비활성)"
                    stock_name = stock_names_map.get(alert['symbol'], alert['symbol'])
                    message += f"{count}. {stock_name} ({alert['symbol']}) {status}\n"
                    count += 1
            
            text = message
            context.user_data['alert_map'] = alert_map

        if message_id:
            await update.effective_chat.edit_message_text(message_id=message_id, text=text, parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(text=text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"알림 목록 조회 중 오류: {e}", exc_info=True)
        if message_id:
            await update.effective_chat.edit_message_text(message_id=message_id, text="알림 목록 조회 중 오류가 발생했습니다.")
        else:
            await update.effective_message.reply_text("알림 목록 조회 중 오류가 발생했습니다.")

# =====================================================================================
# /alert add - Conversation Flow
# =====================================================================================

async def add_alert_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    try:
        stock_data = await _api_search_stocks(query)
        stocks = stock_data.get("items", [])
        if not stocks:
            await update.message.reply_text(f"'{query}'에 대한 검색 결과가 없습니다.")
            return ConversationHandler.END

        keyboard = []
        message = f"'{query}' 검색 결과입니다. 어떤 종목의 알림을 추가하시겠습니까?"
        for stock in stocks:
            button = InlineKeyboardButton(
                f"{stock['name']} ({stock['symbol']})", 
                callback_data=f"alert_add_select_{stock['symbol']}"
            )
            keyboard.append([button])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text=message, reply_markup=reply_markup)
        return ASK_ALERT_TYPE

    except Exception as e:
        logger.error(f"종목 검색 중 오류: {e}", exc_info=True)
        await update.message.reply_text("종목 검색 중 오류가 발생했습니다.")
        return ConversationHandler.END

async def ask_alert_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data.split('_')[-1]
    context.user_data['alert_symbol'] = symbol

    keyboard = [
        [InlineKeyboardButton("가격 알림", callback_data=f"alert_add_type_price")],
        [InlineKeyboardButton("공시 알림", callback_data=f"alert_add_type_disclosure")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"'{symbol}'에 대한 어떤 알림을 추가하시겠습니까?", reply_markup=reply_markup)
    return ASK_PRICE_CONDITION

async def add_disclosure_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = context.user_data.get('alert_symbol')
    auth_token = context.user_data.get('auth_token')

    try:
        api_response = await _api_create_disclosure_alert(symbol, auth_token)
        status_message = api_response.get("status_message", "추가했습니다.")
        await query.edit_message_text(text=f"✅ '{symbol}'에 대한 공시 알림을 {status_message}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            error_detail = e.response.json().get("detail", "이미 등록된 공시 알림입니다.")
            await query.edit_message_text(text=f"⚠️ {error_detail}")
        else:
            logger.error(f"공시 알림 추가 중 HTTP 오류: {e}", exc_info=True)
            await query.edit_message_text(text="공시 알림 추가 중 오류가 발생했습니다.")
    except Exception as e:
        logger.error(f"공시 알림 추가 중 오류: {e}", exc_info=True)
        await query.edit_message_text(text="공시 알림 추가 중 오류가 발생했습니다.")
    
    context.user_data.pop('alert_symbol', None)
    return ConversationHandler.END

async def ask_price_condition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="알림 조건을 입력해주세요 (예: 80000원 이상, 75000원 이하).")
    return ASK_PRICE_TARGET

async def set_price_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        parts = text.split()
        if len(parts) != 2 or parts[1] not in ['이상', '이하']:
            raise ValueError()
        
        target_price = float(parts[0].replace('원', ''))
        condition_kr = parts[1]
        condition_en = 'gte' if condition_kr == '이상' else 'lte'
        symbol = context.user_data.get('alert_symbol')
        auth_token = context.user_data.get('auth_token')

        payload = {
            "symbol": symbol,
            "target_price": target_price,
            "condition": condition_en,
            "is_active": True
        }

        api_response = await _api_create_price_alert(payload, auth_token)
        status_message = api_response.get("status_message", "설정되었습니다.")
        
        display_condition_kr = "이하로" if condition_kr == "이하" else f"{condition_kr}으로"
        await update.message.reply_text(f"✅ '{symbol}'의 가격 알림을 {target_price:,.0f}원 {display_condition_k} {status_message}")

    except (ValueError, IndexError):
        await update.message.reply_text("잘못된 형식입니다. 다시 입력해주세요 (예: 80000원 이상).")
        return ASK_PRICE_TARGET
    except Exception as e:
        logger.error(f"가격 알림 설정 중 오류: {e}", exc_info=True)
        await update.message.reply_text("가격 알림 설정 중 오류가 발생했습니다.")
    
    context.user_data.pop('alert_symbol', None)
    return ConversationHandler.END

async def cancel_alert_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('alert_symbol', None)
    await update.message.reply_text("알림 추가를 취소했습니다.")
    return ConversationHandler.END

async def pause_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth_token = context.user_data.get('auth_token')
    try:
        if len(context.args) < 2:
            await update.message.reply_text("일시정지할 알림 번호를 입력해주세요. 예: `/alert pause 1`", parse_mode='Markdown')
            return
        
        alert_number = context.args[1]
        alert_map = context.user_data.get('alert_map')
        
        if not alert_map or alert_number not in alert_map:
            await update.message.reply_text("유효하지 않은 알림 번호입니다.")
            return
            
        alert_info = alert_map[alert_number]
        alert_id = alert_info['id']
        alert_type = alert_info['type']

        if alert_info['is_active']:
            if alert_type == 'price':
                await _api_update_price_alert_status(alert_id, False, auth_token)
                await update.message.reply_text(f"✅ 가격 알림 {alert_number}번이 일시정지되었습니다.")
            elif alert_type == 'disclosure':
                await _api_update_disclosure_alert_status(alert_id, False, auth_token)
                await update.message.reply_text(f"✅ 공시 알림 {alert_number}번이 일시정지되었습니다.")
            else:
                await update.message.reply_text("지원하지 않는 알림 유형입니다.")
        else:
            if alert_type == 'price':
                await update.message.reply_text(f"ℹ️ 가격 알림 {alert_number}번은 이미 일시정지 상태입니다.")
            elif alert_type == 'disclosure':
                await update.message.reply_text(f"ℹ️ 공시 알림 {alert_number}번은 이미 일시정지 상태입니다.")
        
        await list_alerts(update, context)

    except Exception as e:
        logger.error(f"알림 일시정지 중 오류: {e}", exc_info=True)
        await update.message.reply_text("알림 일시정지 중 오류가 발생했습니다.")

async def resume_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth_token = context.user_data.get('auth_token')
    try:
        if len(context.args) < 2:
            await update.message.reply_text("재개할 알림 번호를 입력해주세요. 예: `/alert resume 1`", parse_mode='Markdown')
            return
        
        alert_number = context.args[1]
        alert_map = context.user_data.get('alert_map')
        
        if not alert_map or alert_number not in alert_map:
            await update.message.reply_text("유효하지 않은 알림 번호입니다.")
            return
            
        alert_info = alert_map[alert_number]
        alert_id = alert_info['id']
        alert_type = alert_info['type']

        if not alert_info['is_active']:
            if alert_type == 'price':
                await _api_update_price_alert_status(alert_id, True, auth_token)
                await update.message.reply_text(f"✅ 가격 알림 {alert_number}번이 재개되었습니다.")
            elif alert_type == 'disclosure':
                await _api_update_disclosure_alert_status(alert_id, True, auth_token)
                await update.message.reply_text(f"✅ 공시 알림 {alert_number}번이 재개되었습니다.")
            else:
                await update.message.reply_text("지원하지 않는 알림 유형입니다.")
        else:
            if alert_type == 'price':
                await update.message.reply_text(f"ℹ️ 가격 알림 {alert_number}번은 이미 활성 상태입니다.")
            elif alert_type == 'disclosure':
                await update.message.reply_text(f"ℹ️ 공시 알림 {alert_number}번은 이미 활성 상태입니다.")

        await list_alerts(update, context)

    except Exception as e:
        logger.error(f"알림 재개 중 오류: {e}", exc_info=True)
        await update.message.reply_text("알림 재개 중 오류가 발생했습니다.")

async def delete_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth_token = context.user_data.get('auth_token')
    try:
        if len(context.args) < 2:
            await update.message.reply_text("삭제할 알림 번호를 입력해주세요. 예: `/alert delete 1`", parse_mode='Markdown')
            return
        
        alert_number = context.args[1]
        alert_map = context.user_data.get('alert_map')
        
        if not alert_map or alert_number not in alert_map:
            await update.message.reply_text("유효하지 않은 알림 번호입니다.")
            await list_alerts(update, context)
            return
            
        alert_info = alert_map[alert_number]
        alert_id = alert_info['id']
        alert_type = alert_info['type']

        if alert_type == 'price':
            await _api_delete_price_alert(alert_id, auth_token)
            await update.message.reply_text(f"✅ 가격 알림 {alert_number}번이 삭제되었습니다.")
        elif alert_type == 'disclosure':
            await _api_delete_disclosure_alert(alert_id, auth_token)
            await update.message.reply_text(f"✅ 공시 알림 {alert_number}번이 삭제되었습니다.")
        else:
            await update.message.reply_text("지원하지 않는 알림 유형입니다.")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await update.message.reply_text("해당 알림 번호가 존재하지 않습니다.")
        else:
            logger.error(f"알림 삭제 중 HTTP 오류: {e}", exc_info=True)
            await update.message.reply_text("알림 삭제 중 오류가 발생했습니다.")
    except Exception as e:
        logger.error(f"알림 삭제 중 오류: {e}", exc_info=True)
        await update.message.reply_text("알림 삭제 중 오류가 발생했습니다.")
    
    await list_alerts(update, context)