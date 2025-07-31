import logging
from sqlalchemy.orm import Session
from src.api.models.price_alert import PriceAlert
from src.api.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime
import time # Add this line
from src.api.models.daily_price import DailyPrice # DailyPrice 모델 임포트

logger = logging.getLogger(__name__)

class PriceAlertService:
    def __init__(self):
        logger.debug("PriceAlertService 초기화.")
        pass

    def create_alert(self, db: Session, user_id: int, alert: PriceAlertCreate) -> PriceAlert:
        logger.debug(f"가격 알림 생성 시도: user_id={user_id}, symbol={alert.symbol}, target_price={alert.target_price}, condition={alert.condition}, change_percent={alert.change_percent}, change_type={alert.change_type}, notify_on_disclosure={alert.notify_on_disclosure}, repeat_interval={alert.repeat_interval}")
        
        # 유효성 검사: 최소 하나의 알림 조건은 설정되어야 함
        if not (alert.target_price is not None or alert.change_percent is not None or alert.notify_on_disclosure):
            logger.warning("최소 하나의 알림 조건(목표 가격, 변동률, 공시 알림)은 반드시 설정해야 합니다.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="최소 하나의 알림 조건(목표 가격, 변동률, 공시 알림)은 반드시 설정해야 합니다."
            )
        
        # 변동률 알림 설정 시 change_percent와 change_type이 함께 설정되어야 함
        if alert.change_percent is not None and alert.change_type is None:
            logger.warning("변동률 알림 설정 시 변동 유형(change_type)도 함께 설정해야 합니다.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="변동률 알림 설정 시 변동 유형(change_type)도 함께 설정해야 합니다."
            )
        if alert.change_percent is None and alert.change_type is not None:
            logger.warning("변동 유형(change_type) 설정 시 변동률(change_percent)도 함께 설정해야 합니다.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="변동 유형(change_type) 설정 시 변동률(change_percent)도 함께 설정해야 합니다."
            )

        try:
            new_alert = PriceAlert(
                user_id=user_id,
                symbol=alert.symbol,
                target_price=alert.target_price,
                condition=alert.condition,
                change_percent=alert.change_percent, # 추가
                change_type=alert.change_type,     # 추가
                notify_on_disclosure=alert.notify_on_disclosure,
                repeat_interval=alert.repeat_interval,
                is_active=alert.is_active if alert.is_active is not None else True
            )
            db.add(new_alert)
            db.commit()
            db.refresh(new_alert)
            logger.info(f"가격 알림 생성 성공: alert_id={new_alert.id}, user_id={user_id}, symbol={alert.symbol}")
            return new_alert
        except Exception as e:
            db.rollback()
            logger.error(f"가격 알림 생성 실패: {str(e)}", exc_info=True)
            raise

    def get_alerts(self, db: Session, user_id: int) -> List[PriceAlert]:
        logger.debug(f"사용자({user_id})의 가격 알림 조회 시도.")
        alerts = db.query(PriceAlert).filter(PriceAlert.user_id == user_id).order_by(PriceAlert.created_at.desc()).all()
        logger.debug(f"사용자({user_id})의 가격 알림 {len(alerts)}개 조회됨.")
        return alerts

    def get_alert_by_user_and_symbol(self, db: Session, user_id: int, symbol: str) -> Optional[PriceAlert]:
        logger.debug(f"사용자({user_id})와 종목({symbol})으로 가격 알림 조회 시도.")
        alert = db.query(PriceAlert).filter(
            PriceAlert.user_id == user_id,
            PriceAlert.symbol == symbol
        ).first()
        if alert:
            logger.debug(f"가격 알림 발견: alert_id={alert.id}")
        else:
            logger.debug(f"가격 알림 없음: user_id={user_id}, symbol={symbol}")
        return alert

    def get_alert_by_id(self, db: Session, alert_id: int) -> Optional[PriceAlert]:
        logger.debug(f"ID({alert_id})로 가격 알림 조회 시도.")
        alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
        if alert:
            logger.debug(f"가격 알림 발견: alert_id={alert.id}")
        else:
            logger.debug(f"가격 알림 없음: alert_id={alert_id}")
        return alert

    def get_all_active_alerts(self, db: Session) -> List[PriceAlert]:
        """모든 활성화된 가격 알림을 조회합니다."""
        logger.debug("모든 활성화된 가격 알림 조회 시도.")
        alerts = db.query(PriceAlert).filter(PriceAlert.is_active == True).all()
        logger.debug(f"활성화된 가격 알림 {len(alerts)}개 조회됨.")
        return alerts

    def update_alert(self, db: Session, alert_id: int, alert_update: PriceAlertUpdate) -> PriceAlert:
        logger.debug(f"가격 알림({alert_id}) 수정 시도: update_data={alert_update.model_dump(exclude_unset=True)}")
        alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
        if not alert:
            logger.error(f"Alert not found: {alert_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        try:
            # exclude_unset=True를 사용하여 명시적으로 설정된 값만 가져옵니다.
            update_data = alert_update.model_dump(exclude_unset=True)
            logger.debug(f"Alert before update: notify_on_disclosure={alert.notify_on_disclosure}, is_active={alert.is_active}")
            logger.debug(f"Update data: {update_data}")
            for key, value in update_data.items():
                setattr(alert, key, value)
            logger.debug(f"After setattr: alert.notify_on_disclosure = {alert.notify_on_disclosure}")  
            db.commit()
            db.refresh(alert)
            logger.debug(f"After db.refresh: alert.notify_on_disclosure = {alert.notify_on_disclosure}")  
            logger.info(f"가격 알림({alert_id}) 수정 성공.")
            return alert
        except Exception as e:
            db.rollback()
            logger.error(f"가격 알림({alert_id}) 수정 실패: {str(e)}", exc_info=True)
            raise

    def delete_alert(self, db: Session, alert_id: int):
        logger.debug(f"가격 알림({alert_id}) 삭제 시도.")
        alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
        if not alert:
            logger.error(f"Alert not found: {alert_id}")
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

    def check_alerts(self, db: Session, symbol: str, current_price: float):
        logger.debug(f"종목({symbol})의 가격 알림 확인 시도. 현재가: {current_price}")
        alerts = db.query(PriceAlert).filter(
            PriceAlert.symbol == symbol,
            PriceAlert.is_active == True
        ).all()
        triggered = []
        for alert in alerts:
            # 목표 가격 조건 확인
            if alert.target_price is not None and alert.condition:
                logger.debug(f"알림({alert.id}) 목표 가격 조건 확인: 목표={alert.target_price}, 조건={alert.condition}")
                if alert.condition == 'gte' and current_price >= alert.target_price:
                    triggered.append(alert)
                    logger.debug(f"알림({alert.id}) 트리거됨 (gte).")
                elif alert.condition == 'lte' and current_price <= alert.target_price:
                    triggered.append(alert)
                    logger.debug(f"알림({alert.id}) 트리거됨 (lte).")
            
            # 변동률 조건 확인
            if alert.change_percent is not None and alert.change_type:
                logger.debug(f"알림({alert.id}) 변동률 조건 확인: 변동률={alert.change_percent}%, 유형={alert.change_type}")
                # 이전 종가 가져오기 (최근 2일치 데이터 필요)
                recent_prices = db.query(DailyPrice).filter(
                    DailyPrice.symbol == symbol
                ).order_by(DailyPrice.date.desc()).limit(2).all()

                if len(recent_prices) >= 2:
                    yesterday_close = recent_prices[1].close # 어제 종가
                    today_close = recent_prices[0].close     # 오늘 종가 (current_price와 동일)
                    
                    if yesterday_close == 0: # 0으로 나누는 오류 방지
                        logger.warning(f"종목 {symbol}의 어제 종가가 0이어서 변동률 계산 불가.")
                        continue

                    actual_change_percent = ((today_close - yesterday_close) / yesterday_close) * 100
                    logger.debug(f"실제 변동률: {actual_change_percent:.2f}%")

                    if alert.change_type == 'up' and actual_change_percent >= alert.change_percent:
                        triggered.append(alert)
                        logger.debug(f"알림({alert.id}) 트리거됨 (변동률 상승).")
                    elif alert.change_type == 'down' and actual_change_percent <= -alert.change_percent: # 하락은 음수 변동률
                        triggered.append(alert)
                        logger.debug(f"알림({alert.id}) 트리거됨 (변동률 하락).")
                else:
                    logger.warning(f"종목 {symbol}의 변동률 알림을 위한 충분한 데이터(최근 2일치) 부족.")

        logger.debug(f"종목({symbol})에 대해 {len(triggered)}개의 알림 트리거됨.")
        return triggered