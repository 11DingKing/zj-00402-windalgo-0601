from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Turbine, OperatingData, Alert, AlertStatus
from app.schemas import (
    OperatingDataCreate,
    OperatingData as OperatingDataSchema,
    BatchDataResponse
)
from app.alert_engine import AlertRuleEngine

router = APIRouter(prefix="/operating-data")


@router.post("", response_model=List[dict], summary="上报运行数据并触发告警检测")
def create_operating_data(
    data_in: OperatingDataCreate,
    db: Session = Depends(get_db)
):
    turbine = db.query(Turbine).filter(Turbine.turbine_code == data_in.turbine_code).first()
    if not turbine:
        raise HTTPException(status_code=404, detail=f"机组 {data_in.turbine_code} 不存在")

    data_dict = data_in.model_dump(exclude={"turbine_code"})
    data_dict["turbine_id"] = turbine.id
    operating_data = OperatingData(**data_dict)
    db.add(operating_data)
    db.flush()

    alert_results = AlertRuleEngine.analyze(operating_data, turbine)
    generated_alerts = []

    for result in alert_results:
        alert = Alert(
            turbine_id=turbine.id,
            operating_data_id=operating_data.id,
            alert_type=result.alert_type,
            alert_level=result.alert_level,
            status=AlertStatus.PENDING,
            trigger_reason=result.trigger_reason,
            suggestion=result.suggestion,
            triggered_at=datetime.utcnow()
        )
        db.add(alert)
        db.flush()
        generated_alerts.append({
            "alert_id": alert.id,
            "alert_type": result.alert_type.value,
            "alert_level": result.alert_level.value,
            "trigger_reason": result.trigger_reason,
            "suggestion": result.suggestion
        })

    db.commit()
    db.refresh(operating_data)

    return generated_alerts


@router.post("/batch", response_model=BatchDataResponse, summary="批量上报运行数据")
def create_operating_data_batch(
    data_list: List[OperatingDataCreate],
    db: Session = Depends(get_db)
):
    records_processed = 0
    alerts_generated = 0
    turbine_cache = {}

    for data_in in data_list:
        if data_in.turbine_code not in turbine_cache:
            turbine = db.query(Turbine).filter(Turbine.turbine_code == data_in.turbine_code).first()
            if not turbine:
                continue
            turbine_cache[data_in.turbine_code] = turbine
        else:
            turbine = turbine_cache[data_in.turbine_code]

        data_dict = data_in.model_dump(exclude={"turbine_code"})
        data_dict["turbine_id"] = turbine.id
        operating_data = OperatingData(**data_dict)
        db.add(operating_data)
        db.flush()

        alert_results = AlertRuleEngine.analyze(operating_data, turbine)
        for result in alert_results:
            alert = Alert(
                turbine_id=turbine.id,
                operating_data_id=operating_data.id,
                alert_type=result.alert_type,
                alert_level=result.alert_level,
                status=AlertStatus.PENDING,
                trigger_reason=result.trigger_reason,
                suggestion=result.suggestion,
                triggered_at=datetime.utcnow()
            )
            db.add(alert)
            alerts_generated += 1

        records_processed += 1

    db.commit()

    return BatchDataResponse(
        success=True,
        records_processed=records_processed,
        alerts_generated=alerts_generated,
        message=f"成功处理 {records_processed} 条数据，生成 {alerts_generated} 条告警"
    )


@router.get("", response_model=List[OperatingDataSchema], summary="查询运行数据")
def get_operating_data(
    turbine_code: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(OperatingData)

    if turbine_code:
        turbine = db.query(Turbine).filter(Turbine.turbine_code == turbine_code).first()
        if not turbine:
            raise HTTPException(status_code=404, detail=f"机组 {turbine_code} 不存在")
        query = query.filter(OperatingData.turbine_id == turbine.id)

    if start_time:
        query = query.filter(OperatingData.timestamp >= start_time)
    if end_time:
        query = query.filter(OperatingData.timestamp <= end_time)

    return query.order_by(OperatingData.timestamp.desc()).offset(skip).limit(limit).all()


@router.get("/{data_id}", response_model=OperatingDataSchema, summary="获取运行数据详情")
def get_operating_data_detail(data_id: int, db: Session = Depends(get_db)):
    data = db.query(OperatingData).filter(OperatingData.id == data_id).first()
    if not data:
        raise HTTPException(status_code=404, detail="运行数据不存在")
    return data
