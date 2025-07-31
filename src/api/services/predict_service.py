from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pandas as pd
from src.api.models.daily_price import DailyPrice
import logging

logger = logging.getLogger(__name__)

class PredictService:
    def __init__(self):
        pass

    def get_recent_prices(self, db: Session, symbol: str, days: int = 40):
        logger.debug(f"get_recent_prices 호출: symbol={symbol}, days={days}")
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            rows = db.query(DailyPrice).filter(
                DailyPrice.symbol == symbol,
                DailyPrice.date >= start_date,
                DailyPrice.date <= end_date
            ).order_by(DailyPrice.date.asc()).all()
            # SQLAlchemy 객체를 dict로 변환
            recent_prices_data = [
                {
                    "date": row.date,
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "volume": row.volume
                }
                for row in rows
            ]
            logger.debug(f"get_recent_prices 결과: {len(recent_prices_data)}개 데이터.")
            return recent_prices_data
        except Exception as e:
            logger.error(f"get_recent_prices 실패: {str(e)}", exc_info=True)
            return []

    def calculate_analysis_items(self, data):
        logger.debug(f"calculate_analysis_items 호출: {len(data)}개 데이터.")
        if not data or len(data) < 2:
            logger.warning("분석 데이터 부족: 2개 미만")
            return None
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date').reset_index(drop=True)
        df['daily_change_percent'] = df['close'].pct_change() * 100
        df['sma_5'] = df['close'].rolling(window=5).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()

        # RSI 계산
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD 계산
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['signal_line']

        movement_type = "정보 부족"
        if len(df) >= 2:
            latest_change_percent = df['daily_change_percent'].iloc[-1]
            if pd.notna(latest_change_percent):
                if abs(latest_change_percent) >= 4:
                    movement_type = "급등" if latest_change_percent > 0 else "급락"
                elif abs(latest_change_percent) < 1:
                    movement_type = "횡보"
                else:
                    movement_type = "보합"
        trend = "정보 부족"
        if len(df) >= 20 and pd.notna(df['sma_5'].iloc[-1]) and pd.notna(df['sma_20'].iloc[-1]):
            if df['sma_5'].iloc[-1] > df['sma_20'].iloc[-1]:
                trend = "상승"
            elif df['sma_5'].iloc[-1] < df['sma_20'].iloc[-1]:
                trend = "하락"
            else:
                trend = "횡보"
        trend_duration = 0
        if len(df) >= 2:
            last_direction = None
            if df['close'].iloc[-1] > df['close'].iloc[-2]:
                last_direction = 'up'
            elif df['close'].iloc[-1] < df['close'].iloc[-2]:
                last_direction = 'down'
            if last_direction:
                count = 0
                for i in range(len(df) - 1, 0, -1):
                    current_direction = None
                    if df['close'].iloc[i] > df['close'].iloc[i-1]:
                        current_direction = 'up'
                    elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                        current_direction = 'down'
                    if current_direction == last_direction:
                        count += 1
                    else:
                        break
                trend_duration = count
        volume_trend_duration = 0
        if len(df) >= 2:
            last_volume_direction = None
            if df['volume'].iloc[-1] > df['volume'].iloc[-2]:
                last_volume_direction = 'up'
            elif df['volume'].iloc[-1] < df['volume'].iloc[-2]:
                last_volume_direction = 'down'
            if last_volume_direction:
                count = 0
                for i in range(len(df) - 1, 0, -1):
                    current_volume_direction = None
                    if df['volume'].iloc[i] > df['volume'].iloc[i-1]:
                        current_volume_direction = 'up'
                    elif df['volume'].iloc[i] < df['volume'].iloc[i-1]:
                        current_volume_direction = 'down'
                    if current_volume_direction == last_volume_direction:
                        count += 1
                    else:
                        break
                volume_trend_duration = count
        up_count_20d = 0
        down_count_20d = 0
        if len(df) >= 20:
            recent_closes_20d = df['close'].iloc[-20:]
            for i in range(1, len(recent_closes_20d)):
                if recent_closes_20d.iloc[i] > recent_closes_20d.iloc[i-1]:
                    up_count_20d += 1
                elif recent_closes_20d.iloc[i] < recent_closes_20d.iloc[i-1]:
                    down_count_20d += 1
        trend_count = {"up": up_count_20d, "down": down_count_20d}
        prediction = "hold"
        if len(df) >= 3:
            movement_type_latest = movement_type
            prev_change_percent = df['daily_change_percent'].iloc[-2] if len(df) >= 2 else None
            movement_type_prev = "보합"
            if pd.notna(prev_change_percent):
                if abs(prev_change_percent) >= 4:
                    movement_type_prev = "급등" if prev_change_percent > 0 else "급락"
                elif abs(prev_change_percent) < 1:
                    movement_type_prev = "횡보"
                else:
                    movement_type_prev = "보합"
            if movement_type_latest == "횡보" and movement_type_prev == "급등":
                prediction = "sell"
        # 예측 및 신뢰도 계산
        # 예측 및 신뢰도 계산
        prediction = "hold"
        confidence = 50 # 기본 신뢰도 (중립)
        
        latest_close = df['close'].iloc[-1]
        latest_sma_5 = df['sma_5'].iloc[-1]
        latest_sma_20 = df['sma_20'].iloc[-1]
        latest_rsi = df['rsi'].iloc[-1]
        latest_macd = df['macd'].iloc[-1]
        latest_signal_line = df['signal_line'].iloc[-1]
        latest_macd_histogram = df['macd_histogram'].iloc[-1]

        reason_parts = []
        buy_score = 0
        sell_score = 0

        # 1. SMA 기반 추세 분석
        if pd.notna(latest_sma_5) and pd.notna(latest_sma_20):
            if latest_sma_5 > latest_sma_20:
                trend = "상승"
                reason_parts.append("단기 이동평균선이 장기 이동평균선 위에 있습니다 (골든 크로스 또는 정배열).")
                buy_score += 15
                if latest_close > latest_sma_5:
                    reason_parts.append("현재가가 단기 이동평균선 위에 있습니다.")
                    buy_score += 5
                if latest_sma_5 > df['sma_5'].iloc[-2] and latest_sma_20 > df['sma_20'].iloc[-2]:
                    reason_parts.append("단기 및 장기 이동평균선이 모두 상승 중입니다.")
                    buy_score += 5
            elif latest_sma_5 < latest_sma_20:
                trend = "하락"
                reason_parts.append("단기 이동평균선이 장기 이동평균선 아래에 있습니다 (데드 크로스 또는 역배열).")
                sell_score += 15
                if latest_close < latest_sma_5:
                    reason_parts.append("현재가가 단기 이동평균선 아래에 있습니다.")
                    sell_score += 5
                if latest_sma_5 < df['sma_5'].iloc[-2] and latest_sma_20 < df['sma_20'].iloc[-2]:
                    reason_parts.append("단기 및 장기 이동평균선이 모두 하락 중입니다.")
                    sell_score += 5
            else:
                trend = "횡보"
                reason_parts.append("단기 이동평균선과 장기 이동평균선이 수렴 중입니다 (횡보).")

        # 2. RSI 기반 예측
        if pd.notna(latest_rsi):
            if latest_rsi > 70:
                reason_parts.append(f"RSI({int(latest_rsi)})가 70 이상으로 과매수 구간입니다.")
                sell_score += 20 # 강한 매도 신호
            elif latest_rsi < 30:
                reason_parts.append(f"RSI({int(latest_rsi)})가 30 이하로 과매도 구간입니다.")
                buy_score += 20 # 강한 매수 신호
            else:
                reason_parts.append(f"RSI({int(latest_rsi)})는 중립 구간입니다.")

        # 3. MACD 기반 예측
        if pd.notna(latest_macd) and pd.notna(latest_signal_line) and pd.notna(latest_macd_histogram):
            if latest_macd > latest_signal_line and latest_macd_histogram > 0:
                reason_parts.append("MACD가 시그널 라인 위에 있고 MACD 히스토그램이 양수입니다 (매수 신호).")
                buy_score += 15
            elif latest_macd < latest_signal_line and latest_macd_histogram < 0:
                reason_parts.append("MACD가 시그널 라인 아래에 있고 MACD 히스토그램이 음수입니다 (매도 신호).")
                sell_score += 15
            else:
                reason_parts.append("MACD는 중립 신호입니다.")

        # 4. 가격 움직임 패턴 기반 예측 (기존 로직 유지 및 강화)
        if len(df) >= 3:
            movement_type_latest = movement_type
            prev_change_percent = df['daily_change_percent'].iloc[-2] if len(df) >= 2 else None
            movement_type_prev = "보합"
            if pd.notna(prev_change_percent):
                if abs(prev_change_percent) >= 4:
                    movement_type_prev = "급등" if prev_change_percent > 0 else "급락"
                elif abs(prev_change_percent) < 1:
                    movement_type_prev = "횡보"
                else:
                    movement_type_prev = "보합"
            
            if movement_type_latest == "횡보" and movement_type_prev == "급등":
                reason_parts.append("급등 후 횡보 패턴 감지 (차익 실현 가능성).")
                sell_score += 10
            elif trend == "횡보" and len(df) >= 20: # 횡보 추세에서 저점 매수 기회
                recent_closes_20d = df['close'].iloc[-20:]
                min_price_20d = recent_closes_20d.min()
                if latest_close <= min_price_20d * 1.02:
                    reason_parts.append("저점 횡보 패턴 감지 (매수 기회).")
                    buy_score += 10

        # 최종 예측 결정 및 신뢰도 계산
        if buy_score > sell_score:
            prediction = "buy"
            confidence = min(100, 50 + (buy_score - sell_score))
        elif sell_score > buy_score:
            prediction = "sell"
            confidence = min(100, 50 + (sell_score - buy_score))
        else:
            prediction = "hold"
            confidence = 50 # 중립일 경우 기본 신뢰도

        reason = " ".join(reason_parts) if reason_parts else "현재 데이터로는 명확한 예측 신호를 찾기 어렵습니다."

        logger.debug(f"calculate_analysis_items 결과: prediction={prediction}, confidence={confidence}, reason={reason}")
        return {
            "prediction": prediction,
            "confidence": confidence,
            "trend": trend,
            "trend_duration": f"{trend_duration}일",
            "movement_type": movement_type,
            "volume_trend_duration": f"{volume_trend_duration}일",
            "trend_count": trend_count,
            "reason": reason,
        }

    def predict_stock_movement(self, db: Session, symbol: str):
        logger.debug(f"predict_stock_movement 호출: symbol={symbol}")
        recent_data = self.get_recent_prices(db, symbol, days=40)
        if len(recent_data) < 20:
            logger.warning(f"예측 불가: 데이터 부족({len(recent_data)}일)")
            return {
                "prediction": "예측 불가",
                "trend": "정보 부족",
                "trend_duration": "N/A",
                "movement_type": "정보 부족",
                "volume_trend_duration": "N/A",
                "trend_count": {"up": 0, "down": 0},
                "reason": f"분석에 필요한 데이터({len(recent_data)}일)가 부족합니다 (최소 20일 필요).",
                "confidence": 0
            }
        analysis_result = self.calculate_analysis_items(recent_data)
        if analysis_result is None:
            logger.error("예측 불가: 데이터 분석 실패")
            return {
                "prediction": "예측 불가",
                "trend": "정보 부족",
                "trend_duration": "N/A",
                "movement_type": "정보 부족",
                "volume_trend_duration": "N/A",
                "trend_count": {"up": 0, "down": 0},
                "reason": "데이터 분석 중 오류가 발생했습니다.",
                "confidence": 0
            }
        logger.debug(f"predict_stock_movement 결과: {analysis_result['prediction']}")
        return analysis_result