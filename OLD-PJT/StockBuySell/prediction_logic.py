import sqlite3
from datetime import datetime, timedelta
import pandas as pd # Use pandas for easier SMA calculation and data handling
import json # Import json for output formatting

DATABASE_URL = "stock_prediction.db"

def get_db():
    db = sqlite3.connect(DATABASE_URL)
    db.row_factory = sqlite3.Row
    return db

def get_recent_prices(symbol, days=7):
    """
    데이터베이스에서 특정 종목의 최근 주가 데이터를 가져옵니다.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    with get_db() as db:
        cursor = db.cursor()
        # Fetch date, open, close, volume for more detailed analysis
        cursor.execute(
            """
            SELECT date, open, close, volume
            FROM daily_prices
            WHERE symbol = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC
            """,
            (symbol, start_date_str, end_date_str)
        )
        # Return data as a list of dictionaries
        return [dict(row) for row in cursor.fetchall()]

def calculate_analysis_items(data):
    """
    주가 데이터를 기반으로 분석 항목을 계산합니다.
    데이터는 날짜 오름차순이어야 합니다.
    """
    if not data or len(data) < 2: # Need at least 2 days for change calculations
        return None # Or handle appropriately

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date').reset_index(drop=True)

    # Calculate daily percentage change (close vs previous close)
    df['daily_change_percent'] = df['close'].pct_change() * 100

    # Calculate SMAs
    df['sma_5'] = df['close'].rolling(window=5).mean()
    df['sma_20'] = df['close'].rolling(window=20).mean()

    # --- Calculate Analysis Items ---

    # movement_type (based on latest day's change)
    movement_type = "정보 부족"
    if len(df) >= 2:
        latest_change_percent = df['daily_change_percent'].iloc[-1]
        if pd.notna(latest_change_percent):
            if abs(latest_change_percent) >= 4:
                movement_type = "급등" if latest_change_percent > 0 else "급락"
            elif abs(latest_change_percent) < 1:
                movement_type = "횡보"
            else:
                movement_type = "보합" # Added '보합' for clarity

    # trend (based on 5-day vs 20-day SMA position)
    trend = "정보 부족"
    if len(df) >= 20 and pd.notna(df['sma_5'].iloc[-1]) and pd.notna(df['sma_20'].iloc[-1]):
         if df['sma_5'].iloc[-1] > df['sma_20'].iloc[-1]:
             trend = "상승"
         elif df['sma_5'].iloc[-1] < df['sma_20'].iloc[-1]:
             trend = "하락"
         else:
             trend = "횡보"

    # trend_duration (consecutive days of same direction close movement)
    trend_duration = 0
    if len(df) >= 2:
        last_direction = None
        if df['close'].iloc[-1] > df['close'].iloc[-2]:
            last_direction = 'up'
        elif df['close'].iloc[-1] < df['close'].iloc[-2]:
            last_direction = 'down'
        # If flat, duration is 0 based on this logic.
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

    # volume_trend_duration (consecutive days of same direction volume movement)
    volume_trend_duration = 0
    if len(df) >= 2:
        last_volume_direction = None
        if df['volume'].iloc[-1] > df['volume'].iloc[-2]:
            last_volume_direction = 'up'
        elif df['volume'].iloc[-1] < df['volume'].iloc[-2]:
            last_volume_direction = 'down'
        # If flat, duration is 0 based on this logic.
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


    # trend_count (up/down days in last 20 days)
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


    # 추천 (prediction)
    prediction = "hold" # Default to hold
    if len(df) >= 20: # Need enough data for SMA and recent low check
        # Check for "급등 후 횡보 -> sell"
        if len(df) >= 3:
            movement_type_latest = movement_type # Already calculated
            # Calculate movement_type for the previous day
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

        # Check for "저점 횡보 -> buy" (only if not already decided to sell)
        if prediction == "hold":
            recent_closes_20d = df['close'].iloc[-20:]
            min_price_20d = recent_closes_20d.min()
            latest_price = df['close'].iloc[-1]
            # Check if latest price is near the 20-day low (within 2%) and is currently sideways
            if movement_type_latest == "횡보" and latest_price <= min_price_20d * 1.02:
                 prediction = "buy"


    # reason
    reason = f"최근 추세: {trend} ({trend_duration}일 지속). 금일 변동: {movement_type}. 최근 20일간 상승일: {trend_count['up']}일, 하락일: {trend_count['down']}일."
    # Add specific rule trigger to reason if applicable
    if prediction == "buy":
         reason += " (저점 횡보 패턴 감지)"
    elif prediction == "sell":
         reason += " (급등 후 횡보 패턴 감지)"


    return {
        "prediction": prediction,
        "trend": trend,
        "trend_duration": f"{trend_duration}일", # Format as string with "일"
        "movement_type": movement_type,
        "volume_trend_duration": f"{volume_trend_duration}일", # Added volume trend duration
        "trend_count": trend_count,
        "reason": reason,
        # confidence and movement_duration are not defined how to calculate, omitting for now
    }


def predict_stock_movement(symbol):
    """
    주어진 종목에 대해 분석 항목을 계산하고 예측 결과를 반환합니다.
    """
    # 분석에 필요한 데이터 가져오기 (최소 20일 + 여유분)
    recent_data = get_recent_prices(symbol, days=40) # 넉넉하게 40일 데이터 사용

    # 데이터가 부족하면 예측 불가
    if len(recent_data) < 20:
        return {
            "prediction": "예측 불가",
            "trend": "정보 부족",
            "trend_duration": "N/A",
            "movement_type": "정보 부족",
            "volume_trend_duration": "N/A", # Added volume_trend_duration
            "trend_count": {"up": 0, "down": 0},
            "reason": f"분석에 필요한 데이터({len(recent_data)}일)가 부족합니다 (최소 20일 필요).",
        }

    # 분석 항목 계산
    analysis_result = calculate_analysis_items(recent_data)

    if analysis_result is None:
         return {
            "prediction": "예측 불가",
            "trend": "정보 부족",
            "trend_duration": "N/A",
            "movement_type": "정보 부족",
            "volume_trend_duration": "N/A", # Added volume_trend_duration
            "trend_count": {"up": 0, "down": 0},
            "reason": "데이터 분석 중 오류가 발생했습니다.",
        }

    return analysis_result


if __name__ == "__main__":
    # Example usage
    # Note: This requires some data to be present in the daily_prices table
    # You might need to run data_collector.py first
    example_symbol = "005930"
    prediction_result = predict_stock_movement(example_symbol)
    import json
    print(f"종목: {example_symbol}")
    print("예측 결과 (JSON 구조):")
    print(json.dumps(prediction_result, indent=4, ensure_ascii=False))
