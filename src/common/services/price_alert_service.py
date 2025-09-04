from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from fastapi import HTTPException, status

from src.common.models.price_alert import PriceAlert
from src.common.models.stock_master import StockMaster
from src.common.models.user import User
from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
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
        if alert_data.target_price is None and alert_data.change_percent is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="최소 하나의 알림 조건(목표 가격, 변동률)은 반드시 설정해야 합니다.")

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
