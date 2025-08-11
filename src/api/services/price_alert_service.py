import logging
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from src.api.models.price_alert import PriceAlert
from src.api.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime
import time
from src.api.models.daily_price import DailyPrice
import redis.asyncio as redis
import os
import json

REDIS_HOST = os.getenv("REDIS_HOST", "stockeye-redis")

logger = logging.getLogger(__name__)

class PriceAlertService:
    def __init__(self):
        logger.debug("PriceAlertService 초기화.")
        pass

    async def create_alert(self, db: Session, user_id: int, alert: PriceAlertCreate) -> PriceAlert:
        logger.debug(f"가격 알림 생성 시도: user_id={user_id}, symbol={alert.symbol}")
        
        if alert.change_percent is not None and alert.change_type is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="변동률 알림 설정 시 변동 유형(change_type)도 함께 설정해야 합니다.")
        if alert.change_percent is None and alert.change_type is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="변동 유형(change_type) 설정 시 변동률(change_percent)도 함께 설정해야 합니다.")
        if not (alert.target_price is not None or alert.change_percent is not None or alert.notify_on_disclosure):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="최소 하나의 알림 조건(목표 가격, 변동률, 공시 알림)은 반드시 설정해야 합니다.")

        try:
            new_alert = PriceAlert(
                user_id=user_id,
                symbol=alert.symbol,
                target_price=alert.target_price,
                condition=alert.condition,
                change_percent=alert.change_percent,
                change_type=alert.change_type,
                notify_on_disclosure=alert.notify_on_disclosure,
                repeat_interval=alert.repeat_interval,
                is_active=alert.is_active if alert.is_active is not None else True
            )
            db.add(new_alert)
            db.commit()
            db.refresh(new_alert)
            logger.info(f"가격 알림 생성 성공: alert_id={new_alert.id}")
            return new_alert
        except Exception as e:
            db.rollback()
            logger.error(f"가격 알림 생성 실패: {str(e)}", exc_info=True)
            raise

    def get_alerts(self, db: Session, user_id: int) -> List[PriceAlert]:
        return db.query(PriceAlert).filter(PriceAlert.user_id == user_id).order_by(PriceAlert.created_at.desc()).all()

    def get_alert_by_user_and_symbol(self, db: Session, user_id: int, symbol: str) -> Optional[PriceAlert]:
        return db.query(PriceAlert).filter(PriceAlert.user_id == user_id, PriceAlert.symbol == symbol).first()

    def get_alert_by_id(self, db: Session, alert_id: int) -> Optional[PriceAlert]:
        return db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()

    def get_all_active_alerts(self, db: Session) -> List[PriceAlert]:
        """모든 활성화된 가격 알림을 조회합니다."""
        logger.debug("모든 활성화된 가격 알림 조회 시도.")
        alerts = db.query(PriceAlert).options(joinedload(PriceAlert.user)).filter(PriceAlert.is_active == True).all()
        logger.debug(f"활성화된 가격 알림 {len(alerts)}개 조회됨.")
        return alerts

    async def update_alert(self, db: Session, alert_id: int, alert_update: PriceAlertUpdate) -> PriceAlert:
        alert = self.get_alert_by_id(db, alert_id)
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        try:
            update_data = alert_update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(alert, key, value)
            db.commit()
            db.refresh(alert)
            logger.info(f"가격 알림({alert.id}) 수정 성공.")
            return alert
        except Exception as e:
            db.rollback()
            logger.error(f"가격 알림({alert_id}) 수정 실패: {str(e)}", exc_info=True)
            raise

    async def delete_alert(self, db: Session, alert_id: int):
        alert = self.get_alert_by_id(db, alert_id)
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        try:
            db.delete(alert)
            db.commit()
            logger.info(f"가격 알림({alert_id}) 삭제 성공.")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"가격 알림({alert_id}) 삭제 실패: {str(e)}", exc_info=True)
            raise

    async def check_and_notify_price_alerts(self, db: Session):
        """모든 활성 가격 알림을 확인하고, 조건 충족 시 Redis에 알림을 발행합니다."""
        logger.info("활성 가격 알림 확인 및 알림 작업 시작")
        active_alerts = self.get_all_active_alerts(db)
        if not active_alerts:
            logger.info("활성 가격 알림이 없어 작업을 조기 종료합니다.")
            return

        symbols_to_check = {alert.symbol for alert in active_alerts}
        latest_prices = db.query(DailyPrice).filter(DailyPrice.symbol.in_(symbols_to_check)).order_by(DailyPrice.date.desc()).all()
        
        latest_price_map = {price.symbol: price.close for price in latest_prices}

        redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
        
        for alert in active_alerts:
            current_price = latest_price_map.get(alert.symbol)
            if current_price is None:
                continue

            triggered = False
            message = ""

            if alert.target_price is not None and alert.condition:
                if (alert.condition == 'gte' and current_price >= alert.target_price) or \
                   (alert.condition == 'lte' and current_price <= alert.target_price):
                    triggered = True
                    message = f"목표 가격 도달: {alert.symbol} {alert.target_price} {alert.condition} (현재가: {current_price})"

            if triggered:
                logger.info(f"알림({alert.id}) 트리거됨. Redis에 메시지 발행.")
                message_data = {
                    "chat_id": str(alert.user.telegram_id),
                    "text": message
                }
                await redis_client.publish("notifications", json.dumps(message_data, ensure_ascii=False))
                
                if not alert.repeat_interval:
                    alert.is_active = False
                    db.add(alert)

        await redis_client.close()
        db.commit() 
        logger.info("활성 가격 알림 확인 및 알림 작업 완료")
