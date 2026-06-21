from typing import List, Callable, Optional, Any
from dataclasses import dataclass, field

from app.models import AlertType, AlertLevel, OperatingData, Turbine
from app.alert_rules.statistics import get_level_rank


@dataclass
class RuleContext:
    data: OperatingData
    turbine: Turbine
    extra: dict = field(default_factory=dict)


@dataclass
class AlertCondition:
    name: str
    check: Callable[[RuleContext], bool]
    level: AlertLevel
    reason_template: str
    format_args: Callable[[RuleContext], dict] = lambda ctx: {}
    only_if: Optional[Callable[[RuleContext], bool]] = None

    def should_check(self, ctx: RuleContext) -> bool:
        if self.only_if is None:
            return True
        return self.only_if(ctx)

    def evaluate(self, ctx: RuleContext) -> Optional[tuple]:
        if not self.should_check(ctx):
            return None
        if self.check(ctx):
            reason = self.reason_template.format(**self.format_args(ctx))
            return (self.level, reason)
        return None


@dataclass
class AlertRule:
    alert_type: AlertType
    conditions: List[AlertCondition]
    preprocess: Optional[Callable[[RuleContext], None]] = None
    postprocess: Optional[Callable[[RuleContext, AlertLevel, List[str]], AlertLevel]] = None
    suggestion_builder: Optional[Callable[[RuleContext, AlertLevel], str]] = None

    def evaluate(self, ctx: RuleContext) -> "AlertRuleResult":
        if self.preprocess:
            self.preprocess(ctx)

        triggered_level, reasons = evaluate_conditions(self.conditions, ctx)

        if not triggered_level:
            return AlertRuleResult(
                alert_type=self.alert_type,
                alert_level=AlertLevel.LOW,
                trigger_reason="",
                suggestion="",
                triggered=False,
            )

        if self.postprocess:
            triggered_level = self.postprocess(ctx, triggered_level, reasons)

        reason_str = "；".join(reasons)

        if self.suggestion_builder:
            suggestion = self.suggestion_builder(ctx, triggered_level)
        else:
            suggestion = ""

        return AlertRuleResult(
            alert_type=self.alert_type,
            alert_level=triggered_level,
            trigger_reason=reason_str,
            suggestion=suggestion,
            triggered=True,
        )


@dataclass
class AlertRuleResult:
    alert_type: AlertType
    alert_level: AlertLevel
    trigger_reason: str
    suggestion: str
    triggered: bool


def evaluate_conditions(
    conditions: List[AlertCondition], ctx: RuleContext
) -> tuple[Optional[AlertLevel], List[str]]:
    triggered_level: Optional[AlertLevel] = None
    reasons: List[str] = []

    for condition in conditions:
        result = condition.evaluate(ctx)
        if result is not None:
            level, reason = result
            reasons.append(reason)
            if triggered_level is None or get_level_rank(level) > get_level_rank(triggered_level):
                triggered_level = level

    return triggered_level, reasons


def upgrade_level(current: AlertLevel, target: AlertLevel) -> AlertLevel:
    if get_level_rank(target) > get_level_rank(current):
        return target
    return current
