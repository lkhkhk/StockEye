from sqlalchemy.orm import Session
import logging

from src.common.models.disclosure_alert import DisclosureAlert
from src.common.schemas.disclosure_alert import DisclosureAlertCreate, DisclosureAlertUpdate
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class DisclosureAlertService:
    def create_alert(self, db: Session, user_id: int, alert_data: DisclosureAlertCreate) -> DisclosureAlert:
        """
        Creates a new disclosure alert.
        """
        existing_alert = self.get_alert_by_user_and_symbol(db, user_id, alert_data.symbol)
        if existing_alert:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="해당 종목에 대한 공시 알림이 이미 등록되어 있습니다.")

        db_alert = DisclosureAlert(**alert_data.model_dump(), user_id=user_id)
        try:
            db.add(db_alert)
            db.commit()
            db.refresh(db_alert)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create disclosure alert: {e}", exc_info=True)
            raise
        return db_alert

    def get_alerts_by_user(self, db: Session, user_id: int) -> list[DisclosureAlert]:
        """
        Retrieves all disclosure alerts for a specific user.
        """
        return db.query(DisclosureAlert).filter(DisclosureAlert.user_id == user_id).all()

    def get_alert_by_user_and_symbol(self, db: Session, user_id: int, symbol: str) -> DisclosureAlert | None:
        """
        Retrieves a disclosure alert for a specific user and symbol.
        """
        return db.query(DisclosureAlert).filter(DisclosureAlert.user_id == user_id, DisclosureAlert.symbol == symbol).first()

    def get_alert_by_id(self, db: Session, alert_id: int) -> DisclosureAlert | None:
        """
        Retrierives a disclosure alert by its ID.
        """
        return db.query(DisclosureAlert).filter(DisclosureAlert.id == alert_id).first()

    def update_alert(self, db: Session, alert_id: int, alert_data: DisclosureAlertUpdate) -> DisclosureAlert:
        """
        Updates a disclosure alert.
        """
        db_alert = self.get_alert_by_id(db, alert_id)
        if not db_alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disclosure alert not found")
        
        update_data = alert_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_alert, key, value)
        
        try:
            db.add(db_alert)
            db.commit()
            db.refresh(db_alert)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update disclosure alert: {e}", exc_info=True)
            raise
        return db_alert

    def delete_alert(self, db: Session, alert_id: int) -> bool:
        """
        Deletes a disclosure alert.
        """
        db_alert = self.get_alert_by_id(db, alert_id)
        if not db_alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disclosure alert not found")
        
        try:
            db.delete(db_alert)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete disclosure alert: {e}", exc_info=True)
            raise

    def update_alert_status(self, db: Session, alert_id: int, is_active: bool) -> DisclosureAlert:
        """
        Updates the active status of a disclosure alert.
        """
        db_alert = self.get_alert_by_id(db, alert_id)
        if not db_alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disclosure alert not found")
        
        db_alert.is_active = is_active
        try:
            db.add(db_alert)
            db.commit()
            db.refresh(db_alert)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update disclosure alert status: {e}", exc_info=True)
            raise
        return db_alert
