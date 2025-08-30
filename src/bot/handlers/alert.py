import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from src.common.utils.http_client import get_retry_client
from src.bot.decorators import ensure_user_registered # Add this import

API_URL = "http://stockeye-api:8000"
logger = logging.getLogger(__name__)

# =====================================================================================
# Internal API Helper Functions (for easier testing)
# =====================================================================================

async def _api_set_price_alert(payload: dict) -> httpx.Response:
    """Helper to call the create price alert API."""
    async with get_retry_client() as client:
        return await client.post(f"{API_URL}/api/v1/alerts/", json=payload)

async def _api_search_stocks(query: str) -> list:
    """Helper to call the stock search API."""
    async with get_retry_client() as client:
        response = await client.get(f"{API_URL}/api/v1/symbols/search", params={"query": query})
        response.raise_for_status()
        return response.json()

async def _api_get_alerts(telegram_id: int) -> list:
    """Helper to call the get alerts API."""
    async with get_retry_client() as client:
        response = await client.get(f"{API_URL}/api/v1/alerts/{telegram_id}")
        response.raise_for_status()
        return response.json()

async def _api_get_current_price(symbol: str) -> dict:
    """Helper to call the get current price API."""
    async with get_retry_client() as client:
        response = await client.get(f"{API_URL}/api/v1/symbols/{symbol}/price")
        response.raise_for_status()
        return response.json()

async def _api_delete_alert(alert_id: int) -> httpx.Response:
    """Helper to call the delete alert API."""
    async with get_retry_client() as client:
        return await client.delete(f"{API_URL}/api/v1/alerts/{alert_id}")

# =====================================================================================
# Command Handlers
# =====================================================================================

@ensure_user_registered
async def set_price_alert(update: Update, context: ContextTypes.DEFAULT_TYPE, repeat_interval: str = None):
    try:
        if len(context.args) < 3:
            raise ValueError("Invalid arguments")
        symbol, price_str, condition = context.args[0], context.args[1], context.args[2]
        price = float(price_str)
        condition_map = {"이상": "gte", "이하": "lte"}
        condition_en = condition_map.get(condition)
        if not condition_en:
            raise ValueError("Invalid condition")

        payload = {
            "telegram_id": update.effective_user.id,
            "symbol": symbol,
            "target_price": price,
            "condition": condition_en,
            "repeat_interval": repeat_interval,
            "is_active": True
        }
        
        response = await _api_set_price_alert(payload)
        response.raise_for_status()
        condition_text = "이상" if condition_en == "gte" else "이하"
        await update.message.reply_text(f"✅ '{symbol}'의 가격 알림을 {price}원 {condition_text}으로 설정했습니다.")

    except ValueError:
        await update.message.reply_text("❌ 사용법: /set_alert [종목코드] [가격] [이상|이하]")
    except Exception as e:
        logger.error(f"가격 알림 설정 중 오류: {e}", exc_info=True)
        await update.message.reply_text("가격 알림 설정 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

@ensure_user_registered
async def alert_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("검색할 종목명을 입력해주세요. 예: /alert_add 삼성전자")
        return

    query = " ".join(context.args)
    try:
        stocks = await _api_search_stocks(query)
        if not stocks:
            await update.message.reply_text(f"'{query}'에 대한 검색 결과가 없습니다.")
            return

        keyboard = []
        message = f"'{query}' 검색 결과입니다. 어떤 종목을 추가하시겠습니까?\n"
        for stock in stocks:
            button = InlineKeyboardButton(f"{stock['name']} ({stock['symbol']})", callback_data=f"alert_add_{stock['symbol']}")
            keyboard.append([button])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text=message, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"종목 검색 중 오류: {e}", exc_info=True)
        await update.message.reply_text("종목 검색 중 오류가 발생했습니다.")

@ensure_user_registered
async def alert_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        telegram_id = update.effective_user.id
        alerts = await _api_get_alerts(telegram_id)
        if not alerts:
            await update.message.reply_text("등록된 알림이 없습니다.")
            return

        message = "🔔 **나의 알림 목록**\n\n"
        alert_map = {}
        stock_names = {} # Cache for stock names
        for i, alert in enumerate(alerts, 1):
            alert_map[str(i)] = alert['id']
            
            # Get stock name from cache or API
            symbol = alert['symbol']
            if symbol not in stock_names:
                try:
                    stocks_data = await _api_search_stocks(symbol)
                    if stocks_data and stocks_data.get('items'):
                        stock_names[symbol] = stocks_data['items'][0]['name']
                    else:
                        stock_names[symbol] = symbol # Fallback to symbol if name not found
                except Exception as e:
                    logger.warning(f"종목명 조회 실패 ({symbol}): {e}")
                    stock_names[symbol] = symbol # Fallback to symbol on error

            stock_name = stock_names[symbol]

            # Corrected f-string syntax for dictionary lookup
            condition_text = {'gte': '이상', 'lte': '이하'}.get(alert['condition'], '')
            price_info = f"{alert['target_price']}원 {condition_text}"
            status = "(활성)" if alert['is_active'] else "(비활성)"
            stock_name = alert['stock_name'] if alert.get('stock_name') else alert['symbol'] # Use stock_name from API, fallback to symbol
            message += f"{i}. **{stock_name}** ({alert['symbol']}) - {price_info} {status}"
        
        context.user_data['alert_map'] = alert_map
        await update.message.reply_text(text=message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"알림 목록 조회 중 오류: {e}", exc_info=True)
        await update.message.reply_text("알림 목록 조회 중 오류가 발생했습니다: . 잠시 후 다시 시도해주세요.")

@ensure_user_registered
async def alert_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("삭제할 알림 번호를 입력해주세요. 예: /alert_remove 1")
        return

    try:
        alert_num = context.args[0]
        alert_map = context.user_data.get('alert_map', {})
        alert_id = alert_map.get(alert_num)

        if not alert_id:
            await update.message.reply_text("잘못된 번호입니다. /alert_list 로 목록을 먼저 조회해주세요.")
            return

        response = await _api_delete_alert(alert_id)
        response.raise_for_status()
        await update.message.reply_text(f"알림 {alert_num}번이 삭제되었습니다.")

    except Exception as e:
        logger.error(f"알림 삭제 중 오류: {e}", exc_info=True)
        await update.message.reply_text("알림 삭제 중 오류가 발생했습니다: . 잠시 후 다시 시도해주세요.")

@ensure_user_registered
async def alert_set_repeat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # ... (Implementation for setting repeat interval) ...
    await query.edit_message_text(text="알림 반복 설정은 현재 구현 중입니다.")

def get_alert_options_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """가격/공시 알림 설정 인라인 키보드를 생성합니다."""
    keyboard = [
        [InlineKeyboardButton("가격 알림 설정/수정", callback_data=f"alert_price_{symbol}")],
        [InlineKeyboardButton("공시 알림 켜기/끄기", callback_data=f"alert_disclosure_{symbol}")],
        [InlineKeyboardButton("반복 알림 설정", callback_data=f"alert_repeat_{symbol}")] # 반복 알림 버튼 추가
    ]
    return InlineKeyboardMarkup(keyboard)

def get_repeat_interval_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """반복 알림 주기 선택 인라인 키보드를 생성합니다."""
    keyboard = [
        [InlineKeyboardButton("반복 안 함", callback_data=f"alert_set_repeat_{symbol}_None")],
        [InlineKeyboardButton("매일", callback_data=f"alert_set_repeat_{symbol}_daily")],
        [InlineKeyboardButton("매주", callback_data=f"alert_set_repeat_{symbol}_weekly")],
        [InlineKeyboardButton("매월", callback_data=f"alert_set_repeat_{symbol}_monthly")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def alert_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """알림 설정 관련 인라인 버튼 콜백을 처리합니다."""
    query = update.callback_query
    await query.answer()

    try:
        data = query.data
        parts = data.split('_', 2)
        action = parts[1]
        symbol = parts[2]

        if action == "select":
            reply_markup = get_alert_options_keyboard(symbol)
            await query.edit_message_text(text=f"'{symbol}'에 대한 알림을 설정합니다. 원하는 작업을 선택하세요.", reply_markup=reply_markup)
            return
        elif action == "price":
            await query.edit_message_text(text=f"'{symbol}'의 가격 알림을 설정하려면, 채팅창에 다음과 같이 입력해주세요:\n\n`/set_price {symbol} [가격] [이상|이하]`\n\n(예: `/set_price {symbol} 75000 이상`)")
            return
        elif action == "repeat":
            reply_markup = get_repeat_interval_keyboard(symbol)
            await query.edit_message_text(text=f"'{symbol}'에 대한 반복 알림 주기를 선택하세요:", reply_markup=reply_markup)
            return
        
        # 공시 알림 토글 로직
        elif action == "disclosure":
            telegram_id = query.from_user.id
            async with get_retry_client() as client:
                # 먼저 현재 알림 설정을 가져옴
                get_resp = await client.get(f"{API_URL}/alerts/user/{telegram_id}/symbol/{symbol}", timeout=10) 
                
                notify_on_disclosure = True # 기본값은 True (켜기)
                if get_resp.status_code == 200:
                    # 기존 설정이 있으면 반대로 토글
                    existing_alert = await get_resp.json()
                    notify_on_disclosure = not existing_alert.get('notify_on_disclosure', False)
                
                payload = {"notify_on_disclosure": notify_on_disclosure}
                resp = await client.put(f"{API_URL}/alerts/{telegram_id}/{symbol}", json=payload, timeout=10)

                if resp.status_code == 200:
                    status_text = "ON" if notify_on_disclosure else "OFF"
                    await query.edit_message_text(text=f"'{symbol}'의 공시 알림을 '{status_text}' 상태로 변경했습니다.")
                else:
                    await query.edit_message_text(f"오류: 공시 알림 설정 실패 ({resp.status_code} - {resp.text})")

    except Exception as e:
        logger.error(f"알림 버튼 콜백 오류: {e}", exc_info=True)
        await query.edit_message_text(f"알림 설정 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")