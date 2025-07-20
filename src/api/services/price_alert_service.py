import logging
from sqlalchemy.orm import Session
from src.api.models.price_alert import PriceAlert
from src.api.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
from fastapi import HTTPException, status
from typing import List
from datetime import datetime

logger = logging.getLogger(__name__)

class PriceAlertService:
    def __init__(self):
        pass

    def create_alert(self, db: Session, user_id: int, alert: PriceAlertCreate) -> PriceAlert:
        try:
            new_alert = PriceAlert(
                user_id=user_id,
                symbol=alert.symbol,
                target_price=alert.target_price,
                condition=alert.condition,
                is_active=True
            )
            db.add(new_alert)
            db.commit()
            db.refresh(new_alert)
            return new_alert
        except Exception as e:
            db.rollback()
            logger.error(f"가격 알림 생성 실패: {str(e)}", exc_info=True)
            raise

    def get_alerts(self, db: Session, user_id: int) -> List[PriceAlert]:
        return db.query(PriceAlert).filter(PriceAlert.user_id == user_id).order_by(PriceAlert.created_at.desc()).all()

    def update_alert(self, db: Session, alert_id: int, alert_update: PriceAlertUpdate) -> PriceAlert:
        alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
        if not alert:
            logger.error(f"Alert not found: {alert_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        try:
            if alert_update.target_price is not None:
                alert.target_price = alert_update.target_price
            if alert_update.condition is not None:
                alert.condition = alert_update.condition
            if alert_update.is_active is not None:
                alert.is_active = alert_update.is_active
            alert.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(alert)
            return alert
        except Exception as e:
            db.rollback()
            logger.error(f"가격 알림 수정 실패: {str(e)}", exc_info=True)
            raise

    def delete_alert(self, db: Session, alert_id: int):
        alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
        if not alert:
            logger.error(f"Alert not found: {alert_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        try:
            db.delete(alert)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"가격 알림 삭제 실패: {str(e)}", exc_info=True)
            raise

    def check_alerts(self, db: Session, symbol: str, current_price: float):
        """특정 종목의 가격이 알림 조건을 만족하는지 확인하고, 만족 시 알림 반환"""
        alerts = db.query(PriceAlert).filter(
            PriceAlert.symbol == symbol,
            PriceAlert.is_active == True
        ).all()
        triggered = []
        for alert in alerts:
            if alert.condition == 'gte' and current_price >= alert.target_price:
                triggered.append(alert)
            elif alert.condition == 'lte' and current_price <= alert.target_price:
                triggered.append(alert)
        return triggered 