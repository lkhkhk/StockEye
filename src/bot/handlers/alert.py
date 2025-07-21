from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
import requests
import os

# --- Helper Functions ---
def get_alert_options_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """가격/공시 알림 설정 인라인 키보드를 생성합니다."""
    keyboard = [
        [InlineKeyboardButton("가격 알림 설정/수정", callback_data=f"alert_price_{symbol}")],
        [InlineKeyboardButton("공시 알림 켜기/끄기", callback_data=f"alert_disclosure_{symbol}")],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Command Handlers ---
async def alert_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    종목에 대한 알림 설정을 시작합니다.
    종목명/코드로 검색하고, 결과에 따라 선택지를 제공합니다.
    """
    if not context.args:
        await update.message.reply_text("사용법: /alert_add [종목코드 또는 종목명]")
        return
    
    query_str = " ".join(context.args)
    api_url = os.getenv("API_URL", "http://api_service:8000")

    try:
        search_resp = requests.get(f"{api_url}/symbols/search", params={"query": query_str}, timeout=5)
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
        await update.message.reply_text(f"API 요청 실패: {e}")

async def alert_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """알림 설정 관련 인라인 버튼 콜백을 처리합니다."""
    query = update.callback_query
    await query.answer()

    try:
        data = query.data
        parts = data.split('_', 2)
        # callback_data format: "alert_{action}_{symbol}"
        action = parts[1]
        symbol = parts[2]

        if action == "select":
            reply_markup = get_alert_options_keyboard(symbol)
            await query.edit_message_text(f"'{symbol}'에 대한 알림을 설정합니다. 원하는 작업을 선택하세요.", reply_markup=reply_markup)
            return

        api_url = os.getenv("API_URL", "http://api_service:8000")
        user = query.from_user

        if action == "price":
            await query.edit_message_text(text=f"'{symbol}'의 가격 알림을 설정하려면, 채팅창에 다음과 같이 입력해주세요:\n\n`/set_price {symbol} [가격] [이상|이하]`\n\n(예: `/set_price {symbol} 75000 이상`)")
        
        elif action == "disclosure":
            payload = {
                "telegram_user_id": user.id,
                "telegram_username": user.username,
                "telegram_first_name": user.first_name,
                "telegram_last_name": user.last_name,
                "symbol": symbol,
            }
            
            resp = requests.post(f"{api_url}/bot/alert/disclosure-toggle", json=payload, timeout=5)

            if resp.status_code == 200:
                result = resp.json()
                new_status = result.get("notify_on_disclosure")
                status_text = "ON" if new_status else "OFF"
                await query.edit_message_text(text=f"'{symbol}'의 공시 알림을 '{status_text}' 상태로 변경했습니다.")
            else:
                await query.edit_message_text(f"오류: 공시 알림 설정 실패 ({resp.status_code} - {resp.text})")

    except Exception as e:
        await query.edit_message_text(f"오류 발생: {e}")

async def set_price_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /set_price 명령어로 가격 알림을 설정합니다.
    """
    if len(context.args) != 3:
        await update.message.reply_text("사용법: /set_price [종목코드] [가격] [이상|이하]")
        return

    symbol, price, condition = context.args[0], None, None
    try:
        price = float(context.args[1])
        cond_str = context.args[2]
        if cond_str in ["이상", "gte"]:
            condition = "gte"
        elif cond_str in ["이하", "lte"]:
            condition = "lte"
        else:
            raise ValueError()
    except (ValueError, IndexError):
        await update.message.reply_text("입력이 잘못되었습니다. 가격은 숫자여야 하며, 조건은 '이상' 또는 '이하'여야 합니다.")
        return

    api_url = os.getenv("API_URL", "http://api_service:8000")
    user = update.effective_user
    
    payload = {
        "telegram_user_id": user.id,
        "telegram_username": user.username,
        "telegram_first_name": user.first_name,
        "telegram_last_name": user.last_name,
        "symbol": symbol,
        "target_price": price,
        "condition": condition
    }

    try:
        resp = requests.post(f"{api_url}/bot/alert/price", json=payload, timeout=5)
        if resp.status_code == 200:
            await update.message.reply_text(f"✅ '{symbol}'의 가격 알림을 '{price:,}원 {cond_str}'(으)로 설정했습니다.")
        else:
            await update.message.reply_text(f"❌ 가격 알림 설정 실패: {resp.status_code} - {resp.text}")
    except Exception as e:
        await update.message.reply_text(f"API 요청 실패: {e}")

async def alert_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_url = os.getenv("API_URL", "http://api_service:8000")
    try:
        # TODO: JWT 인증을 통해 현재 사용자의 알림만 가져오도록 수정 필요
        resp = requests.get(f"{api_url}/alerts/", timeout=5)
        if resp.status_code == 200:
            alerts = resp.json()
            if not alerts:
                await update.message.reply_text("등록된 알림이 없습니다.")
                return
            msg = "[내 알림 목록]\n"
            for a in alerts:
                price_info = "가격 미설정"
                if a.get("target_price") is not None and a.get("condition"):
                    cond = "이상" if a["condition"] == "gte" else "이하"
                    price_info = f"{a['target_price']:,}원 {cond}"

                disclosure_info = "공시ON" if a.get("notify_on_disclosure") else "공시OFF"
                
                msg += f"- {a['symbol']} ({a.get('name', '')}): {price_info} / {disclosure_info} {'(활성)' if a['is_active'] else '(비활성)'}\n"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"알림 목록 조회 실패: {resp.text}")
    except Exception as e:
        await update.message.reply_text(f"API 요청 실패: {e}")

async def alert_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("사용법: /alert_remove [알림ID]")
        return
    alert_id = context.args[0]
    api_url = os.getenv("API_URL", "http://api_service:8000")
    try:
        resp = requests.delete(f"{api_url}/alerts/{alert_id}", timeout=5)
        if resp.status_code == 200:
            await update.message.reply_text(f"알림 ID {alert_id} 삭제 완료")
        else:
            await update.message.reply_text(f"알림 삭제 실패: {resp.text}")
    except Exception as e:
        await update.message.reply_text(f"API 요청 실패: {e}")

def get_handler():
    return CommandHandler("alert_add", alert_add)

def get_list_handler():
    return CommandHandler("alert_list", alert_list)

def get_remove_handler():
    return CommandHandler("alert_remove", alert_remove) 