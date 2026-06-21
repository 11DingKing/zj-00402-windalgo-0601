from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.models import (
    RiskChain,
    RiskPhase,
    RiskChainStatus,
    Turbine,
    Alert,
    AlertLevel,
    AlertHandling,
    HandlingType,
    AlertStatus
)
from app.schemas import (
    RiskChain as RiskChainSchema,
    RiskChainDetail,
    RiskPhase as RiskPhaseSchema,
    RiskChainCloseRequest,
    RiskChainListResponse,
    Alert as AlertSchema,
    AlertHandling as AlertHandlingSchema
)
from app.risk_chain_engine import RiskChainEngine

router = APIRouter(prefix="/risk-chains")


@router.get("", response_model=RiskChainListResponse, summary="查询风险链列表")
def get_risk_chains(
    turbine_code: Optional[str] = None,
    status: Optional[RiskChainStatus] = None,
    current_phase: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(RiskChain)

    if turbine_code:
        turbine = db.query(Turbine).filter(Turbine.turbine_code == turbine_code).first()
        if not turbine:
            raise HTTPException(status_code=404, detail=f"机组 {turbine_code} 不存在")
        query = query.filter(RiskChain.turbine_id == turbine.id)

    if status:
        query = query.filter(RiskChain.status == status)
    if current_phase:
        query = query.filter(RiskChain.current_phase == current_phase)
    if start_time:
        query = query.filter(RiskChain.started_at >= start_time)
    if end_time:
        query = query.filter(RiskChain.started_at <= end_time)

    total = query.count()
    items = query.order_by(RiskChain.last_updated_at.desc()).offset(skip).limit(limit).all()

    result_items = []
    for chain in items:
        chain_dict = _chain_to_schema(chain)
        result_items.append(chain_dict)

    return RiskChainListResponse(total=total, items=result_items)


@router.get("/{chain_id}", response_model=RiskChainDetail, summary="获取风险链详情")
def get_risk_chain(chain_id: int, db: Session = Depends(get_db)):
    chain = db.query(RiskChain).filter(RiskChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="风险链不存在")

    return _chain_to_detail_schema(chain)


@router.get("/{chain_id}/phases", response_model=List[RiskPhaseSchema], summary="获取风险链阶段列表")
def get_risk_chain_phases(chain_id: int, db: Session = Depends(get_db)):
    chain = db.query(RiskChain).filter(RiskChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="风险链不存在")

    return db.query(RiskPhase).filter(
        RiskPhase.risk_chain_id == chain_id
    ).order_by(RiskPhase.phase_index.asc()).all()


@router.get("/{chain_id}/alerts", response_model=List[AlertSchema], summary="获取风险链关联的告警")
def get_risk_chain_alerts(
    chain_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    chain = db.query(RiskChain).filter(RiskChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="风险链不存在")

    return db.query(Alert).filter(
        Alert.risk_chain_id == chain_id
    ).order_by(Alert.triggered_at.desc()).offset(skip).limit(limit).all()


@router.get("/{chain_id}/handling-records", response_model=List[AlertHandlingSchema], summary="获取风险链处置记录")
def get_risk_chain_handling_records(
    chain_id: int,
    db: Session = Depends(get_db)
):
    chain = db.query(RiskChain).filter(RiskChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="风险链不存在")

    alert_ids = [a.id for a in chain.alerts]
    if not alert_ids:
        return []

    return db.query(AlertHandling).filter(
        AlertHandling.alert_id.in_(alert_ids)
    ).order_by(AlertHandling.handled_at.desc()).all()


@router.post("/{chain_id}/close", response_model=RiskChainDetail, summary="关闭风险链")
def close_risk_chain(
    chain_id: int,
    close_data: RiskChainCloseRequest,
    db: Session = Depends(get_db)
):
    chain = db.query(RiskChain).filter(RiskChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="风险链不存在")

    if chain.status == RiskChainStatus.CLOSED:
        raise HTTPException(status_code=400, detail="该风险链已关闭")

    chain.status = RiskChainStatus.CLOSED
    chain.closed_at = datetime.utcnow()
    chain.close_condition = close_data.close_condition or "人工关闭"
    chain.close_note = close_data.close_note

    if chain.phases:
        last_phase = chain.phases[-1]
        if not last_phase.ended_at:
            last_phase.ended_at = datetime.utcnow()

    for alert in chain.alerts:
        if alert.status != AlertStatus.CLOSED:
            handling = AlertHandling(
                alert_id=alert.id,
                handling_type=HandlingType.RESUMED_OPERATION,
                operator=close_data.operator,
                note=f"风险链关闭：{close_data.close_note or '风险已消除'}",
                handled_at=datetime.utcnow()
            )
            db.add(handling)
            alert.status = AlertStatus.CLOSED
            alert.closed_at = datetime.utcnow()
            alert.close_note = f"风险链关闭：{close_data.close_note or '风险已消除'}"

    db.commit()
    db.refresh(chain)

    return _chain_to_detail_schema(chain)


@router.post("/{chain_id}/escalate", response_model=RiskChainDetail, summary="标记风险链升级")
def escalate_risk_chain(
    chain_id: int,
    note: Optional[str] = None,
    db: Session = Depends(get_db)
):
    chain = db.query(RiskChain).filter(RiskChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="风险链不存在")

    if chain.status == RiskChainStatus.CLOSED:
        raise HTTPException(status_code=400, detail="已关闭的风险链无法升级")

    chain.status = RiskChainStatus.ESCALATING
    chain.escalation_count += 1
    chain.last_updated_at = datetime.utcnow()

    db.commit()
    db.refresh(chain)

    return _chain_to_detail_schema(chain)


@router.get("/close-conditions", summary="获取风险链关闭条件列表")
def get_close_conditions():
    return {
        "conditions": RiskChainEngine.get_close_conditions()
    }


def _chain_to_schema(chain: RiskChain) -> RiskChainSchema:
    turbine = chain.turbine
    return RiskChainSchema(
        id=chain.id,
        turbine_id=chain.turbine_id,
        turbine_code=turbine.turbine_code if turbine else None,
        chain_code=chain.chain_code,
        status=chain.status,
        current_phase=chain.current_phase,
        current_level=chain.current_level,
        started_at=chain.started_at,
        last_updated_at=chain.last_updated_at,
        closed_at=chain.closed_at,
        close_condition=chain.close_condition,
        close_note=chain.close_note,
        total_alerts=chain.total_alerts,
        escalation_count=chain.escalation_count,
        overall_suggestion=chain.overall_suggestion,
        phases=list(chain.phases)
    )


def _chain_to_detail_schema(chain: RiskChain) -> RiskChainDetail:
    base = _chain_to_schema(chain)
    return RiskChainDetail(
        **base.model_dump(),
        alerts=list(chain.alerts)
    )
