import os
import re
from telegram import Update
from telegram.ext import ContextTypes
from src.common.http_client import session
import httpx # httpx 임포트 추가

API_HOST = os.getenv("API_HOST", "localhost")
API_URL = f"http://{API_HOST}:8000"

# 종목명/코드 추출 및 예측/상세 안내
async def natural_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    symbol = None

    # 1. 6자리 숫자 종목코드 우선 추출
    code_match = re.search(r'\b\d{6}\b', text)
    if code_match:
        symbol = code_match.group(0)
    
    # 2. 종목코드가 없으면 메시지 전체를 쿼리로 사용하여 종목명 검색 시도
    if not symbol:
        try:
            response = await session.get(f"{API_URL}/symbols/search", params={"query": text}, timeout=10)
            response.raise_for_status()
            data = await response.json()
            if data:
                symbol = data[0]["symbol"]
        except httpx.HTTPStatusError:
            pass # 검색 결과 없음 또는 HTTP 오류는 무시하고 다음 단계로 진행
        except Exception as e:
            print(f"Error during full text search: {e}") # 디버깅용
            pass

    # 3. 메시지 전체로도 못 찾았으면 단어별로 검색 시도
    if not symbol:
        words = re.findall(r'[가-힣A-Za-z0-9]+', text)
        for word in words:
            q = word.strip()
            if not q: continue
            try:
                response = await session.get(f"{API_URL}/symbols/search", params={"query": q}, timeout=10)
                response.raise_for_status()
                data = await response.json()
                if data:
                    symbol = data[0]["symbol"]
                    break
            except httpx.HTTPStatusError:
                pass
            except Exception as e:
                print(f"Error during word-by-word search for '{q}': {e}") # 디버깅용
                pass

    if not symbol:
        await update.message.reply_text("메시지에서 종목코드(6자리)나 종목명을 찾을 수 없습니다. 예: '삼성전자 얼마야', '005930 예측'")
        return

    # 4. 예측/상세 안내
    if "예측" in text or "predict" in text or "얼마" in text or "가격" in text:
        # 예측 결과 안내
        try:
            response = await session.post(f"{API_URL}/predict", json={"symbol": symbol}, timeout=10)
            response.raise_for_status()
            data = await response.json()
            msg = f"[예측 결과] {symbol}: {data.get('prediction', 'N/A')}\n사유: {data.get('reason', '')}"
            await update.message.reply_text(msg)
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response and e.response.text else str(e)
            await update.message.reply_text(f"예측 실패: {error_detail}")
        except Exception as e:
            await update.message.reply_text(f"예측 실패: {e}")
    else:
        # 종목 상세 안내
        try:
            response = await session.get(f"{API_URL}/symbols/search", params={"query": symbol}, timeout=10)
            response.raise_for_status()
            data = await response.json()
            if not data:
                await update.message.reply_text("해당 종목을 찾을 수 없습니다.")
                return
            info = data[0]
            msg = f"[종목 상세]\n코드: {info['symbol']}\n이름: {info['name']}\n시장: {info.get('market','')}"
            await update.message.reply_text(msg)
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response and e.response.text else str(e)
            await update.message.reply_text(f"종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (오류: {error_detail})")
        except Exception as e:
            await update.message.reply_text(f"종목 상세 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (오류: {e})") 