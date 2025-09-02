from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pandas as pd
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice
import logging
import asyncio

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class PredictService:
    def __init__(self):
        pass

    def get_recent_prices(self, db: Session, symbol: str, days: int = 40):
        """
        DB에서 특정 종목의 최근 N일치 일별 시세 데이터를 가져옵니다.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        prices = db.query(DailyPrice).filter(
            DailyPrice.symbol == symbol,
            DailyPrice.date >= start_date,
            DailyPrice.date <= end_date
        ).order_by(DailyPrice.date.asc()).all() # 오래된 날짜부터 정렬
        
        # SQLAlchemy 객체를 딕셔너리 리스트로 변환
        return [{
            "date": p.date,
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume
        } for p in prices]

    def calculate_analysis_items(self, data: list[dict]) -> dict:
        """
        주어진 일별 시세 데이터를 기반으로 기술적 분석 지표를 계산하고 예측을 수행합니다.
        """
        if not data or len(data) < 20: # 최소 20일치 데이터 필요 (SMA 20 계산 위함)
            logger.warning(f"데이터 부족: {len(data)}일치 데이터로는 분석을 수행할 수 없습니다. 최소 20일치 데이터가 필요합니다.")
            return None

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df = df.sort_index() # 날짜 오름차순 정렬

        # 이동평균선 (Moving Average)
        df['SMA5'] = df['close'].rolling(window=5).mean()
        df['SMA20'] = df['close'].rolling(window=20).mean()

        # RSI (Relative Strength Index)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))

        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['signal_line']

        latest_close = df['close'].iloc[-1]
        latest_sma_5 = df['SMA5'].iloc[-1]
        latest_sma_20 = df['SMA20'].iloc[-1]
        latest_rsi = df['rsi'].iloc[-1]
        latest_macd = df['macd'].iloc[-1]
        latest_signal_line = df['signal_line'].iloc[-1]

        reason_parts = []
        buy_score = 0
        sell_score = 0

        if pd.notna(latest_sma_5) and pd.notna(latest_sma_20):
            if latest_sma_5 > latest_sma_20:
                reason_parts.append("단기 이동평균선이 장기 이동평균선 위에 있습니다 (골든 크로스).")
                buy_score += 15
            elif latest_sma_5 < latest_sma_20:
                reason_parts.append("단기 이동평균선이 장기 이동평균선 아래에 있습니다 (데드 크로스).")
                sell_score += 15

        if pd.notna(latest_rsi):
            if latest_rsi > 70:
                reason_parts.append(f"RSI({int(latest_rsi)})가 과매수 구간입니다.")
                sell_score += 25
            elif latest_rsi < 30:
                reason_parts.append(f"RSI({int(latest_rsi)})가 과매도 구간입니다.")
                buy_score += 25

        if pd.notna(latest_macd) and pd.notna(latest_signal_line):
            if latest_macd > latest_signal_line:
                reason_parts.append("MACD가 시그널 라인을 상향 돌파했습니다.")
                buy_score += 20
            elif latest_macd < latest_signal_line:
                reason_parts.append("MACD가 시그널 라인을 하향 돌파했습니다.")
                sell_score += 20

        if buy_score > sell_score:
            prediction = "buy"
            confidence = min(100, 50 + (buy_score - sell_score))
        elif sell_score > buy_score:
            prediction = "sell"
            confidence = min(100, 50 + (sell_score - buy_score))
        else:
            prediction = "hold"
            confidence = 50

        reason = " ".join(reason_parts) if reason_parts else "현재 데이터로는 명확한 예측 신호를 찾기 어렵습니다."
        
        return {
            "prediction": prediction,
            "confidence": confidence,
            "reason": reason
        }

    async def predict_stock_movement(self, db: Session, symbol: str, user_id: int = None):
        logger.debug(f"predict_stock_movement 호출: symbol={symbol}")
        stock = await asyncio.to_thread(lambda: db.query(StockMaster).filter(StockMaster.symbol == symbol).first()) # 이 라인을 추가합니다.
        if not stock:
            logger.warning(f"종목을 찾을 수 없습니다: {symbol}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"종목을 찾을 수 없습니다: {symbol}")

        recent_data = self.get_recent_prices(db, symbol, days=40)
        if len(recent_data) < 20:
            logger.warning(f"예측 불가: 데이터 부족({len(recent_data)}일)")
            return {
                "prediction": "예측 불가",
                "reason": f"분석에 필요한 데이터({len(recent_data)}일)가 부족합니다 (최소 20일 필요).",
                "confidence": 0
            }

        analysis_result = self.calculate_analysis_items(recent_data)
        
        if analysis_result is None:
            logger.error("예측 불가: 데이터 분석 실패")
            return {
                "prediction": "예측 불가",
                "reason": "데이터 분석 중 오류가 발생했습니다.",
                "confidence": 0
            }

        logger.debug(f"predict_stock_movement 결과: {analysis_result['prediction']}")
        return analysis_result
