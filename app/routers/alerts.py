from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, AlertStatus, AlertHandling, HandlingType, Turbine, AlertLevel
from app.schemas import (
    Alert as AlertSchema,
    AlertHandlingCreate,
    AlertHandling as AlertHandlingSchema,
    AlertHandlingResponse
)

router = APIRouter(prefix="/alerts")


@router.get("", response_model=List[AlertSchema], summary="查询告警列表")
def get_alerts(
    turbine_code: Optional[str] = None,
    alert_type: Optional[str] = None,
    alert_level: Optional[AlertLevel] = None,
    status: Optional[AlertStatus] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(Alert)

    if turbine_code:
        turbine = db.query(Turbine).filter(Turbine.turbine_code == turbine_code).first()
        if not turbine:
            raise HTTPException(status_code=404, detail=f"机组 {turbine_code} 不存在")
        query = query.filter(Alert.turbine_id == turbine.id)

    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    if alert_level:
        query = query.filter(Alert.alert_level == alert_level)
    if status:
        query = query.filter(Alert.status == status)
    if start_time:
        query = query.filter(Alert.triggered_at >= start_time)
    if end_time:
        query = query.filter(Alert.triggered_at <= end_time)

    return query.order_by(Alert.triggered_at.desc()).offset(skip).limit(limit).all()


@router.get("/{alert_id}", response_model=AlertSchema, summary="获取告警详情")
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    return alert


@router.post("/{alert_id}/handle", response_model=AlertHandlingResponse, summary="处理告警")
def handle_alert(
    alert_id: int,
    handling_in: AlertHandlingCreate,
    db: Session = Depends(get_db)
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    if alert.status == AlertStatus.CLOSED:
        raise HTTPException(status_code=400, detail="该告警已关闭，无法重复处理")

    handling_record = AlertHandling(
        alert_id=alert_id,
        handling_type=handling_in.handling_type,
        operator=handling_in.operator,
        note=handling_in.note,
        handled_at=datetime.utcnow()
    )
    db.add(handling_record)

    if handling_in.handling_type in [
        HandlingType.SHUTDOWN_INSPECTION,
        HandlingType.LOAD_REDUCED
    ]:
        alert.status = AlertStatus.PROCESSING
    elif handling_in.handling_type in [
        HandlingType.FALSE_ALARM,
        HandlingType.RESUMED_OPERATION
    ]:
        alert.status = AlertStatus.CLOSED
        alert.closed_at = datetime.utcnow()
        alert.close_note = handling_in.note or f"{handling_in.handling_type.value}"

    db.commit()
    db.refresh(alert)

    status_text = {
        HandlingType.FALSE_ALARM: "标记为误报",
        HandlingType.LOAD_REDUCED: "已降载处理",
        HandlingType.SHUTDOWN_INSPECTION: "已停机检查",
        HandlingType.RESUMED_OPERATION: "已恢复运行"
    }

    return AlertHandlingResponse(
        success=True,
        message=f"告警{status_text.get(handling_in.handling_type, '处理成功')}",
        alert=alert
    )


@router.get("/{alert_id}/history", response_model=List[AlertHandlingSchema], summary="获取告警处理历史")
def get_alert_history(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    return db.query(AlertHandling).filter(
        AlertHandling.alert_id == alert_id
    ).order_by(AlertHandling.handled_at.desc()).all()


@router.post("/{alert_id}/close", response_model=AlertHandlingResponse, summary="关闭告警")
def close_alert(
    alert_id: int,
    operator: str,
    note: Optional[str] = None,
    db: Session = Depends(get_db)
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    if alert.status == AlertStatus.CLOSED:
        raise HTTPException(status_code=400, detail="该告警已关闭")

    handling_record = AlertHandling(
        alert_id=alert_id,
        handling_type=HandlingType.RESUMED_OPERATION,
        operator=operator,
        note=note or "手动关闭告警",
        handled_at=datetime.utcnow()
    )
    db.add(handling_record)

    alert.status = AlertStatus.CLOSED
    alert.closed_at = datetime.utcnow()
    alert.close_note = note or "手动关闭"

    db.commit()
    db.refresh(alert)

    return AlertHandlingResponse(
        success=True,
        message="告警已关闭",
        alert=alert
    )
