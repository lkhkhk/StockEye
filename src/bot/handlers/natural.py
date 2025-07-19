import os
import requests
import re
from telegram import Update
from telegram.ext import ContextTypes

API_URL = os.getenv("API_URL", "http://api_service:8000")

# 종목명/코드 추출 및 예측/상세 안내
async def natural_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # 종목코드(숫자 6자리) 우선 추출
    code_match = re.search(r'\b\d{6}\b', text)
    symbol = None
    if code_match:
        symbol = code_match.group(0)
    else:
        # 메시지에서 한글/영문/숫자 단어 추출
        words = re.findall(r'[가-힣A-Za-z0-9]+', text)
        for word in words:
            try:
                q = word.strip()
                response = requests.get(f"{API_URL}/symbols/search", params={"query": q})
                response.raise_for_status()
                data = response.json()
                if data:
                    symbol = data[0]["symbol"]
                    break
            except Exception as e:
                await update.message.reply_text(f"[DEBUG] 검색 쿼리: {q}, 예외: {e}")
        if not symbol:
            await update.message.reply_text(f"[DEBUG] 단어별 검색 결과 없음: {words}")
    if not symbol:
        await update.message.reply_text("메시지에서 종목코드(6자리)나 종목명을 찾을 수 없습니다. 예: '삼성전자 얼마야', '005930 예측'")
        return
    # 예측/상세 안내
    if "예측" in text or "predict" in text or "얼마" in text or "가격" in text:
        # 예측 결과 안내
        try:
            response = requests.post(f"{API_URL}/predict", json={"symbol": symbol})
            response.raise_for_status()
            data = response.json()
            msg = f"[예측 결과] {symbol}: {data.get('prediction', 'N/A')}\n사유: {data.get('reason', '')}"
            await update.message.reply_text(msg)
        except Exception as e:
            await update.message.reply_text(f"예측 실패: {e}")
    else:
        # 종목 상세 안내
        try:
            response = requests.get(f"{API_URL}/symbols/search", params={"query": symbol})
            response.raise_for_status()
            data = response.json()
            if not data:
                await update.message.reply_text("해당 종목을 찾을 수 없습니다.")
                return
            info = data[0]
            msg = f"[종목 상세]\n코드: {info['symbol']}\n이름: {info['name']}\n시장: {info.get('market','')}"
            await update.message.reply_text(msg)
        except Exception as e:
            await update.message.reply_text(f"종목 상세 조회 실패: {e}") 