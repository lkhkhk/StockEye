from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.api.db import get_db
from src.api.schemas.price_alert import PriceAlertCreate, PriceAlertRead, PriceAlertUpdate
from src.api.services.price_alert_service import PriceAlertService
from src.api.auth.jwt_handler import get_current_user
from typing import List
from src.api.models.price_alert import PriceAlert

router = APIRouter(prefix="/alerts", tags=["notification"])
alert_service = PriceAlertService()

@router.post("/", response_model=PriceAlertRead)
def create_alert(alert: PriceAlertCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """가격 알림 생성"""
    result = alert_service.create_alert(db, user_id=current_user["user_id"], alert=alert)
    return PriceAlertRead.model_validate(result)

@router.get("/", response_model=List[PriceAlertRead])
def get_my_alerts(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """내 가격 알림 목록 조회"""
    results = alert_service.get_alerts(db, user_id=current_user["user_id"])
    return [PriceAlertRead.model_validate(r) for r in results]

@router.put("/{alert_id}", response_model=PriceAlertRead)
def update_alert(alert_id: int, alert_update: PriceAlertUpdate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """가격 알림 수정"""
    alert = alert_service.update_alert(db, alert_id, alert_update)
    if alert.user_id != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한 없음")
    return PriceAlertRead.model_validate(alert)

@router.delete("/{alert_id}")
def delete_alert(alert_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """가격 알림 삭제"""
    alert = db.query(PriceAlert).filter_by(id=alert_id).first()
    if alert and alert.user_id != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한 없음")
    alert_service.delete_alert(db, alert_id)
    return {"result": True} 