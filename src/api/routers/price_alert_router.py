from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from src.common.database import db_connector
from src.common.models.user import User
from src.common.schemas.price_alert import PriceAlertCreate, PriceAlertRead, PriceAlertUpdate
from src.api.auth.jwt_handler import get_current_active_user
from src.common.services.price_alert_service import PriceAlertService

logger = logging.getLogger(__name__)

router = APIRouter()

def get_price_alert_service():
    return PriceAlertService()

@router.post("/price-alerts/", response_model=PriceAlertRead, status_code=201,
             summary="새 가격 알림 생성",
             description="사용자를 위한 새로운 가격 알림을 생성합니다. 사용자는 특정 종목(symbol)에 대한 목표 가격(target_price)과 조건(condition)을 설정할 수 있습니다.",
             response_description="성공적으로 생성된 가격 알림의 상세 정보.")
async def create_price_alert(
    alert: PriceAlertCreate,
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    price_alert_service: PriceAlertService = Depends(get_price_alert_service)
):
    print(f"[API] create_price_alert called! current_user.id={current_user.id}, alert={alert.model_dump()}")
    logger.debug(f"create_price_alert: current_user={current_user.id}, alert={alert.model_dump()}")

    # Check for an existing alert with the same user, symbol, and condition
    existing_alert = price_alert_service.get_alert_by_user_symbol_and_condition(
        db, current_user.id, alert.symbol, alert.condition
    )

    if existing_alert:
        # If an alert with the same condition exists, update it
        updated_alert = await price_alert_service.update_alert(
            db, existing_alert.id, alert
        )
        updated_alert.status_message = "갱신되었습니다."
        return updated_alert
    else:
        # Otherwise, create a new alert
        new_alert = await price_alert_service.create_alert(db=db, user_id=current_user.id, alert_data=alert)
        new_alert.status_message = "생성되었습니다."
        return new_alert


@router.get("/price-alerts/", response_model=List[PriceAlertRead],
            summary="사용자의 모든 가격 알림 조회",
            description="현재 사용자가 설정한 모든 가격 알림 목록을 조회합니다.",
            response_description="가격 알림 목록.")
def get_price_alerts(
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    price_alert_service: PriceAlertService = Depends(get_price_alert_service)
):
    alerts = price_alert_service.get_alerts(db, current_user.id)
    return alerts


@router.get("/price-alerts/{alert_id}", response_model=PriceAlertRead,
            summary="특정 가격 알림 조회",
            description="ID를 사용하여 특정 가격 알림의 상세 정보를 조회합니다.",
            response_description="가격 알림의 상세 정보.")
def get_price_alert(
    alert_id: int,
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    price_alert_service: PriceAlertService = Depends(get_price_alert_service)
):
    alert = price_alert_service.get_alert_by_id(db, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    return alert


@router.put("/price-alerts/{alert_id}", response_model=PriceAlertRead,
            summary="가격 알림 수정",
            description="ID를 사용하여 기존 가격 알림의 정보를 수정합니다.",
            response_description="성공적으로 수정된 가격 알림의 상세 정보.")
async def update_price_alert(
    alert_id: int,
    alert_update: PriceAlertUpdate,
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    price_alert_service: PriceAlertService = Depends(get_price_alert_service)
):
    alert = price_alert_service.get_alert_by_id(db, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")

    updated_alert = await price_alert_service.update_alert(db, alert_id, alert_update)
    return updated_alert


@router.delete("/price-alerts/{alert_id}", status_code=204,
               summary="가격 알림 삭제",
               description="ID를 사용하여 특정 가격 알림을 삭제합니다.",
               response_description="성공적으로 삭제되었음을 나타내는 204 No Content 응답.")
async def delete_price_alert(
    alert_id: int,
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    price_alert_service: PriceAlertService = Depends(get_price_alert_service)
):
    alert = price_alert_service.get_alert_by_id(db, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")

    await price_alert_service.delete_alert(db, alert_id)
    return


@router.put("/price-alerts/{alert_id}/pause", response_model=PriceAlertRead,
            summary="가격 알림 일시정지",
            description="ID를 사용하여 특정 가격 알림을 일시정지합니다.",
            response_description="일시정지된 가격 알림의 상세 정보.")
async def pause_price_alert(
    alert_id: int,
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    price_alert_service: PriceAlertService = Depends(get_price_alert_service)
):
    alert = price_alert_service.get_alert_by_id(db, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    
    paused_alert = await price_alert_service.update_alert_status(db, alert_id, is_active=False)
    return paused_alert


@router.put("/price-alerts/{alert_id}/resume", response_model=PriceAlertRead,
            summary="가격 알림 재개",
            description="ID를 사용하여 특정 가격 알림을 재개합니다.",
            response_description="재개된 가격 알림의 상세 정보.")
async def resume_price_alert(
    alert_id: int,
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    price_alert_service: PriceAlertService = Depends(get_price_alert_service)
):
    alert = price_alert_service.get_alert_by_id(db, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    
    resumed_alert = await price_alert_service.update_alert_status(db, alert_id, is_active=True)
    return resumed_alert