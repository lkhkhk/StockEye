import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import requests
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# FastAPI 서버 URL (로컬에서 실행 시)
API_URL = "http://localhost:8000"

# 텔레그램 봇 토큰 (TODO: 실제 토큰으로 교체하거나 환경 변수 사용)
# TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_BOT_TOKEN = "7794267712:AAF2TPoF7oOpje0GRU4qViTmxZLXczMKwWo"

# 임시 사용자 ID (실제 구현 시에는 텔레그램 user_id 사용)
# 텔레그램 user_id는 update.effective_user.id로 접근 가능
# 여기서는 예시를 위해 임시 ID 사용
# TEMP_USER_ID = 12345
TEMP_USER_ID = 7412973494

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """봇 시작 시 환영 메시지"""
    await update.message.reply_text('안녕하세요! 주식 예측 봇입니다. 종목 코드를 입력하여 예측 결과를 받아보세요. 예: 005930')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """도움말 메시지"""
    await update.message.reply_text('종목 코드를 입력하면 단기 예측 결과를 알려드립니다. 예: 005930\n\n'
                                    '사용 가능한 명령어:\n'
                                    '/start - 봇 시작\n'
                                    '/help - 도움말 보기\n'
                                    '/predict [종목코드] - 특정 종목 예측 (예: /predict 005930)\n'
                                    '/watchlist_add [종목코드] - 관심 종목 추가\n'
                                    '/watchlist_remove [종목코드] - 관심 종목 제거\n'
                                    '/watchlist_get - 관심 종목 목록 조회\n'
                                    '/trade_simulate [buy/sell] [종목코드] [가격] [수량] - 모의 거래 기록 (예: /trade_simulate buy 005930 10000 10)\n'
                                    '/trade_history - 모의 거래 기록 조회')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """사용자 메시지를 처리하여 종목 예측"""
    text = update.message.text
    if text.startswith('/'): # 명령어는 무시
        return

    stock_symbol = text.strip()
    await update.message.reply_text(f"'{stock_symbol}' 종목에 대한 예측 정보를 가져오는 중입니다...")

    try:
        response = requests.post(f"{API_URL}/predict", json={"symbol": stock_symbol})
        response.raise_for_status() # HTTP 오류 발생 시 예외 처리
        prediction_data = response.json()

        prediction = prediction_data.get("prediction", "정보 없음")
        reason = prediction_data.get("reason", "근거 없음")

        message = f"종목: {stock_symbol}\n예측: {prediction}\n근거: {reason}"
        await update.message.reply_text(message)

    except requests.exceptions.RequestException as e:
        logging.error(f"API 호출 오류: {e}")
        await update.message.reply_text("예측 정보를 가져오는 데 실패했습니다. API 서버가 실행 중인지 확인해주세요.")
    except Exception as e:
        logging.error(f"예측 처리 중 오류 발생: {e}")
        await update.message.reply_text("예측 처리 중 오류가 발생했습니다.")

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/predict 명령어 처리"""
    if not context.args:
        await update.message.reply_text("종목 코드를 입력해주세요. 예: /predict 005930")
        return

    stock_symbol = context.args[0].strip()
    await update.message.reply_text(f"'{stock_symbol}' 종목에 대한 예측 정보를 가져오는 중입니다...")

    try:
        response = requests.post(f"{API_URL}/predict", json={"symbol": stock_symbol})
        response.raise_for_status() # HTTP 오류 발생 시 예외 처리
        prediction_data = response.json()

        prediction = prediction_data.get("prediction", "정보 없음")
        reason = prediction_data.get("reason", "근거 없음")

        message = f"종목: {stock_symbol}\n예측: {prediction}\n근거: {reason}"
        await update.message.reply_text(message)

    except requests.exceptions.RequestException as e:
        logging.error(f"API 호출 오류: {e}")
        await update.message.reply_text("예측 정보를 가져오는 데 실패했습니다. API 서버가 실행 중인지 확인해주세요.")
    except Exception as e:
        logging.error(f"예측 처리 중 오류 발생: {e}")
        await update.message.reply_text("예측 처리 중 오류가 발생했습니다.")

async def watchlist_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/watchlist_add 명령어 처리"""
    if not context.args:
        await update.message.reply_text("관심 종목으로 추가할 종목 코드를 입력해주세요. 예: /watchlist_add 005930")
        return

    stock_symbol = context.args[0].strip()
    user_id = update.effective_user.id # 실제 텔레그램 user_id 사용

    try:
        response = requests.post(f"{API_URL}/watchlist/add", json={"user_id": user_id, "symbol": stock_symbol})
        response.raise_for_status()
        result = response.json()
        await update.message.reply_text(result.get("message", "관심 종목 추가 처리 중 오류 발생"))
    except requests.exceptions.RequestException as e:
        logging.error(f"API 호출 오류: {e}")
        await update.message.reply_text("관심 종목 추가 요청에 실패했습니다. API 서버가 실행 중인지 확인해주세요.")
    except Exception as e:
        logging.error(f"관심 종목 추가 처리 중 오류 발생: {e}")
        await update.message.reply_text("관심 종목 추가 처리 중 오류가 발생했습니다.")

async def watchlist_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/watchlist_remove 명령어 처리"""
    if not context.args:
        await update.message.reply_text("관심 종목에서 제거할 종목 코드를 입력해주세요. 예: /watchlist_remove 005930")
        return

    stock_symbol = context.args[0].strip()
    user_id = update.effective_user.id # 실제 텔레그램 user_id 사용

    try:
        response = requests.delete(f"{API_URL}/watchlist/remove", json={"user_id": user_id, "symbol": stock_symbol})
        response.raise_for_status()
        result = response.json()
        await update.message.reply_text(result.get("message", "관심 종목 제거 처리 중 오류 발생"))
    except requests.exceptions.RequestException as e:
        logging.error(f"API 호출 오류: {e}")
        await update.message.reply_text("관심 종목 제거 요청에 실패했습니다. API 서버가 실행 중인지 확인해주세요.")
    except Exception as e:
        logging.error(f"관심 종목 제거 처리 중 오류 발생: {e}")
        await update.message.reply_text("관심 종목 제거 처리 중 오류가 발생했습니다.")

async def watchlist_get_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/watchlist_get 명령어 처리"""
    user_id = update.effective_user.id # 실제 텔레그램 user_id 사용

    try:
        response = requests.get(f"{API_URL}/watchlist/get/{user_id}")
        response.raise_for_status()
        result = response.json()
        watchlist = result.get("watchlist", [])

        if watchlist:
            message = "관심 종목 목록:\n" + "\n".join(watchlist)
        else:
            message = "관심 종목이 없습니다."

        await update.message.reply_text(message)
    except requests.exceptions.RequestException as e:
        logging.error(f"API 호출 오류: {e}")
        await update.message.reply_text("관심 종목 목록 조회 요청에 실패했습니다. API 서버가 실행 중인지 확인해주세요.")
    except Exception as e:
        logging.error(f"관심 종목 목록 조회 처리 중 오류 발생: {e}")
        await update.message.reply_text("관심 종목 목록 조회 처리 중 오류가 발생했습니다.")

async def trade_simulate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/trade_simulate 명령어 처리"""
    if len(context.args) != 4:
        await update.message.reply_text("사용법: /trade_simulate [buy/sell] [종목코드] [가격] [수량]\n예: /trade_simulate buy 005930 10000 10")
        return

    trade_type = context.args[0].lower()
    stock_symbol = context.args[1].strip()
    try:
        price = float(context.args[2])
        quantity = int(context.args[3])
    except ValueError:
        await update.message.reply_text("가격과 수량은 숫자로 입력해주세요.")
        return

    if trade_type not in ["buy", "sell"]:
        await update.message.reply_text("trade_type은 'buy' 또는 'sell'이어야 합니다.")
        return

    user_id = update.effective_user.id # 실제 텔레그램 user_id 사용

    try:
        response = requests.post(f"{API_URL}/trade/simulate", json={
            "user_id": user_id,
            "symbol": stock_symbol,
            "trade_type": trade_type,
            "price": price,
            "quantity": quantity
        })
        response.raise_for_status()
        result = response.json()
        await update.message.reply_text(result.get("message", "모의 거래 기록 처리 중 오류 발생"))
    except requests.exceptions.RequestException as e:
        logging.error(f"API 호출 오류: {e}")
        await update.message.reply_text("모의 거래 기록 요청에 실패했습니다. API 서버가 실행 중인지 확인해주세요.")
    except Exception as e:
        logging.error(f"모의 거래 기록 처리 중 오류 발생: {e}")
        await update.message.reply_text("모의 거래 기록 처리 중 오류가 발생했습니다.")

async def trade_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/trade_history 명령어 처리"""
    user_id = update.effective_user.id # 실제 텔레그램 user_id 사용

    try:
        response = requests.get(f"{API_URL}/trade/history/{user_id}")
        response.raise_for_status()
        result = response.json()
        trades = result.get("trades", [])

        if trades:
            message = "모의 거래 기록:\n"
            for trade in trades:
                trade_time_str = datetime.fromisoformat(trade["trade_time"]).strftime("%Y-%m-%d %H:%M:%S")
                message += f"- [{trade_time_str}] {trade['trade_type'].upper()} {trade['symbol']} {trade['quantity']}주 @ {trade['price']}원\n"
        else:
            message = "모의 거래 기록이 없습니다."

        await update.message.reply_text(message)
    except requests.exceptions.RequestException as e:
        logging.error(f"API 호출 오류: {e}")
        await update.message.reply_text("모의 거래 기록 조회 요청에 실패했습니다. API 서버가 실행 중인지 확인해주세요.")
    except Exception as e:
        logging.error(f"모의 거래 기록 조회 처리 중 오류 발생: {e}")
        await update.message.reply_text("모의 거래 기록 조회 처리 중 오류가 발생했습니다.")


def main() -> None:
    """봇 시작 함수"""
    # ApplicationBuilder를 사용하여 봇 인스턴스 생성
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # 명령어 핸들러 추가
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("predict", predict_command))
    application.add_handler(CommandHandler("watchlist_add", watchlist_add_command))
    application.add_handler(CommandHandler("watchlist_remove", watchlist_remove_command))
    application.add_handler(CommandHandler("watchlist_get", watchlist_get_command))
    application.add_handler(CommandHandler("trade_simulate", trade_simulate_command))
    application.add_handler(CommandHandler("trade_history", trade_history_command))


    # 일반 메시지 핸들러 추가 (명령어 제외)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


    # 봇 실행
    print("텔레그램 봇이 시작되었습니다. 메시지를 기다리는 중...")
    application.run_polling(poll_interval=3.0) # 3초 간격으로 업데이트 확인

if __name__ == "__main__":
    main()
