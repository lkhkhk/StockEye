from sqlalchemy.orm import Session, joinedload
import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from fastapi import HTTPException, status
from typing import List

from src.common.models.price_alert import PriceAlert
from src.common.models.stock_master import StockMaster
from src.common.models.user import User
from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
from src.common.models.daily_price import DailyPrice
from src.common.services.notify_service import send_telegram_message
from src.common.services.market_data_service import MarketDataService # Import here

logger = logging.getLogger(__name__)

class PriceAlertService:
    def __init__(self):
        self.market_data_service = MarketDataService() # Initialize here

    async def create_alert(self, db: Session, user_id: int, alert_data: PriceAlertCreate) -> PriceAlert:
        if alert_data.change_percent is not None and alert_data.change_type is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="변동률 알림 설정 시 변동 유형(change_type)도 함께 설정해야 합니다.")
        if alert_data.change_type is not None and alert_data.change_percent is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="변동 유형(change_type) 설정 시 변동률(change_percent)도 함께 설정해야 합니다.")
        if alert_data.target_price is None and alert_data.change_percent is None and not alert_data.notify_on_disclosure:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="최소 하나의 알림 조건(목표 가격, 변동률, 공시 알림)은 반드시 설정해야 합니다.")

        db_alert = PriceAlert(**alert_data.model_dump(), user_id=user_id)
        try:
            db.add(db_alert)
            db.commit()
            db.refresh(db_alert)
        except Exception as e:
            db.rollback()
            raise e
        return db_alert

    def get_alerts(self, db: Session, user_id: int):
        return db.query(PriceAlert).options(joinedload(PriceAlert.stock)).filter(PriceAlert.user_id == user_id).all()

    def get_exact_duplicate_alert(self, db: Session, user_id: int, symbol: str, target_price: float, condition: str):
        return db.query(PriceAlert).filter(
            PriceAlert.user_id == user_id,
            PriceAlert.symbol == symbol,
            PriceAlert.target_price == target_price,
            PriceAlert.condition == condition
        ).first()

    def get_alert_by_id(self, db: Session, alert_id: int):
        return db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()

    def get_alert_by_user_symbol_and_condition(self, db: Session, user_id: int, symbol: str, condition: str):
        return db.query(PriceAlert).filter(
            PriceAlert.user_id == user_id,
            PriceAlert.symbol == symbol,
            PriceAlert.condition == condition
        ).first()

    def get_alert_by_user_and_symbol(self, db: Session, user_id: int, symbol: str):
        """사용자 ID와 심볼로 알림 조회 (condition 무관)"""
        return db.query(PriceAlert).filter(
            PriceAlert.user_id == user_id,
            PriceAlert.symbol == symbol
        ).first()


    def get_all_active_alerts(self, db: Session):
        return db.query(PriceAlert).options(
            joinedload(PriceAlert.user),
            joinedload(PriceAlert.stock)
        ).filter(PriceAlert.is_active == True).all()

    async def update_alert(self, db: Session, alert_id: int, alert_data: PriceAlertUpdate):
        db_alert = self.get_alert_by_id(db, alert_id)
        if not db_alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        
        update_data = alert_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_alert, key, value)
        
        try:
            db.add(db_alert)
            db.commit()
            db.refresh(db_alert)
        except Exception as e:
            db.rollback()
            raise e
        return db_alert

    async def delete_alert(self, db: Session, alert_id: int) -> bool:
        db_alert = self.get_alert_by_id(db, alert_id)
        if not db_alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        
        try:
            db.delete(db_alert)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e

    async def update_alert_status(self, db: Session, alert_id: int, is_active: bool) -> PriceAlert:
        db_alert = self.get_alert_by_id(db, alert_id)
        if not db_alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        
        db_alert.is_active = is_active
        try:
            db.add(db_alert)
            db.commit()
            db.refresh(db_alert)
        except Exception as e:
            db.rollback()
            raise e
        return db_alert

    def _get_latest_prices(self, db: Session, symbols: List[str]):
        """
        심볼 목록에 대한 최신 가격을 조회합니다.
        PostgreSQL의 경우 DISTINCT ON을 사용하여 효율적으로 조회하고,
        SQLite(테스트 환경)의 경우 Python 레벨에서 필터링합니다.
        """
        if db.bind.dialect.name == 'postgresql':
            return db.query(DailyPrice).filter(
                DailyPrice.symbol.in_(symbols)
            ).distinct(DailyPrice.symbol).order_by(
                DailyPrice.symbol, DailyPrice.date.desc()
            ).all()
        else:
            # SQLite fallback
            prices = db.query(DailyPrice).filter(
                DailyPrice.symbol.in_(symbols)
            ).order_by(DailyPrice.date.desc()).all()
            
            latest = {}
            for p in prices:
                if p.symbol not in latest:
                    latest[p.symbol] = p
            return list(latest.values())

    async def check_and_notify_price_alerts(self, db: Session):
        try:
            alerts = self.get_all_active_alerts(db)
            if not alerts:
                return

            # 1. 알림 대상 심볼 수집
            symbols = list(set(alert.symbol for alert in alerts))
            
            # 2. 최신 가격 일괄 조회 (N+1 문제 해결)
            latest_prices = self._get_latest_prices(db, symbols)
            
            # 심볼별 가격 매핑
            price_map = {p.symbol: p for p in latest_prices}

            for alert in alerts:
                # Check notification interval
                if alert.last_notified_at and alert.notification_interval_hours:
                    next_notify_time = alert.last_notified_at + timedelta(hours=alert.notification_interval_hours)
                    if datetime.utcnow() < next_notify_time:
                        logger.info(f"알림 ID {alert.id}는 최근에 전송되었으므로 건너뜁니다.")
                        continue

                # Get current price from map
                daily_price = price_map.get(alert.symbol)
                
                if not daily_price:
                    continue

                current_price = daily_price.close
                triggered = False
                message = ""

                # Stock name is already loaded via joinedload
                stock_name = alert.stock.name if alert.stock else "Unknown"

                # Check target price
                if alert.target_price:
                    if (alert.condition == 'gte' or alert.condition == 'above') and current_price >= alert.target_price:
                        triggered = True
                        message = f"[{alert.symbol}] {stock_name}\n목표가 도달: {alert.target_price}원 이상으로 상승\n현재가: {current_price}원"
                    elif (alert.condition == 'lte' or alert.condition == 'below') and current_price <= alert.target_price:
                        triggered = True
                        message = f"[{alert.symbol}] {stock_name}\n목표가 도달: {alert.target_price}원 이하로 하락\n현재가: {current_price}원"

                # Check change percent
                if not triggered and alert.change_percent:
                    # 변동률 계산을 위한 전일 종가 조회 (여전히 N+1 발생 가능성 있음, 하지만 빈도는 낮음)
                    # 최적화를 위해 이 부분도 개선 가능하지만, 일단 현재 가격 체크가 우선임.
                    # 변동률 체크는 복잡도가 높으므로 일단 기존 로직 유지하되, 필요한 경우에만 쿼리 실행.
                    
                    # TODO: 변동률 체크도 Bulk 조회로 개선 필요
                    prev_price_obj = db.query(DailyPrice).filter(
                        DailyPrice.symbol == alert.symbol,
                        DailyPrice.date < daily_price.date
                    ).order_by(DailyPrice.date.desc()).first()

                    if prev_price_obj:
                        prev_close = prev_price_obj.close
                        change_rate = ((current_price - prev_close) / prev_close) * 100
                        
                        if alert.change_type == 'up' and change_rate >= alert.change_percent:
                            triggered = True
                            message = f"[{alert.symbol}] {stock_name}\n변동률 도달: {alert.change_percent}% up\n현재 변동률: {change_rate:.2f}%\n현재가: {current_price}원"
                        elif alert.change_type == 'down' and change_rate <= alert.change_percent:
                            triggered = True
                            message = f"[{alert.symbol}] {stock_name}\n변동률 도달: {alert.change_percent}% down\n현재 변동률: {change_rate:.2f}%\n현재가: {current_price}원"

                if triggered:
                    # Send notification
                    # User is already loaded via joinedload
                    if alert.user.telegram_id:
                        await send_telegram_message(alert.user.telegram_id, message)
                        
                        alert.last_notified_at = datetime.utcnow()
                        alert.notification_count += 1
                        db.commit()
        except Exception as e:
            logger.error(f"Error checking and notifying price alerts: {e}", exc_info=True)

