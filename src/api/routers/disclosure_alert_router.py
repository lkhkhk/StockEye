from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from src.common.database import db_connector
from src.common.models.user import User
from src.common.schemas.disclosure_alert import DisclosureAlertCreate, DisclosureAlertRead, DisclosureAlertUpdate
from src.api.auth.jwt_handler import get_current_active_user
from src.common.services.disclosure_alert_service import DisclosureAlertService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/disclosure-alerts", tags=["disclosure-alerts"])

def get_disclosure_alert_service():
    return DisclosureAlertService()

@router.post("/", response_model=DisclosureAlertRead, status_code=201)
def create_disclosure_alert(
    alert: DisclosureAlertCreate,
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    disclosure_alert_service: DisclosureAlertService = Depends(get_disclosure_alert_service)
):
    return disclosure_alert_service.create_alert(db=db, user_id=current_user.id, alert_data=alert)

@router.get("/", response_model=List[DisclosureAlertRead])
def get_disclosure_alerts(
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    disclosure_alert_service: DisclosureAlertService = Depends(get_disclosure_alert_service)
):
    return disclosure_alert_service.get_alerts_by_user(db, current_user.id)

@router.put("/{alert_id}", response_model=DisclosureAlertRead)
def update_disclosure_alert(
    alert_id: int,
    alert_update: DisclosureAlertUpdate,
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    disclosure_alert_service: DisclosureAlertService = Depends(get_disclosure_alert_service)
):
    alert = disclosure_alert_service.get_alert_by_id(db, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Disclosure alert not found")
    return disclosure_alert_service.update_alert(db, alert_id, alert_update)

@router.put("/{alert_id}/pause", response_model=DisclosureAlertRead)
def pause_disclosure_alert(
    alert_id: int,
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    disclosure_alert_service: DisclosureAlertService = Depends(get_disclosure_alert_service)
):
    alert = disclosure_alert_service.get_alert_by_id(db, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Disclosure alert not found")
    return disclosure_alert_service.update_alert_status(db, alert_id, False)

@router.put("/{alert_id}/resume", response_model=DisclosureAlertRead)
def resume_disclosure_alert(
    alert_id: int,
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    disclosure_alert_service: DisclosureAlertService = Depends(get_disclosure_alert_service)
):
    alert = disclosure_alert_service.get_alert_by_id(db, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Disclosure alert not found")
    return disclosure_alert_service.update_alert_status(db, alert_id, True)

@router.delete("/{alert_id}", status_code=204)
def delete_disclosure_alert(
    alert_id: int,
    db: Session = Depends(db_connector.get_db),
    current_user: User = Depends(get_current_active_user),
    disclosure_alert_service: DisclosureAlertService = Depends(get_disclosure_alert_service)
):
    alert = disclosure_alert_service.get_alert_by_id(db, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Disclosure alert not found")
    disclosure_alert_service.delete_alert(db, alert_id)
    return
