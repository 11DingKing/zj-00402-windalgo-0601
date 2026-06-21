from app.models import AlertType, AlertLevel
from app.alert_rules.base import AlertCondition, AlertRule, RuleContext
from app.alert_rules.suggestions import (
    build_stall_suggestion,
    build_vortex_suggestion,
    build_temperature_suggestion,
    build_power_suggestion,
)


STANDARD_AIR_DENSITY = 1.225
HIGH_ALTITUDE_THRESHOLD = 0.95


def _stall_preprocess(ctx: RuleContext) -> None:
    data = ctx.data
    is_high_altitude = data.air_density < HIGH_ALTITUDE_THRESHOLD
    density_correction = (data.air_density / STANDARD_AIR_DENSITY - 1) * 100
    effective_power_deviation = data.power_deviation - density_correction if is_high_altitude else data.power_deviation
    ctx.extra["is_high_altitude"] = is_high_altitude
    ctx.extra["effective_power_deviation"] = effective_power_deviation


STALL_CONDITIONS = [
    AlertCondition(
        name="rotor_speed_fluctuation",
        check=lambda ctx: ctx.data.rotor_speed_std is not None and ctx.data.rotor_speed_std > 0.8,
        level=AlertLevel.MEDIUM,
        reason_template="叶轮转速波动过大（标准差{std:.2f}rpm）",
        format_args=lambda ctx: {"std": ctx.data.rotor_speed_std or 0},
    ),
    AlertCondition(
        name="wind_speed_power_deviation",
        check=lambda ctx: ctx.data.wind_speed > 8.0 and ctx.extra["effective_power_deviation"] < -15,
        level=AlertLevel.HIGH,
        reason_template="风速{wind_speed:.1f}m/s时功率负偏{deviation:.1f}%{suffix}",
        format_args=lambda ctx: {
            "wind_speed": ctx.data.wind_speed,
            "deviation": ctx.extra["effective_power_deviation"],
            "suffix": "（高海拔修正后）" if ctx.extra["is_high_altitude"] else "",
        },
    ),
    AlertCondition(
        name="blade_load_imbalance",
        check=lambda ctx: (max([ctx.data.blade_load_1, ctx.data.blade_load_2, ctx.data.blade_load_3])
                          - min([ctx.data.blade_load_1, ctx.data.blade_load_2, ctx.data.blade_load_3])) > 30,
        level=AlertLevel.HIGH,
        reason_template="三叶片载荷差过大（{imbalance:.1f}kN）",
        format_args=lambda ctx: {
            "imbalance": max([ctx.data.blade_load_1, ctx.data.blade_load_2, ctx.data.blade_load_3])
                        - min([ctx.data.blade_load_1, ctx.data.blade_load_2, ctx.data.blade_load_3]),
        },
    ),
    AlertCondition(
        name="high_altitude_wind_fluctuation",
        check=lambda ctx: (ctx.extra["is_high_altitude"]
                          and ctx.data.wind_speed > 10.0
                          and ctx.data.rotor_speed_std is not None
                          and ctx.data.rotor_speed_std > 1.0),
        level=AlertLevel.CRITICAL,
        reason_template="高海拔（空气密度{density:.3f}kg/m³）大风速下转速波动异常",
        format_args=lambda ctx: {"density": ctx.data.air_density},
    ),
]

STALL_RULE = AlertRule(
    alert_type=AlertType.STALL_TENDENCY,
    conditions=STALL_CONDITIONS,
    preprocess=_stall_preprocess,
    suggestion_builder=build_stall_suggestion,
)


def _vortex_preprocess(ctx: RuleContext) -> None:
    data = ctx.data
    vibration_magnitude = (data.tower_vibration_x ** 2 + data.tower_vibration_y ** 2) ** 0.5
    ctx.extra["vibration_magnitude"] = vibration_magnitude


VORTEX_CONDITIONS = [
    AlertCondition(
        name="high_vibration",
        check=lambda ctx: ctx.extra["vibration_magnitude"] > 15.0,
        level=AlertLevel.HIGH,
        reason_template="塔筒合成振动超过阈值（{vib:.2f}mm/s）",
        format_args=lambda ctx: {"vib": ctx.extra["vibration_magnitude"]},
    ),
    AlertCondition(
        name="moderate_vibration",
        check=lambda ctx: ctx.extra["vibration_magnitude"] > 10.0,
        level=AlertLevel.MEDIUM,
        reason_template="塔筒合成振动偏高（{vib:.2f}mm/s）",
        format_args=lambda ctx: {"vib": ctx.extra["vibration_magnitude"]},
    ),
    AlertCondition(
        name="axial_vibration",
        check=lambda ctx: ctx.data.tower_vibration_z is not None and ctx.data.tower_vibration_z > 8.0,
        level=AlertLevel.HIGH,
        reason_template="塔筒轴向振动异常（{vib:.2f}mm/s）",
        format_args=lambda ctx: {"vib": ctx.data.tower_vibration_z or 0},
    ),
    AlertCondition(
        name="vortex_resonance_range",
        check=lambda ctx: 4.0 < ctx.data.wind_speed < 10.0 and ctx.extra["vibration_magnitude"] > 8.0,
        level=AlertLevel.HIGH,
        reason_template="风速{wind_speed:.1f}m/s（涡激共振区间）下振动偏高",
        format_args=lambda ctx: {"wind_speed": ctx.data.wind_speed},
    ),
    AlertCondition(
        name="blade_load_fluctuation",
        check=lambda ctx: ctx.data.blade_load_std is not None and ctx.data.blade_load_std > 20,
        level=AlertLevel.LOW,
        reason_template="叶片载荷波动异常（标准差{std:.1f}kN）",
        format_args=lambda ctx: {"std": ctx.data.blade_load_std or 0},
    ),
]

VORTEX_RULE = AlertRule(
    alert_type=AlertType.VORTEX_VIBRATION,
    conditions=VORTEX_CONDITIONS,
    preprocess=_vortex_preprocess,
    suggestion_builder=build_vortex_suggestion,
)


TEMPERATURE_CONDITIONS = [
    AlertCondition(
        name="nacelle_temp_high",
        check=lambda ctx: ctx.data.nacelle_temperature > 65,
        level=AlertLevel.HIGH,
        reason_template="机舱温度过高（{temp:.1f}℃）",
        format_args=lambda ctx: {"temp": ctx.data.nacelle_temperature},
    ),
    AlertCondition(
        name="nacelle_temp_moderate",
        check=lambda ctx: ctx.data.nacelle_temperature > 55,
        level=AlertLevel.MEDIUM,
        reason_template="机舱温度偏高（{temp:.1f}℃）",
        format_args=lambda ctx: {"temp": ctx.data.nacelle_temperature},
    ),
    AlertCondition(
        name="gearbox_temp_critical",
        check=lambda ctx: ctx.data.gearbox_temperature is not None and ctx.data.gearbox_temperature > 80,
        level=AlertLevel.CRITICAL,
        reason_template="齿轮箱温度过高（{temp:.1f}℃）",
        format_args=lambda ctx: {"temp": ctx.data.gearbox_temperature or 0},
    ),
    AlertCondition(
        name="gearbox_temp_high",
        check=lambda ctx: ctx.data.gearbox_temperature is not None and ctx.data.gearbox_temperature > 70,
        level=AlertLevel.HIGH,
        reason_template="齿轮箱温度偏高（{temp:.1f}℃）",
        format_args=lambda ctx: {"temp": ctx.data.gearbox_temperature or 0},
    ),
    AlertCondition(
        name="generator_temp_critical",
        check=lambda ctx: ctx.data.generator_temperature is not None and ctx.data.generator_temperature > 95,
        level=AlertLevel.CRITICAL,
        reason_template="发电机温度过高（{temp:.1f}℃）",
        format_args=lambda ctx: {"temp": ctx.data.generator_temperature or 0},
    ),
    AlertCondition(
        name="generator_temp_high",
        check=lambda ctx: ctx.data.generator_temperature is not None and ctx.data.generator_temperature > 85,
        level=AlertLevel.HIGH,
        reason_template="发电机温度偏高（{temp:.1f}℃）",
        format_args=lambda ctx: {"temp": ctx.data.generator_temperature or 0},
    ),
    AlertCondition(
        name="low_wind_nacelle_temp",
        check=lambda ctx: ctx.data.wind_speed < 6.0 and ctx.data.nacelle_temperature > 50,
        level=AlertLevel.MEDIUM,
        reason_template="低风速（{wind_speed:.1f}m/s）下机舱温度异常偏高",
        format_args=lambda ctx: {"wind_speed": ctx.data.wind_speed},
    ),
]

TEMPERATURE_RULE = AlertRule(
    alert_type=AlertType.TEMPERATURE_ANOMALY,
    conditions=TEMPERATURE_CONDITIONS,
    suggestion_builder=build_temperature_suggestion,
)


def _power_preprocess(ctx: RuleContext) -> None:
    data = ctx.data
    is_high_altitude = data.air_density < HIGH_ALTITUDE_THRESHOLD
    density_correction = (data.air_density / STANDARD_AIR_DENSITY - 1) * 100
    corrected_deviation = data.power_deviation - density_correction
    effective_deviation = corrected_deviation if is_high_altitude else data.power_deviation
    ctx.extra["is_high_altitude"] = is_high_altitude
    ctx.extra["corrected_deviation"] = corrected_deviation
    ctx.extra["effective_deviation"] = effective_deviation
    ctx.extra["density_correction"] = density_correction


POWER_CONDITIONS = [
    AlertCondition(
        name="high_altitude_critical_deviation",
        only_if=lambda ctx: ctx.extra["is_high_altitude"],
        check=lambda ctx: abs(ctx.extra["corrected_deviation"]) > 30,
        level=AlertLevel.CRITICAL,
        reason_template="高海拔修正后功率严重偏离（{deviation:+.1f}%）",
        format_args=lambda ctx: {"deviation": ctx.extra["corrected_deviation"]},
    ),
    AlertCondition(
        name="high_altitude_high_deviation",
        only_if=lambda ctx: ctx.extra["is_high_altitude"],
        check=lambda ctx: abs(ctx.extra["corrected_deviation"]) > 20,
        level=AlertLevel.HIGH,
        reason_template="高海拔修正后功率大幅偏离（{deviation:+.1f}%）",
        format_args=lambda ctx: {"deviation": ctx.extra["corrected_deviation"]},
    ),
    AlertCondition(
        name="high_altitude_medium_deviation",
        only_if=lambda ctx: ctx.extra["is_high_altitude"],
        check=lambda ctx: abs(ctx.extra["corrected_deviation"]) > 10,
        level=AlertLevel.MEDIUM,
        reason_template="高海拔修正后功率偏离（{deviation:+.1f}%）",
        format_args=lambda ctx: {"deviation": ctx.extra["corrected_deviation"]},
    ),
    AlertCondition(
        name="high_altitude_mild_deviation",
        only_if=lambda ctx: ctx.extra["is_high_altitude"],
        check=lambda ctx: abs(ctx.extra["corrected_deviation"]) > 5,
        level=AlertLevel.LOW,
        reason_template="高海拔修正后功率轻度偏离（{deviation:+.1f}%）",
        format_args=lambda ctx: {"deviation": ctx.extra["corrected_deviation"]},
    ),
    AlertCondition(
        name="normal_critical_deviation",
        only_if=lambda ctx: not ctx.extra["is_high_altitude"],
        check=lambda ctx: abs(ctx.data.power_deviation) > 30,
        level=AlertLevel.CRITICAL,
        reason_template="功率曲线严重偏离（{deviation:+.1f}%）",
        format_args=lambda ctx: {"deviation": ctx.data.power_deviation},
    ),
    AlertCondition(
        name="normal_high_deviation",
        only_if=lambda ctx: not ctx.extra["is_high_altitude"],
        check=lambda ctx: abs(ctx.data.power_deviation) > 20,
        level=AlertLevel.HIGH,
        reason_template="功率曲线大幅偏离（{deviation:+.1f}%）",
        format_args=lambda ctx: {"deviation": ctx.data.power_deviation},
    ),
    AlertCondition(
        name="normal_medium_deviation",
        only_if=lambda ctx: not ctx.extra["is_high_altitude"],
        check=lambda ctx: abs(ctx.data.power_deviation) > 10,
        level=AlertLevel.MEDIUM,
        reason_template="功率曲线偏离（{deviation:+.1f}%）",
        format_args=lambda ctx: {"deviation": ctx.data.power_deviation},
    ),
    AlertCondition(
        name="high_wind_positive_deviation",
        check=lambda ctx: ctx.data.power_deviation > 15 and ctx.data.wind_speed > 12,
        level=AlertLevel.HIGH,
        reason_template="大风速下功率正偏异常，可能存在过发风险",
        format_args=lambda ctx: {},
    ),
    AlertCondition(
        name="high_altitude_negative_deviation",
        only_if=lambda ctx: ctx.extra["is_high_altitude"],
        check=lambda ctx: ctx.extra["corrected_deviation"] < -15 and ctx.data.wind_speed > 6,
        level=AlertLevel.HIGH,
        reason_template="高海拔修正后中风速以上功率负偏严重，发电效率偏低",
        format_args=lambda ctx: {},
    ),
    AlertCondition(
        name="normal_negative_deviation",
        only_if=lambda ctx: not ctx.extra["is_high_altitude"],
        check=lambda ctx: ctx.data.power_deviation < -20 and ctx.data.wind_speed > 6,
        level=AlertLevel.HIGH,
        reason_template="中风速以上功率负偏严重，发电效率偏低",
        format_args=lambda ctx: {},
    ),
]

POWER_RULE = AlertRule(
    alert_type=AlertType.POWER_DEVIATION,
    conditions=POWER_CONDITIONS,
    preprocess=_power_preprocess,
    suggestion_builder=build_power_suggestion,
)


ALL_RULES = [STALL_RULE, VORTEX_RULE, TEMPERATURE_RULE, POWER_RULE]
