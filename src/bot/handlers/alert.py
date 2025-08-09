from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from src.common.http_client import session
import os
import requests
import logging

API_HOST = os.getenv("API_HOST", "localhost")
API_URL = f"http://{API_HOST}:8000/api/v1"

logger = logging.getLogger(__name__)

# --- Helper Functions ---
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

# --- Command Handlers ---
async def alert_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    종목에 대한 알림 설정을 시작합니다.
    종목명/코드로 검색하고, 결과에 따라 선택지를 제공합니다.
    """
    if not context.args:
        await update.message.reply_text("사용법: /alert_add [종목코드 또는 종목명] (예: /alert_add 삼성전자)")
        return
    
    query_str = " ".join(context.args)

    try:
        search_resp = await session.get(f"{API_URL}/symbols/search", params={"query": query_str}, timeout=10)
        if search_resp.status_code != 200:
            await update.message.reply_text(f"종목 검색 실패: {search_resp.text}")
            return
        
        stocks = search_resp.json()

        if not stocks:
            await update.message.reply_text(f"'{query_str}'에 해당하는 종목을 찾을 수 없습니다.")
            return

        if len(stocks) > 1:
            # 여러 종목이 검색되면 선택지를 제공
            keyboard = [
                [InlineKeyboardButton(f"{s['name']} ({s['symbol']})", callback_data=f"alert_select_{s['symbol']}")]
                for s in stocks[:10]  # 최대 10개까지 표시
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("여러 종목이 검색되었습니다. 알림을 설정할 종목을 선택하세요:", reply_markup=reply_markup)
        else:
            # 한 종목만 검색되면 바로 알림 설정 옵션 제공
            stock = stocks[0]
            symbol = stock['symbol']
            stock_name = stock['name']
            reply_markup = get_alert_options_keyboard(symbol)
            await update.message.reply_text(f"'{stock_name}({symbol})'에 대한 알림을 설정합니다. 원하는 작업을 선택하세요.", reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"알림 설정 중 오류가 발생했습니다: {e}. 잠시 후 다시 시도해주세요.")

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
            # 먼저 현재 알림 설정을 가져옴
            get_resp = await session.get(f"{API_URL}/alerts/user/{telegram_id}/symbol/{symbol}", timeout=10) 
            
            notify_on_disclosure = True # 기본값은 True (켜기)
            if get_resp.status_code == 200:
                # 기존 설정이 있으면 반대로 토글
                existing_alert = get_resp.json()
                notify_on_disclosure = not existing_alert.get('notify_on_disclosure', False)
            
            payload = {"notify_on_disclosure": notify_on_disclosure}
            resp = await session.put(f"{API_URL}/alerts/{telegram_id}/{symbol}", json=payload, timeout=10)

            if resp.status_code == 200:
                status_text = "ON" if notify_on_disclosure else "OFF"
                await query.edit_message_text(text=f"'{symbol}'의 공시 알림을 '{status_text}' 상태로 변경했습니다.")
            else:
                await query.edit_message_text(f"오류: 공시 알림 설정 실패 ({resp.status_code} - {resp.text})")

    except Exception as e:
        logger.error(f"알림 버튼 콜백 오류: {e}", exc_info=True)
        await query.edit_message_text(f"알림 설정 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

async def alert_set_repeat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """반복 알림 주기 선택 콜백을 처리합니다."""
    query = update.callback_query
    await query.answer()

    try:
        data = query.data
        parts = data.split('_')
        symbol = parts[3]
        repeat_interval = parts[4] if parts[4] != "None" else None

        telegram_id = query.from_user.id
        payload = {"repeat_interval": repeat_interval}
        
        resp = await session.put(f"{API_URL}/alerts/{telegram_id}/{symbol}", json=payload, timeout=10)

        if resp.status_code == 200:
            status_text = repeat_interval if repeat_interval else "안 함"
            await query.edit_message_text(text=f"'{symbol}'의 반복 알림 주기를 '{status_text}'으로 설정했습니다.")
        else:
            # 알림이 없는 경우 새로 생성
            if resp.status_code == 404:
                create_payload = {
                    "telegram_id": telegram_id,
                    "symbol": symbol,
                    "repeat_interval": repeat_interval,
                    "is_active": True
                }
                create_resp = await session.post(f"{API_URL}/alerts/", json=create_payload, timeout=10)
                if create_resp.status_code == 200:
                    status_text = repeat_interval if repeat_interval else "안 함"
                    await query.edit_message_text(text=f"'{symbol}'에 대한 신규 알림을 생성하고, 반복 주기를 '{status_text}'으로 설정했습니다.")
                    return
            
            await query.edit_message_text(f"오류: 반복 알림 설정 실패 ({resp.status_code} - {resp.text})")

    except Exception as e:
        logger.error(f"반복 알림 설정 오류: {e}", exc_info=True)
        await query.edit_message_text(f"반복 알림 설정 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


async def set_price_alert(update: Update, context: ContextTypes.DEFAULT_TYPE, repeat_interval: Optional[str] = None):
    """
    /set_price 명령어로 가격 알림을 설정합니다.
    """
    if len(context.args) != 3:
        await update.message.reply_text("사용법: /set_price [종목코드] [가격] [이상|이하]")
        return

    symbol, price, condition_str = context.args[0], None, context.args[2]
    try:
        price = float(context.args[1])
        if condition_str in ["이상", "gte"]:
            condition = "gte"
        elif condition_str in ["이하", "lte"]:
            condition = "lte"
        else:
            raise ValueError()
    except (ValueError, IndexError):
        await update.message.reply_text("입력이 잘못되었습니다. 가격은 숫자여야 하며, 조건은 '이상' 또는 '이하'여야 합니다.")
        return

    user = update.effective_user
    
    payload = {
        "telegram_id": user.id,
        "symbol": symbol,
        "target_price": price,
        "condition": condition,
        "repeat_interval": repeat_interval,
        "is_active": True
    }
    print(f"Sending payload to API: {payload}")

    try:
        resp = await session.post(f"{API_URL}/alerts/", json=payload, timeout=10)
        if resp.status_code == 200:
            await update.message.reply_text(f"✅ '{symbol}'의 가격 알림을 '{price:,}원 {condition_str}'(으)로 설정했습니다.")
        else:
            await update.message.reply_text(f"❌ 가격 알림 설정 실패: {resp.status_code} - {resp.text}")
    except Exception as e:
        await update.message.reply_text(f"가격 알림 설정 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

async def alert_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    try:
        resp = await session.get(f"{API_URL}/alerts/{telegram_id}", timeout=10)
        if resp.status_code == 200:
            alerts = resp.json()
            if not alerts:
                await update.message.reply_text("등록된 알림이 없습니다.")
                return
            msg = "[내 알림 목록]\n"
            user_alerts_map = {}
            for i, a in enumerate(alerts):
                user_alerts_map[str(i+1)] = a['symbol'] # 순번과 symbol 매핑
                price_info = "가격 미설정"
                if a.get("target_price") is not None and a.get("condition"):
                    cond = "이상" if a["condition"] == "gte" else "이하"
                    price_info = f"{a['target_price']:,}원 {cond}"

                disclosure_info = "공시ON" if a.get("notify_on_disclosure") else "공시OFF"
                repeat_info = f"반복: {a.get('repeat_interval', '안 함')}" # 반복 정보 추가
                
                # 현재가 및 등락률 정보 추가
                current_price_resp = await session.get(f"{API_URL}/symbols/{a['symbol']}/current_price_and_change", timeout=5)
                current_price_str = "N/A"
                change_str = ""

                if current_price_resp.status_code == 200:
                    current_stock_data = current_price_resp.json()
                    if current_stock_data and current_stock_data["current_price"] is not None:
                        current_price_str = f"{current_stock_data['current_price']:,}원"
                        if current_stock_data["change"] is not None and current_stock_data["change_rate"] is not None:
                            change_sign = "+" if current_stock_data["change"] >= 0 else ""
                            change_str = f" ({change_sign}{current_stock_data['change']:,}원, {change_sign}{current_stock_data['change_rate']:.2f}%)"
                
                msg += (
                    f"- {i+1}. {a['symbol']} ({a.get('name', '')}): {price_info} / {disclosure_info} / {repeat_info} {'(활성)' if a['is_active'] else '(비활성)'}\n"
                    f"  현재가: {current_price_str}{change_str}\n"
                )
            context.user_data['alert_map'] = user_alerts_map # 매핑 정보 저장
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"알림 목록 조회 실패: {resp.text}")
    except Exception as e:
        await update.message.reply_text(f"알림 목록 조회 중 오류가 발생했습니다: {e}. 잠시 후 다시 시도해주세요.")

async def alert_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("사용법: /alert_remove [알림 번호]")
        return
    
    alert_number = context.args[0]
    alert_map = context.user_data.get('alert_map')

    if not alert_map or alert_number not in alert_map:
        await update.message.reply_text("유효하지 않은 알림 번호입니다. /alert_list 로 알림 목록을 다시 확인해주세요.")
        return

    symbol_to_delete = alert_map[alert_number]
    telegram_id = update.effective_user.id
    try:
        resp = await session.delete(f"{API_URL}/alerts/{telegram_id}/{symbol_to_delete}", timeout=10)
        if resp.status_code == 200:
            await update.message.reply_text(f"알림 번호 {alert_number} ({symbol_to_delete}) 삭제 완료")
            if 'alert_map' in context.user_data: # 삭제 후 맵 업데이트
                del context.user_data['alert_map']
        else:
            await update.message.reply_text(f"알림 삭제 실패: {resp.text}")
    except Exception as e:
        await update.message.reply_text(f"알림 삭제 중 오류가 발생했습니다: {e}. 잠시 후 다시 시도해주세요.")

def get_handler():
    return CommandHandler("alert_add", alert_add)

def get_list_handler():
    return CommandHandler("alert_list", alert_list)

def get_remove_handler():
    return CommandHandler("alert_remove", alert_remove)
