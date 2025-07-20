from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pandas as pd
from src.api.models.daily_price import DailyPrice
import logging

logger = logging.getLogger(__name__)

# 최근 N일간 주가 데이터 조회

def get_recent_prices(db: Session, symbol: str, days: int = 40):
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        rows = db.query(DailyPrice).filter(
            DailyPrice.symbol == symbol,
            DailyPrice.date >= start_date,
            DailyPrice.date <= end_date
        ).order_by(DailyPrice.date.asc()).all()
        # SQLAlchemy 객체를 dict로 변환
        return [
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
    except Exception as e:
        logger.error(f"get_recent_prices 실패: {str(e)}", exc_info=True)
        return []

def calculate_analysis_items(data):
    if not data or len(data) < 2:
        logger.warning("분석 데이터 부족: 2개 미만")
        return None
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date').reset_index(drop=True)
    df['daily_change_percent'] = df['close'].pct_change() * 100
    df['sma_5'] = df['close'].rolling(window=5).mean()
    df['sma_20'] = df['close'].rolling(window=20).mean()
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
    if len(df) >= 20:
        if len(df) >= 3:
            movement_type_latest = movement_type
            prev_change_percent = df['daily_change_percent'].iloc[-2] if len(df) >= 2 else None
            movement_type_prev = "정보 부족"
            if pd.notna(prev_change_percent):
                if abs(prev_change_percent) >= 4:
                    movement_type_prev = "급등" if prev_change_percent > 0 else "급락"
                elif abs(prev_change_percent) < 1:
                    movement_type_prev = "횡보"
                else:
                    movement_type_prev = "보합"
            if movement_type_latest == "횡보" and movement_type_prev == "급등":
                prediction = "sell"
        if prediction == "hold":
            recent_closes_20d = df['close'].iloc[-20:]
            min_price_20d = recent_closes_20d.min()
            latest_price = df['close'].iloc[-1]
            if movement_type_latest == "횡보" and latest_price <= min_price_20d * 1.02:
                prediction = "buy"
    reason = f"최근 추세: {trend} ({trend_duration}일 지속). 금일 변동: {movement_type}. 최근 20일간 상승일: {trend_count['up']}일, 하락일: {trend_count['down']}일."
    if prediction == "buy":
        reason += " (저점 횡보 패턴 감지)"
    elif prediction == "sell":
        reason += " (급등 후 횡보 패턴 감지)"
    return {
        "prediction": prediction,
        "trend": trend,
        "trend_duration": f"{trend_duration}일",
        "movement_type": movement_type,
        "volume_trend_duration": f"{volume_trend_duration}일",
        "trend_count": trend_count,
        "reason": reason,
    }

def predict_stock_movement(db: Session, symbol: str):
    recent_data = get_recent_prices(db, symbol, days=40)
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
        }
    analysis_result = calculate_analysis_items(recent_data)
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
        }
    return analysis_result 