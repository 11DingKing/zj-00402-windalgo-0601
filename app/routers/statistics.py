from typing import List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database import get_db
from app.models import Turbine, Alert, AlertStatus, AlertLevel
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
    high_risk_alerts = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.triggered_at >= start_date,
            Alert.alert_level.in_([AlertLevel.HIGH, AlertLevel.CRITICAL])
        )
    ).scalar()

    ridge_distributions = _get_ridge_risk_distribution(db, start_date)
    high_risk_periods = _get_high_risk_periods(db, start_date)
    repeated_alert_turbines = _get_repeated_alert_turbines(db, start_date)

    return StatisticsResponse(
        total_turbines=total_turbines or 0,
        total_alerts=total_alerts or 0,
        pending_alerts=pending_alerts or 0,
        high_risk_alerts=high_risk_alerts or 0,
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

        alert_count = len(alerts)
        high_risk_count = sum(
            1 for a in alerts
            if a.alert_level in [AlertLevel.HIGH, AlertLevel.CRITICAL]
        )

        risk_score = alert_count * 1 + high_risk_count * 2

        ridge_data[turbine.ridge_name].append(RiskDistributionItem(
            turbine_code=turbine.turbine_code,
            position=turbine.position,
            alert_count=alert_count,
            high_risk_count=high_risk_count,
            risk_score=round(risk_score, 2)
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
        if alert.alert_level in [AlertLevel.HIGH, AlertLevel.CRITICAL]:
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
            result.append(RepeatedAlertTurbine(
                turbine_code=turbine.turbine_code,
                ridge_name=turbine.ridge_name,
                total_alerts=len(alerts),
                alert_types=alert_types
            ))

    return sorted(result, key=lambda x: x.total_alerts, reverse=True)
