from typing import List

from app.models import AlertLevel, Alert


HIGH_RISK_LEVELS = [AlertLevel.HIGH, AlertLevel.CRITICAL]

RISK_SCORE_WEIGHTS = {
    "alert_count": 1,
    "high_risk_count": 2,
}

CHAIN_RISK_SCORE_MULTIPLIER = 2


def get_level_rank(level: AlertLevel) -> int:
    level_order = [
        AlertLevel.LOW,
        AlertLevel.MEDIUM,
        AlertLevel.HIGH,
        AlertLevel.CRITICAL,
    ]
    try:
        return level_order.index(level)
    except ValueError:
        return -1


def is_high_risk(level: AlertLevel) -> bool:
    return level in HIGH_RISK_LEVELS


def calculate_risk_score(alert_count: int, high_risk_count: int) -> float:
    return (
        alert_count * RISK_SCORE_WEIGHTS["alert_count"]
        + high_risk_count * RISK_SCORE_WEIGHTS["high_risk_count"]
    )


def count_high_risk(alerts: List[Alert]) -> int:
    return sum(1 for a in alerts if is_high_risk(a.alert_level))


def filter_active(alerts: List[Alert]) -> List[Alert]:
    from app.models import AlertStatus
    return [a for a in alerts if a.status in [AlertStatus.PENDING, AlertStatus.PROCESSING]]


def filter_closed(alerts: List[Alert]) -> List[Alert]:
    from app.models import AlertStatus
    return [a for a in alerts if a.status == AlertStatus.CLOSED]
