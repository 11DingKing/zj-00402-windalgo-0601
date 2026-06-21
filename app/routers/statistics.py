from typing import List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database import get_db
from app.models import Turbine, Alert, AlertStatus, AlertLevel, RiskChain, RiskChainStatus
from app.alert_rules import (
    get_level_rank,
    is_high_risk,
    calculate_risk_score,
    count_high_risk,
    filter_active,
    filter_closed,
    HIGH_RISK_LEVELS,
    CHAIN_RISK_SCORE_MULTIPLIER,
)
from app.schemas import (
    StatisticsResponse,
    RidgeRiskDistribution,
    RiskDistributionItem,
    HighRiskPeriodItem,
    RepeatedAlertTurbine
)

router = APIRouter(prefix="/statistics")


@router.get("", response_model=StatisticsResponse, summary="获取综合统计信息")
def get_statistics(
    days: int = Query(7, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db)
):
    start_date = datetime.utcnow() - timedelta(days=days)

    total_turbines = db.query(func.count(Turbine.id)).scalar()
    total_alerts = db.query(func.count(Alert.id)).filter(
        Alert.triggered_at >= start_date
    ).scalar()
    pending_alerts = db.query(func.count(Alert.id)).filter(
        Alert.status == AlertStatus.PENDING
    ).scalar()
    processing_alerts = db.query(func.count(Alert.id)).filter(
        Alert.status == AlertStatus.PROCESSING
    ).scalar()
    closed_alerts = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.triggered_at >= start_date,
            Alert.status == AlertStatus.CLOSED
        )
    ).scalar()
    active_alerts = db.query(func.count(Alert.id)).filter(
        Alert.status.in_([AlertStatus.PENDING, AlertStatus.PROCESSING])
    ).scalar()
    high_risk_alerts = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.triggered_at >= start_date,
            Alert.alert_level.in_(HIGH_RISK_LEVELS)
        )
    ).scalar()
    active_high_risk_alerts = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.status.in_([AlertStatus.PENDING, AlertStatus.PROCESSING]),
            Alert.alert_level.in_(HIGH_RISK_LEVELS)
        )
    ).scalar()

    total_risk_chains = db.query(func.count(RiskChain.id)).filter(
        RiskChain.started_at >= start_date
    ).scalar()
    active_risk_chains = db.query(func.count(RiskChain.id)).filter(
        RiskChain.status.in_([
            RiskChainStatus.ACTIVE,
            RiskChainStatus.ESCALATING,
            RiskChainStatus.STABILIZED
        ])
    ).scalar()
    escalating_risk_chains = db.query(func.count(RiskChain.id)).filter(
        RiskChain.status == RiskChainStatus.ESCALATING
    ).scalar()

    ridge_distributions = _get_ridge_risk_distribution(db, start_date)
    high_risk_periods = _get_high_risk_periods(db, start_date)
    repeated_alert_turbines = _get_repeated_alert_turbines(db, start_date)

    return StatisticsResponse(
        total_turbines=total_turbines or 0,
        total_alerts=total_alerts or 0,
        pending_alerts=pending_alerts or 0,
        processing_alerts=processing_alerts or 0,
        closed_alerts=closed_alerts or 0,
        active_alerts=active_alerts or 0,
        high_risk_alerts=high_risk_alerts or 0,
        active_high_risk_alerts=active_high_risk_alerts or 0,
        total_risk_chains=total_risk_chains or 0,
        active_risk_chains=active_risk_chains or 0,
        escalating_risk_chains=escalating_risk_chains or 0,
        ridge_distributions=ridge_distributions,
        high_risk_periods=high_risk_periods,
        repeated_alert_turbines=repeated_alert_turbines
    )


@router.get("/ridge-distribution", response_model=List[RidgeRiskDistribution], summary="山脊风险分布")
def get_ridge_distribution(
    days: int = Query(7, ge=1, le=365),
    ridge_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    start_date = datetime.utcnow() - timedelta(days=days)
    return _get_ridge_risk_distribution(db, start_date, ridge_name)


@router.get("/high-risk-periods", response_model=List[HighRiskPeriodItem], summary="高风险时段分布")
def get_high_risk_periods(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    start_date = datetime.utcnow() - timedelta(days=days)
    return _get_high_risk_periods(db, start_date)


@router.get("/repeated-alert-turbines", response_model=List[RepeatedAlertTurbine], summary="重复告警机组")
def get_repeated_alert_turbines(
    days: int = Query(7, ge=1, le=365),
    min_alerts: int = Query(3, ge=1, le=100),
    db: Session = Depends(get_db)
):
    start_date = datetime.utcnow() - timedelta(days=days)
    return _get_repeated_alert_turbines(db, start_date, min_alerts)


def _get_ridge_risk_distribution(
    db: Session,
    start_date: datetime,
    ridge_name: Optional[str] = None
) -> List[RidgeRiskDistribution]:
    query = db.query(Turbine)
    if ridge_name:
        query = query.filter(Turbine.ridge_name == ridge_name)
    turbines = query.order_by(Turbine.ridge_name, Turbine.position).all()

    ridge_data = defaultdict(list)
    for turbine in turbines:
        alerts = db.query(Alert).filter(
            and_(
                Alert.turbine_id == turbine.id,
                Alert.triggered_at >= start_date
            )
        ).all()

        active_alerts = filter_active(alerts)
        closed_alerts_list = filter_closed(alerts)

        alert_count = len(alerts)
        high_risk_count = count_high_risk(alerts)

        active_alert_count = len(active_alerts)
        active_high_risk_count = count_high_risk(active_alerts)

        risk_score = calculate_risk_score(alert_count, high_risk_count)
        active_risk_score = calculate_risk_score(active_alert_count, active_high_risk_count)
        closed_alert_count = len(closed_alerts_list)

        risk_chains = db.query(RiskChain).filter(
            and_(
                RiskChain.turbine_id == turbine.id,
                RiskChain.started_at >= start_date
            )
        ).all()

        active_chains = [
            c for c in risk_chains
            if c.status in [RiskChainStatus.ACTIVE, RiskChainStatus.ESCALATING, RiskChainStatus.STABILIZED]
        ]
        active_chain_count = len(active_chains)
        high_risk_chain_count = sum(
            1 for c in risk_chains
            if is_high_risk(c.current_level)
            and c.status != RiskChainStatus.CLOSED
        )
        chain_risk_score = sum(
            (get_level_rank(c.current_level) + 1) * CHAIN_RISK_SCORE_MULTIPLIER
            for c in risk_chains
            if c.status != RiskChainStatus.CLOSED
        )

        ridge_data[turbine.ridge_name].append(RiskDistributionItem(
            turbine_code=turbine.turbine_code,
            position=turbine.position,
            alert_count=alert_count,
            high_risk_count=high_risk_count,
            risk_score=round(risk_score, 2),
            active_alert_count=active_alert_count,
            active_high_risk_count=active_high_risk_count,
            active_risk_score=round(active_risk_score, 2),
            closed_alert_count=closed_alert_count,
            active_risk_chain_count=active_chain_count,
            high_risk_chain_count=high_risk_chain_count,
            chain_risk_score=round(chain_risk_score, 2)
        ))

    result = []
    for ridge, turbines_data in sorted(ridge_data.items()):
        result.append(RidgeRiskDistribution(
            ridge_name=ridge,
            turbines=sorted(turbines_data, key=lambda x: x.position)
        ))

    return result


def _get_high_risk_periods(
    db: Session,
    start_date: datetime
) -> List[HighRiskPeriodItem]:
    alerts = db.query(Alert).filter(
        Alert.triggered_at >= start_date
    ).all()

    hour_data = defaultdict(lambda: {"alert_count": 0, "high_risk_count": 0})

    for alert in alerts:
        hour = alert.triggered_at.hour
        hour_data[hour]["alert_count"] += 1
        if is_high_risk(alert.alert_level):
            hour_data[hour]["high_risk_count"] += 1

    result = []
    for hour in range(24):
        data = hour_data.get(hour, {"alert_count": 0, "high_risk_count": 0})
        result.append(HighRiskPeriodItem(
            hour=hour,
            alert_count=data["alert_count"],
            high_risk_count=data["high_risk_count"]
        ))

    return sorted(result, key=lambda x: x.hour)


def _get_repeated_alert_turbines(
    db: Session,
    start_date: datetime,
    min_alerts: int = 3
) -> List[RepeatedAlertTurbine]:
    turbines = db.query(Turbine).all()
    result = []

    for turbine in turbines:
        alerts = db.query(Alert).filter(
            and_(
                Alert.turbine_id == turbine.id,
                Alert.triggered_at >= start_date
            )
        ).all()

        if len(alerts) >= min_alerts:
            alert_types = sorted(list(set(a.alert_type.value for a in alerts)))

            active_alerts_list = filter_active(alerts)
            closed_alerts_list = filter_closed(alerts)
            active_alert_types = sorted(list(set(a.alert_type.value for a in active_alerts_list)))

            risk_chains = db.query(RiskChain).filter(
                and_(
                    RiskChain.turbine_id == turbine.id,
                    RiskChain.started_at >= start_date
                )
            ).all()

            active_chains = sum(
                1 for c in risk_chains
                if c.status in [RiskChainStatus.ACTIVE, RiskChainStatus.ESCALATING, RiskChainStatus.STABILIZED]
            )
            max_phases = max([len(c.phases) for c in risk_chains], default=0)
            has_escalation = any(
                c.escalation_count > 0 for c in risk_chains
            )

            result.append(RepeatedAlertTurbine(
                turbine_code=turbine.turbine_code,
                ridge_name=turbine.ridge_name,
                total_alerts=len(alerts),
                alert_types=alert_types,
                active_alerts=len(active_alerts_list),
                active_alert_types=active_alert_types,
                closed_alerts=len(closed_alerts_list),
                active_risk_chains=active_chains,
                max_chain_phases=max_phases,
                has_escalation_chain=has_escalation
            ))

    return sorted(result, key=lambda x: (x.active_alerts, x.total_alerts), reverse=True)
