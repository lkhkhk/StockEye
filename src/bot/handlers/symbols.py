import os
import requests
from telegram import Update
from telegram.ext import ContextTypes

API_URL = os.getenv("API_URL", "http://api_service:8000")

async def symbols_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(f"{API_URL}/symbols/")
        response.raise_for_status()
        data = response.json()
        if not data:
            await update.message.reply_text("등록된 종목이 없습니다.")
            return
        msg = "[종목 목록]\n" + "\n".join([f"{item['symbol']} {item['name']} ({item.get('market','')})" for item in data])
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"종목 목록 조회 실패: {e}")

async def symbols_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /symbols_search [키워드] 예: /symbols_search 삼성")
        return
    query = context.args[0]
    try:
        response = requests.get(f"{API_URL}/symbols/search", params={"query": query})
        response.raise_for_status()
        data = response.json()
        if not data:
            await update.message.reply_text("검색 결과가 없습니다.")
            return
        msg = "[종목 검색 결과]\n" + "\n".join([f"{item['symbol']} {item['name']} ({item.get('market','')})" for item in data])
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"종목 검색 실패: {e}")

async def symbol_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /symbol_info [종목코드] 예: /symbol_info 005930")
        return
    symbol = context.args[0]
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