from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from fastapi import HTTPException, status

from src.common.models.price_alert import PriceAlert
from src.common.models.stock_master import StockMaster
from src.common.models.user import User
from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
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
        return db.query(PriceAlert).filter(PriceAlert.user_id == user_id).all()

    def get_alert_by_user_and_symbol(self, db: Session, user_id: int, symbol: str):
        return db.query(PriceAlert).filter(PriceAlert.user_id == user_id, PriceAlert.symbol == symbol).first()

    def get_alert_by_id(self, db: Session, alert_id: int):
        return db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()

    def get_all_active_alerts(self, db: Session):
        return db.query(PriceAlert).filter(PriceAlert.is_active == True).all()

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

    async def delete_alert(self, db: Session, alert_id: int):
        db_alert = self.get_alert_by_id(db, alert_id)
        if not db_alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        
        try:
            db.delete(db_alert)
            db.commit()
        except Exception as e:
            db.rollback()
            raise e

    async def check_and_notify_price_alerts(self, db: Session):
        """
        활성화된 가격 알림을 확인하고, 조건 충족 시 사용자에게 알림을 보냅니다.
        """
        logger.debug("check_and_notify_price_alerts 함수 시작.")
        try:
            alerts = self.get_all_active_alerts(db)
        except Exception as e:
            logger.error(f"Error checking and notifying price alerts: {e}", exc_info=True)
            return
        
        for alert in alerts:
            # 1. 알림 주기 확인을 먼저 수행
            if alert.last_notified_at and (datetime.now() - alert.last_notified_at) < timedelta(hours=alert.notification_interval_hours):
                logger.info(f"알림 ID {alert.id}는 최근에 전송되었으므로 건너뜁니다. 다음 알림 가능 시간: {alert.last_notified_at + timedelta(hours=alert.notification_interval_hours)}")
                continue

            stock_info = db.query(StockMaster).filter(StockMaster.symbol == alert.symbol).first()
            if not stock_info:
                logger.warning(f"알림 종목 {alert.symbol}에 대한 종목 마스터 정보가 없습니다. 알림 ID: {alert.id}")
                continue

            current_price_data = self.market_data_service.get_current_price_and_change(alert.symbol, db)
            current_price = current_price_data.get("current_price")

            if current_price is None:
                logger.warning(f"종목 {alert.symbol}의 현재 가격 정보를 가져올 수 없습니다. 알림 ID: {alert.id}")
                continue

            should_notify = False
            message = ""

            if alert.condition == "above" and current_price >= alert.target_price:
                should_notify = True
                message = f"📈 {stock_info.name} ({alert.symbol}) 가격이 {alert.target_price}원 이상으로 상승했습니다. 현재가: {current_price}원"
            elif alert.condition == "below" and current_price <= alert.target_price:
                should_notify = True
                message = f"📉 {stock_info.name} ({alert.symbol}) 가격이 {alert.target_price}원 이하로 하락했습니다. 현재가: {current_price}원"
            elif alert.change_percent is not None and current_price_data.get("change_rate") is not None:
                current_change_rate = current_price_data["change_rate"]
                if alert.change_type == "up" and current_change_rate >= alert.change_percent:
                    should_notify = True
                    message = f"📈 {stock_info.name} ({alert.symbol}) 변동률 도달: {alert.change_percent}% up (현재 변동률: {current_change_rate:.2f}%)"
                elif alert.change_type == "down" and current_change_rate <= alert.change_percent:
                    should_notify = True
                    message = f"📉 {stock_info.name} ({alert.symbol}) 변동률 도달: {alert.change_percent}% down (현재 변동률: {current_change_rate:.2f}%)"
            
            if should_notify:
                user = db.query(User).filter(User.id == alert.user_id).first()
                if user and user.telegram_id:
                    try:
                        await send_telegram_message(user.telegram_id, message)
                        alert.last_notified_at = datetime.now()
                        alert.notification_count += 1
                        db.add(alert)
                        db.commit()
                        logger.info(f"가격 알림 전송 성공: 알림 ID {alert.id}, 사용자 {user.id}")
                    except Exception as e:
                        db.rollback()
                        logger.error(f"가격 알림 전송 실패: 알림 ID {alert.id}, 사용자 {user.id}, 오류: {e}", exc_info=True)
                else:
                    logger.warning(f"알림 ID {alert.id}에 대한 사용자 또는 텔레그램 ID를 찾을 수 없습니다.")