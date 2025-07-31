import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from src.common.db_connector import get_db
from src.api.services.user_service import UserService # user_service 대신 UserService 클래스 임포트
from src.api.services.price_alert_service import PriceAlertService
from src.api.schemas.price_alert import PriceAlertCreate, PriceAlertUpdate, PriceAlertRead
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/bot", tags=["bot_internal"])

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

# 의존성 주입 함수 정의
def get_user_service():
    return UserService()

def get_price_alert_service():
    return PriceAlertService()

class BotAlertRequest(BaseModel):
    telegram_user_id: int
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None
    telegram_last_name: Optional[str] = None
    symbol: str
    target_price: Optional[float] = None
    condition: Optional[str] = None
    notify_on_disclosure: Optional[bool] = None # 토글 로직을 위해 봇에서 상태를 보내지 않도록 변경

@router.post("/alert/disclosure-toggle", response_model=PriceAlertRead)
def toggle_disclosure_alert_for_bot(request: BotAlertRequest = Body(...), db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service), price_alert_service: PriceAlertService = Depends(get_price_alert_service)):
    """(봇 전용) 특정 종목의 공시 알림 상태를 토글합니다."""
    user = user_service.get_user_by_telegram_id(db, request.telegram_user_id)
    if not user:
        # 사용자가 없으면 자동 가입
        user = user_service.create_user_from_telegram(
            db,
            telegram_id=request.telegram_user_id,
            username=request.telegram_username or f"telegram_user_{request.telegram_user_id}",
            first_name=request.telegram_first_name,
            last_name=request.telegram_last_name
        )
    
    existing_alert = price_alert_service.get_alert_by_user_and_symbol(db, user_id=user.id, symbol=request.symbol)

    if existing_alert:
        # 기존 알림이 있으면 상태를 토글
        # db.refresh(existing_alert) # 데이터베이스에서 최신 상태로 새로고침 
        logger.debug(f"Before toggle: existing_alert.notify_on_disclosure = {existing_alert.notify_on_disclosure}") 
        new_status = not existing_alert.notify_on_disclosure
        logger.debug(f"Calculated new_status: {new_status}")       
        update_data = PriceAlertUpdate(notify_on_disclosure=new_status)
        updated_alert_orm = price_alert_service.update_alert(db, alert_id=existing_alert.id, alert_update=update_data)
        logger.debug(f"After update_alert call: updated_alert_orm.notify_on_disclosure = {updated_alert_orm.notify_on_disclosure}")     
        return updated_alert_orm
    else:
        # 기존 알림이 없으면 새로 생성하며 ON으로 설정
        create_data = PriceAlertCreate(
            symbol=request.symbol,
            notify_on_disclosure=True,
            is_active=True # 명시적으로 활성화
        )
        return price_alert_service.create_alert(db, user_id=user.id, alert=create_data)

class BotPriceAlertRequest(BaseModel):
    telegram_user_id: int
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None
    telegram_last_name: Optional[str] = None
    symbol: str
    target_price: float
    condition: str
    repeat_interval: Optional[str] = None

@router.post("/alert/price", response_model=PriceAlertRead)
def set_price_alert_for_bot(request: BotPriceAlertRequest = Body(...), db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service), price_alert_service: PriceAlertService = Depends(get_price_alert_service)):
    """(봇 전용) 특정 종목의 가격 알림을 설정합니다."""
    user = user_service.get_user_by_telegram_id(db, request.telegram_user_id)
    if not user:
        user = user_service.create_user_from_telegram(
            db,
            telegram_id=request.telegram_user_id,
            username=request.telegram_username or f"telegram_user_{request.telegram_user_id}",
            first_name=request.telegram_first_name,
            last_name=request.telegram_last_name
        )
    
    existing_alert = price_alert_service.get_alert_by_user_and_symbol(db, user_id=user.id, symbol=request.symbol)

    if existing_alert:
        # 기존 알림이 있으면 가격 정보만 업데이트
        update_data = PriceAlertUpdate(
            target_price=request.target_price,
            condition=request.condition,
            repeat_interval=request.repeat_interval,
            is_active=True, # 비활성 상태였다면 다시 활성화
            notify_on_disclosure=existing_alert.notify_on_disclosure # 기존 값 유지
        )
        return price_alert_service.update_alert(db, alert_id=existing_alert.id, alert_update=update_data)
    else:
        # 기존 알림이 없으면 새로 생성
        create_data = PriceAlertCreate(
            symbol=request.symbol,
            target_price=request.target_price,
            condition=request.condition,
            repeat_interval=request.repeat_interval
        )
        return price_alert_service.create_alert(db, user_id=user.id, alert=create_data)

class BotAlertIdRequest(BaseModel):
    telegram_user_id: int
    alert_id: int

class BotListAlertsRequest(BaseModel):
    telegram_user_id: int

@router.post("/alert/list", response_model=list[PriceAlertRead])
def list_alerts_for_bot(request: BotListAlertsRequest = Body(...), db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service), price_alert_service: PriceAlertService = Depends(get_price_alert_service)):
    """(봇 전용) 사용자의 모든 알림 목록을 조회합니다."""
    user = user_service.get_user_by_telegram_id(db, request.telegram_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    alerts = price_alert_service.get_alerts(db, user_id=user.id)
    return alerts

@router.post("/alert/remove", response_model=dict)
def remove_alert_for_bot(request: BotAlertIdRequest = Body(...), db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service), price_alert_service: PriceAlertService = Depends(get_price_alert_service)):
    """(봇 전용) 특정 알림을 삭제합니다."""
    user = user_service.get_user_by_telegram_id(db, request.telegram_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    alert = price_alert_service.get_alert_by_id(db, request.alert_id)
    if not alert or alert.user_id != user.id:
        raise HTTPException(status_code=404, detail="Alert not found or not authorized")
    
    price_alert_service.delete_alert(db, request.alert_id)
    return {"message": f"Alert {request.alert_id} removed successfully"}

@router.post("/alert/deactivate", response_model=PriceAlertRead)
def deactivate_alert_for_bot(request: BotAlertIdRequest = Body(...), db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service), price_alert_service: PriceAlertService = Depends(get_price_alert_service)):
    """(봇 전용) 특정 알림을 비활성화합니다."""
    user = user_service.get_user_by_telegram_id(db, request.telegram_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    alert = price_alert_service.get_alert_by_id(db, request.alert_id)
    if not alert or alert.user_id != user.id:
        raise HTTPException(status_code=404, detail="Alert not found or not authorized")
    
    update_data = PriceAlertUpdate(is_active=False)
    updated_alert = price_alert_service.update_alert(db, request.alert_id, update_data)
    return updated_alert 