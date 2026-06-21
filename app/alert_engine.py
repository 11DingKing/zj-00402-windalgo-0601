from typing import List

from app.models import OperatingData, Turbine
from app.alert_rules import (
    AlertRuleResult,
    RuleContext,
    STALL_RULE,
    VORTEX_RULE,
    TEMPERATURE_RULE,
    POWER_RULE,
    ALL_RULES,
)


class AlertRuleEngine:
    STANDARD_AIR_DENSITY = 1.225
    HIGH_ALTITUDE_THRESHOLD = 0.95

    @staticmethod
    def check_stall_tendency(
        data: OperatingData, turbine: Turbine
    ) -> AlertRuleResult:
        ctx = RuleContext(data=data, turbine=turbine)
        return STALL_RULE.evaluate(ctx)

    @staticmethod
    def check_vortex_vibration(
        data: OperatingData, turbine: Turbine
    ) -> AlertRuleResult:
        ctx = RuleContext(data=data, turbine=turbine)
        return VORTEX_RULE.evaluate(ctx)

    @staticmethod
    def check_temperature_anomaly(
        data: OperatingData, turbine: Turbine
    ) -> AlertRuleResult:
        ctx = RuleContext(data=data, turbine=turbine)
        return TEMPERATURE_RULE.evaluate(ctx)

    @staticmethod
    def check_power_deviation(
        data: OperatingData, turbine: Turbine
    ) -> AlertRuleResult:
        ctx = RuleContext(data=data, turbine=turbine)
        return POWER_RULE.evaluate(ctx)

    @staticmethod
    def analyze(
        data: OperatingData, turbine: Turbine
    ) -> List[AlertRuleResult]:
        ctx = RuleContext(data=data, turbine=turbine)
        results = []
        for rule in ALL_RULES:
            result = rule.evaluate(ctx)
            if result.triggered:
                results.append(result)
        return results
