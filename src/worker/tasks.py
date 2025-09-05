import logging
import json
import redis
import os
from datetime import datetime
import asyncio
import yfinance as yf
from datetime import timedelta

from src.common.database.db_connector import get_db
from src.common.services.stock_master_service import StockMasterService
from src.common.services.market_data_service import MarketDataService
from src.common.services.disclosure_service import DisclosureService
from src.common.services.price_alert_service import PriceAlertService
from src.common.models.user import User
from src.common.models.stock_master import StockMaster
from src.common.models.daily_price import DailyPrice


# 로깅 설정
logger = logging.getLogger(__name__)

# 환경 변수
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

def _publish_message(redis_client, chat_id, text):
    """메시지를 Redis에 게시합니다."""
    if not chat_id:
        return
    try:
        redis_client.publish("notifications", json.dumps({"chat_id": chat_id, "text": text}, ensure_ascii=False))
        logger.info(f"Published message to chat_id: {chat_id}")
    except Exception as e:
        logger.error(f"Failed to publish message: {e}", exc_info=True)

def _publish_completion_message(redis_client, chat_id, job_name, success, start_time, details=""):
    """작업 완료 메시지를 Redis에 게시합니다."""
    if not chat_id:
        return
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if success:
        status_icon = "✅"
        status_text = "성공"
    else:
        status_icon = "❌"
        status_text = "실패"
        
    message = (
        f"{status_icon} **{job_name}** 작업 완료\n"
        f"• **결과:** {status_text}\n"
        f"• **소요 시간:** {duration:.2f}초"
    )
    if details:
        message += f"\n{details}"

    _publish_message(redis_client, chat_id, message)


def update_stock_master_task(chat_id: int = None):
    """[Process] 종목마스터 정보 갱신 작업"""
    job_name = "종목마스터 갱신"
    start_time = datetime.now()
    logger.info(f"[Process] {job_name} 시작.")
    
    db_gen = get_db()
    db = next(db_gen)
    redis_client = redis.from_url(f"redis://{REDIS_HOST}")
    stock_master_service = StockMasterService()
    success = False
    
    try:
        asyncio.run(stock_master_service.update_stock_master(db))
        success = True
        logger.info(f"[Process] {job_name} 성공.")
    except Exception as e:
        logger.error(f"[Process] {job_name} 중 오류: {e}", exc_info=True)
    finally:
        try:
            next(db_gen, None)
        except StopIteration:
            pass
        _publish_completion_message(redis_client, chat_id, job_name, success, start_time)
        redis_client.close()
        logger.info(f"[Process] {job_name} 종료.")


def update_daily_price_task(chat_id: int = None):
    """[Process] 일별시세 갱신 작업"""
    job_name = "일별시세 갱신"
    start_time = datetime.now()
    logger.info(f"[Process] {job_name} 시작.")
    
    db_gen = get_db()
    db = next(db_gen)
    redis_client = redis.from_url(f"redis://{REDIS_HOST}")
    market_data_service = MarketDataService()
    success = False
    
    try:
        asyncio.run(market_data_service.update_daily_prices(db))
        success = True
        logger.info(f"[Process] {job_name} 성공.")
    except Exception as e:
        logger.error(f"[Process] {job_name} 중 오류: {e}", exc_info=True)
    finally:
        try:
            next(db_gen, None)
        except StopIteration:
            pass
        _publish_completion_message(redis_client, chat_id, job_name, success, start_time)
        redis_client.close()
        logger.info(f"[Process] {job_name} 종료.")

def check_disclosures_task(chat_id: int = None):
    """[Process] 최신 공시 확인 및 알림 작업"""
    job_name = "최신 공시 확인"
    start_time = datetime.now()
    logger.info(f"[Process] {job_name} 시작.")
    
    db_gen = get_db()
    db = next(db_gen)
    redis_client = redis.from_url(f"redis://{REDIS_HOST}")
    disclosure_service = DisclosureService()
    success = False
    
    try:
        asyncio.run(disclosure_service.check_and_notify_new_disclosures(db))
        success = True
        logger.info(f"[Process] {job_name} 성공.")
    except Exception as e:
        logger.error(f"[Process] {job_name} 중 오류: {e}", exc_info=True)
    finally:
        try:
            next(db_gen, None)
        except StopIteration:
            pass
        _publish_completion_message(redis_client, chat_id, job_name, success, start_time)
        redis_client.close()
        logger.info(f"[Process] {job_name} 종료.")

def check_price_alerts_task(chat_id: int = None):
    """[Process] 가격 알림 조건 확인 및 알림 작업"""
    job_name = "가격 알림 확인"
    start_time = datetime.now()
    logger.info(f"[Process] {job_name} 시작.")
    
    db_gen = get_db()
    db = next(db_gen)
    redis_client = redis.from_url(f"redis://{REDIS_HOST}")
    alert_service = PriceAlertService()
    market_data_service = MarketDataService()
    success = False
    
    try:
        active_alerts = alert_service.get_all_active_alerts(db)
        alerts_by_symbol = {}
        for alert in active_alerts:
            if alert.symbol not in alerts_by_symbol:
                alerts_by_symbol[alert.symbol] = []
            alerts_by_symbol[alert.symbol].append(alert)

        for symbol, alerts in alerts_by_symbol.items():
            try:
                price_data = market_data_service.get_current_price_and_change(symbol, db)
                current_price = price_data.get("current_price")
                if current_price is None:
                    continue

                for alert in alerts:
                    triggered = False
                    if alert.condition == 'gte' and current_price >= alert.target_price:
                        triggered = True
                    elif alert.condition == 'lte' and current_price <= alert.target_price:
                        triggered = True
                    
                    if triggered:
                        user = db.query(User).filter(User.id == alert.user_id).first()
                        if user and user.telegram_id:
                            msg = f"🔔 가격 알림: {alert.symbol}\n현재가 {current_price}원이 목표가 {alert.target_price}({alert.condition})에 도달했습니다."
                            _publish_message(redis_client, user.telegram_id, msg)
                        
                        if alert.repeat_interval is None:
                            alert.is_active = False
                            db.add(alert)
                db.commit()
            except Exception as e:
                logger.error(f"가격 알림 확인 중 '{symbol}' 처리 오류: {e}", exc_info=True)
                db.rollback()
                continue
        db.commit()
        success = True
    except Exception as e:
        logger.error(f"[Process] {job_name} 중 상위 레벨 오류: {e}", exc_info=True)
        db.rollback()
    finally:
        try:
            next(db_gen, None)
        except StopIteration:
            pass
        _publish_completion_message(redis_client, chat_id, job_name, success, start_time)
        redis_client.close()
        logger.info(f"[Process] {job_name} 종료.")


def run_historical_price_update_task(chat_id: int, start_date_str: str, end_date_str: str):
    """[Process] 과거 일별 시세 갱신 작업"""
    job_name = "과거 일별 시세 갱신"
    start_time = datetime.now()
    logger.info(f"[Process] {job_name} 시작: {start_date_str} ~ {end_date_str}")
    
    db_gen = get_db()
    db = next(db_gen)
    redis_client = redis.from_url(f"redis://{REDIS_HOST}")
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    total_updated_count = 0
    total_created_count = 0
    total_error_stocks = []
    processed_stocks = 0
    success = False
    
    try:
        stocks = db.query(StockMaster).all()
        total_stocks = len(stocks)

        if total_stocks == 0:
            _publish_message(redis_client, chat_id, "❌ 처리할 주식 데이터가 없습니다. 먼저 종목 마스터를 업데이트해주세요.")
            return

        for i, stock in enumerate(stocks):
            processed_stocks += 1
            logger.debug(f"종목 {stock.symbol} ({stock.name}) 과거 시세 갱신 시작.")
            try:
                ticker = f"{stock.symbol}.KS"
                data = yf.download(ticker, start=start_date, end=end_date + timedelta(days=1))
                
                if data.empty:
                    logger.warning(f"종목 {stock.symbol} ({ticker})에 대한 과거 시세 데이터가 없습니다.")
                    total_error_stocks.append(stock.symbol)
                    continue

                for index, row in data.iterrows():
                    target_date = index.date()
                    
                    if not (start_date.date() <= target_date <= end_date.date()):
                        continue

                    existing_price = db.query(DailyPrice).filter(DailyPrice.symbol == stock.symbol, DailyPrice.date == target_date).first()
                    
                    if existing_price:
                        existing_price.open = float(row['Open'])
                        existing_price.high = float(row['High'])
                        existing_price.low = float(row['Low'])
                        existing_price.close = float(row['Close'])
                        existing_price.volume = int(row['Volume'])
                        total_updated_count += 1
                    else:
                        new_price = DailyPrice(
                            symbol=stock.symbol,
                            date=target_date,
                            open=float(row['Open']),
                            high=float(row['High']),
                            low=float(row['Low']),
                            close=float(row['Close']),
                            volume=int(row['Volume'])
                        )
                        db.add(new_price)
                        total_created_count += 1
                
                if (i + 1) % 100 == 0:
                    db.commit()
                    logger.info(f"{i+1}개 종목 처리 후 중간 커밋")

            except Exception as e:
                logger.error(f"과거 시세 갱신 중 '{stock.symbol}' 처리에서 오류 발생: {e}")
                total_error_stocks.append(stock.symbol)
                db.rollback()

            if processed_stocks % 50 == 0:
                progress_msg = f"⏳ {job_name} 진행 중... ({processed_stocks}/{total_stocks}개 종목 처리 완료)"
                _publish_message(redis_client, chat_id, progress_msg)

        db.commit()
        success = True
    except Exception as e:
        logger.error(f"[Process] {job_name} 중 오류: {e}", exc_info=True)
        db.rollback()
    finally:
        details = ""
        if success:
            details = (
                f"- **신규:** {total_created_count}개\n"
                f"- **갱신:** {total_updated_count}개\n"
                f"- **오류 종목 수:** {len(total_error_stocks)}개"
            )
        
        try:
            next(db_gen, None)
        except StopIteration:
            pass
        _publish_completion_message(redis_client, chat_id, job_name, success, start_time, details)
        redis_client.close()
        logger.info(f"[Process] {job_name} 종료.")