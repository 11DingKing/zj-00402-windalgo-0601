from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.models import Turbine, OperatingData, Alert, AlertStatus, AlertLevel, RiskChain
from app.schemas import (
    OperatingDataCreate,
    OperatingData as OperatingDataSchema,
    BatchDataResponse
)
from app.alert_engine import AlertRuleEngine
from app.risk_chain_engine import RiskChainEngine, get_level_rank

router = APIRouter(prefix="/operating-data")

DUPLICATE_ALERT_WINDOW_MINUTES = 30


def _find_or_merge_alert(
    db: Session,
    turbine_id: int,
    operating_data_id: int,
    alert_type,
    alert_level,
    trigger_reason: str,
    suggestion: str,
    triggered_at: datetime
):
    cutoff_time = triggered_at - timedelta(minutes=DUPLICATE_ALERT_WINDOW_MINUTES)

    existing_alert = db.query(Alert).filter(
        and_(
            Alert.turbine_id == turbine_id,
            Alert.alert_type == alert_type,
            Alert.status.in_([AlertStatus.PENDING, AlertStatus.PROCESSING]),
            Alert.triggered_at >= cutoff_time
        )
    ).order_by(Alert.triggered_at.desc()).first()

    if existing_alert:
        if get_level_rank(alert_level) > get_level_rank(existing_alert.alert_level):
            existing_alert.alert_level = alert_level
            existing_alert.suggestion = suggestion
        existing_alert.trigger_reason = trigger_reason
        existing_alert.triggered_at = triggered_at
        existing_alert.operating_data_id = operating_data_id
        is_new = False
        return existing_alert, is_new
    else:
        alert = Alert(
            turbine_id=turbine_id,
            operating_data_id=operating_data_id,
            alert_type=alert_type,
            alert_level=alert_level,
            status=AlertStatus.PENDING,
            trigger_reason=trigger_reason,
            suggestion=suggestion,
            triggered_at=triggered_at
        )
        db.add(alert)
        db.flush()
        is_new = True
        return alert, is_new


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
        now = datetime.utcnow()
        alert, is_new_alert = _find_or_merge_alert(
            db, turbine.id, operating_data.id,
            result.alert_type, result.alert_level,
            result.trigger_reason, result.suggestion, now
        )

        if is_new_alert:
            chain_result = RiskChainEngine.process_alert(db, alert, turbine)
            risk_chain_code = chain_result.risk_chain.chain_code
            is_new_chain = chain_result.is_new_chain
            is_escalation = chain_result.is_escalation
        else:
            risk_chain_code = None
            is_new_chain = False
            is_escalation = False
            if alert.risk_chain_id:
                chain = db.query(RiskChain).filter(RiskChain.id == alert.risk_chain_id).first()
                if chain:
                    risk_chain_code = chain.chain_code
                    chain.last_updated_at = now

        generated_alerts.append({
            "alert_id": alert.id,
            "alert_type": result.alert_type.value,
            "alert_level": alert.alert_level.value,
            "trigger_reason": alert.trigger_reason,
            "suggestion": alert.suggestion,
            "risk_chain_id": alert.risk_chain_id,
            "risk_chain_code": risk_chain_code,
            "is_new_chain": is_new_chain,
            "is_escalation": is_escalation,
            "is_merged_alert": not is_new_alert
        })

    RiskChainEngine.check_and_close_stale_chains(db)

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
            now = datetime.utcnow()
            alert, is_new_alert = _find_or_merge_alert(
                db, turbine.id, operating_data.id,
                result.alert_type, result.alert_level,
                result.trigger_reason, result.suggestion, now
            )

            if is_new_alert:
                RiskChainEngine.process_alert(db, alert, turbine)
                alerts_generated += 1
            else:
                if alert.risk_chain_id:
                    chain = db.query(RiskChain).filter(RiskChain.id == alert.risk_chain_id).first()
                    if chain:
                        chain.last_updated_at = now

        records_processed += 1

    RiskChainEngine.check_and_close_stale_chains(db)
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
