from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid

from sqlalchemy.orm import Session

from app.models import (
    AlertType,
    AlertLevel,
    Alert,
    RiskChain,
    RiskPhase,
    RiskChainStatus,
    Turbine
)
from app.alert_rules import get_level_rank


RISK_EVOLUTION_ORDER = [
    AlertType.POWER_DEVIATION,
    AlertType.STALL_TENDENCY,
    AlertType.VORTEX_VIBRATION,
    AlertType.TEMPERATURE_ANOMALY
]

RISK_CHAIN_TIMEOUT_HOURS = 24


def get_risk_severity_rank(alert_type: AlertType) -> int:
    try:
        return RISK_EVOLUTION_ORDER.index(alert_type)
    except ValueError:
        return -1


def is_risk_escalation(prev_type: AlertType, new_type: AlertType) -> bool:
    prev_rank = get_risk_severity_rank(prev_type)
    new_rank = get_risk_severity_rank(new_type)
    return new_rank > prev_rank


@dataclass
class RiskChainResult:
    risk_chain: RiskChain
    is_new_chain: bool
    is_escalation: bool
    new_phase: Optional[RiskPhase]


class RiskChainEngine:

    @staticmethod
    def process_alert(
        db: Session,
        alert: Alert,
        turbine: Turbine
    ) -> RiskChainResult:
        active_chain = RiskChainEngine._find_active_chain(db, turbine.id, alert.triggered_at)

        if not active_chain:
            return RiskChainEngine._create_new_chain(db, alert, turbine)

        return RiskChainEngine._update_existing_chain(db, active_chain, alert)

    @staticmethod
    def _find_active_chain(
        db: Session,
        turbine_id: int,
        alert_time: datetime
    ) -> Optional[RiskChain]:
        cutoff_time = alert_time - timedelta(hours=RISK_CHAIN_TIMEOUT_HOURS)
        chain = db.query(RiskChain).filter(
            RiskChain.turbine_id == turbine_id,
            RiskChain.status.in_([
                RiskChainStatus.ACTIVE,
                RiskChainStatus.ESCALATING,
                RiskChainStatus.STABILIZED
            ]),
            RiskChain.last_updated_at >= cutoff_time
        ).order_by(RiskChain.last_updated_at.desc()).first()
        return chain

    @staticmethod
    def _create_new_chain(
        db: Session,
        alert: Alert,
        turbine: Turbine
    ) -> RiskChainResult:
        chain_code = RiskChainEngine._generate_chain_code(turbine.turbine_code)

        risk_chain = RiskChain(
            turbine_id=turbine.id,
            chain_code=chain_code,
            status=RiskChainStatus.ACTIVE,
            current_phase=alert.alert_type,
            current_level=alert.alert_level,
            started_at=alert.triggered_at,
            last_updated_at=alert.triggered_at,
            total_alerts=1,
            escalation_count=0,
            overall_suggestion=RiskChainEngine._build_overall_suggestion(
                [alert.alert_type], alert.alert_level
            )
        )
        db.add(risk_chain)
        db.flush()

        phase = RiskPhase(
            risk_chain_id=risk_chain.id,
            phase_index=0,
            alert_type=alert.alert_type,
            alert_level=alert.alert_level,
            started_at=alert.triggered_at,
            trigger_reason=alert.trigger_reason,
            phase_suggestion=alert.suggestion,
            is_escalation=0
        )
        db.add(phase)
        db.flush()

        alert.risk_chain_id = risk_chain.id

        return RiskChainResult(
            risk_chain=risk_chain,
            is_new_chain=True,
            is_escalation=False,
            new_phase=phase
        )

    @staticmethod
    def _update_existing_chain(
        db: Session,
        chain: RiskChain,
        alert: Alert
    ) -> RiskChainResult:
        is_escalation = is_risk_escalation(chain.current_phase, alert.alert_type)
        is_level_up = get_level_rank(alert.alert_level) > get_level_rank(chain.current_level)

        chain.last_updated_at = alert.triggered_at
        chain.total_alerts += 1

        new_phase = None

        if is_escalation:
            chain.escalation_count += 1
            chain.status = RiskChainStatus.ESCALATING
            chain.current_phase = alert.alert_type
            chain.current_level = alert.alert_level

            if chain.phases:
                last_phase = chain.phases[-1]
                last_phase.ended_at = alert.triggered_at

            new_phase_index = len(chain.phases)
            new_phase = RiskPhase(
                risk_chain_id=chain.id,
                phase_index=new_phase_index,
                alert_type=alert.alert_type,
                alert_level=alert.alert_level,
                started_at=alert.triggered_at,
                trigger_reason=alert.trigger_reason,
                phase_suggestion=alert.suggestion,
                is_escalation=1
            )
            db.add(new_phase)
            db.flush()
            db.refresh(chain)

            phase_types = [p.alert_type for p in chain.phases]
            chain.overall_suggestion = RiskChainEngine._build_overall_suggestion(
                phase_types, alert.alert_level
            )
        elif is_level_up:
            chain.current_level = alert.alert_level

            if chain.phases:
                last_phase = chain.phases[-1]
                if last_phase.alert_type == alert.alert_type:
                    last_phase.alert_level = alert.alert_level
                    last_phase.phase_suggestion = alert.suggestion
                    last_phase.trigger_reason = alert.trigger_reason

            phase_types = [p.alert_type for p in chain.phases]
            chain.overall_suggestion = RiskChainEngine._build_overall_suggestion(
                phase_types, alert.alert_level
            )
        else:
            if chain.status == RiskChainStatus.ESCALATING:
                chain.status = RiskChainStatus.ACTIVE

            if chain.phases:
                last_phase = chain.phases[-1]
                if last_phase.alert_type == alert.alert_type:
                    if get_level_rank(alert.alert_level) > get_level_rank(last_phase.alert_level):
                        last_phase.alert_level = alert.alert_level
                        last_phase.phase_suggestion = alert.suggestion
                    last_phase.trigger_reason = alert.trigger_reason

        alert.risk_chain_id = chain.id

        return RiskChainResult(
            risk_chain=chain,
            is_new_chain=False,
            is_escalation=is_escalation,
            new_phase=new_phase
        )

    @staticmethod
    def _generate_chain_code(turbine_code: str) -> str:
        short_uuid = uuid.uuid4().hex[:8].upper()
        return f"RC-{turbine_code}-{short_uuid}"

    @staticmethod
    def _build_overall_suggestion(
        phase_types: List[AlertType],
        current_level: AlertLevel
    ) -> str:
        if not phase_types:
            return ""

        type_names = [t.value for t in phase_types]
        evolution_path = " → ".join(type_names)

        level_suggestions = {
            AlertLevel.LOW: "持续监控，关注各参数变化趋势",
            AlertLevel.MEDIUM: "加强巡检频次，重点关注演化路径上的相关系统",
            AlertLevel.HIGH: "建议安排现场检查，评估风险演化趋势，必要时降载运行",
            AlertLevel.CRITICAL: "立即安排专业人员现场排查，考虑停机检查防止设备损坏"
        }

        base_suggestion = level_suggestions.get(current_level, "")
        return f"风险演化路径：{evolution_path}。处置建议：{base_suggestion}"

    @staticmethod
    def check_and_close_stale_chains(db: Session) -> int:
        cutoff_time = datetime.utcnow() - timedelta(hours=RISK_CHAIN_TIMEOUT_HOURS)
        stale_chains = db.query(RiskChain).filter(
            RiskChain.status.in_([
                RiskChainStatus.ACTIVE,
                RiskChainStatus.ESCALATING,
                RiskChainStatus.STABILIZED
            ]),
            RiskChain.last_updated_at < cutoff_time
        ).all()

        for chain in stale_chains:
            chain.status = RiskChainStatus.CLOSED
            chain.closed_at = datetime.utcnow()
            chain.close_condition = f"连续{RISK_CHAIN_TIMEOUT_HOURS}小时无新告警，自动关闭"

            if chain.phases:
                last_phase = chain.phases[-1]
                if not last_phase.ended_at:
                    last_phase.ended_at = chain.last_updated_at

        return len(stale_chains)

    @staticmethod
    def get_close_conditions() -> List[str]:
        return [
            "连续24小时无新告警，自动关闭",
            "人工确认风险已消除",
            "检修完成恢复正常运行",
            "误报标记关闭"
        ]
