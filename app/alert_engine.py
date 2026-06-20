from typing import List, Tuple, Optional
from dataclasses import dataclass

from app.models import AlertType, AlertLevel, OperatingData, Turbine


@dataclass
class AlertRuleResult:
    alert_type: AlertType
    alert_level: AlertLevel
    trigger_reason: str
    suggestion: str
    triggered: bool


class AlertRuleEngine:
    STANDARD_AIR_DENSITY = 1.225
    HIGH_ALTITUDE_THRESHOLD = 0.95

    @staticmethod
    def check_stall_tendency(
        data: OperatingData, turbine: Turbine
    ) -> AlertRuleResult:
        triggered = False
        level = AlertLevel.LOW
        reasons = []

        density_ratio = data.air_density / AlertRuleEngine.STANDARD_AIR_DENSITY
        is_high_altitude = data.air_density < AlertRuleEngine.HIGH_ALTITUDE_THRESHOLD

        if is_high_altitude:
            density_correction = (data.air_density / AlertRuleEngine.STANDARD_AIR_DENSITY - 1) * 100
            effective_power_deviation = data.power_deviation - density_correction
        else:
            effective_power_deviation = data.power_deviation

        if data.rotor_speed_std and data.rotor_speed_std > 0.8:
            reasons.append(f"叶轮转速波动过大（标准差{data.rotor_speed_std:.2f}rpm）")
            triggered = True
            level = AlertLevel.MEDIUM

        if data.wind_speed > 8.0 and effective_power_deviation < -15:
            reasons.append(f"风速{data.wind_speed:.1f}m/s时功率负偏{effective_power_deviation:.1f}%{'（高海拔修正后）' if is_high_altitude else ''}")
            triggered = True
            level = AlertLevel.HIGH

        blade_loads = [data.blade_load_1, data.blade_load_2, data.blade_load_3]
        load_imbalance = max(blade_loads) - min(blade_loads)
        if load_imbalance > 30:
            reasons.append(f"三叶片载荷差过大（{load_imbalance:.1f}kN）")
            triggered = True
            level = AlertLevel.HIGH if level.value < AlertLevel.HIGH.value else level

        if is_high_altitude and data.wind_speed > 10.0 and data.rotor_speed_std and data.rotor_speed_std > 1.0:
            reasons.append(f"高海拔（空气密度{data.air_density:.3f}kg/m³）大风速下转速波动异常")
            triggered = True
            level = AlertLevel.CRITICAL

        if not triggered:
            return AlertRuleResult(
                alert_type=AlertType.STALL_TENDENCY,
                alert_level=AlertLevel.LOW,
                trigger_reason="",
                suggestion="",
                triggered=False
            )

        reason_str = "；".join(reasons)
        suggestion = AlertRuleEngine._get_stall_suggestion(level, is_high_altitude)

        return AlertRuleResult(
            alert_type=AlertType.STALL_TENDENCY,
            alert_level=level,
            trigger_reason=reason_str,
            suggestion=suggestion,
            triggered=True
        )

    @staticmethod
    def check_vortex_vibration(
        data: OperatingData, turbine: Turbine
    ) -> AlertRuleResult:
        triggered = False
        level = AlertLevel.LOW
        reasons = []

        vibration_magnitude = (data.tower_vibration_x ** 2 + data.tower_vibration_y ** 2) ** 0.5

        if vibration_magnitude > 15.0:
            reasons.append(f"塔筒合成振动超过阈值（{vibration_magnitude:.2f}mm/s）")
            triggered = True
            level = AlertLevel.HIGH
        elif vibration_magnitude > 10.0:
            reasons.append(f"塔筒合成振动偏高（{vibration_magnitude:.2f}mm/s）")
            triggered = True
            level = AlertLevel.MEDIUM

        if data.tower_vibration_z and data.tower_vibration_z > 8.0:
            reasons.append(f"塔筒轴向振动异常（{data.tower_vibration_z:.2f}mm/s）")
            triggered = True
            level = AlertLevel.HIGH if level.value < AlertLevel.HIGH.value else level

        if 4.0 < data.wind_speed < 10.0 and vibration_magnitude > 8.0:
            reasons.append(f"风速{data.wind_speed:.1f}m/s（涡激共振区间）下振动偏高")
            triggered = True
            level = AlertLevel.HIGH if level.value < AlertLevel.HIGH.value else level

        if data.blade_load_std and data.blade_load_std > 20:
            reasons.append(f"叶片载荷波动异常（标准差{data.blade_load_std:.1f}kN）")
            triggered = True

        if not triggered:
            return AlertRuleResult(
                alert_type=AlertType.VORTEX_VIBRATION,
                alert_level=AlertLevel.LOW,
                trigger_reason="",
                suggestion="",
                triggered=False
            )

        reason_str = "；".join(reasons)
        suggestion = AlertRuleEngine._get_vortex_suggestion(level, vibration_magnitude)

        return AlertRuleResult(
            alert_type=AlertType.VORTEX_VIBRATION,
            alert_level=level,
            trigger_reason=reason_str,
            suggestion=suggestion,
            triggered=True
        )

    @staticmethod
    def check_temperature_anomaly(
        data: OperatingData, turbine: Turbine
    ) -> AlertRuleResult:
        triggered = False
        level = AlertLevel.LOW
        reasons = []

        if data.nacelle_temperature > 65:
            reasons.append(f"机舱温度过高（{data.nacelle_temperature:.1f}℃）")
            triggered = True
            level = AlertLevel.HIGH
        elif data.nacelle_temperature > 55:
            reasons.append(f"机舱温度偏高（{data.nacelle_temperature:.1f}℃）")
            triggered = True
            level = AlertLevel.MEDIUM

        if data.gearbox_temperature:
            if data.gearbox_temperature > 80:
                reasons.append(f"齿轮箱温度过高（{data.gearbox_temperature:.1f}℃）")
                triggered = True
                level = AlertLevel.CRITICAL
            elif data.gearbox_temperature > 70:
                reasons.append(f"齿轮箱温度偏高（{data.gearbox_temperature:.1f}℃）")
                triggered = True
                level = AlertLevel.HIGH if level.value < AlertLevel.HIGH.value else level

        if data.generator_temperature:
            if data.generator_temperature > 95:
                reasons.append(f"发电机温度过高（{data.generator_temperature:.1f}℃）")
                triggered = True
                level = AlertLevel.CRITICAL
            elif data.generator_temperature > 85:
                reasons.append(f"发电机温度偏高（{data.generator_temperature:.1f}℃）")
                triggered = True
                level = AlertLevel.HIGH if level.value < AlertLevel.HIGH.value else level

        if data.wind_speed < 6.0 and data.nacelle_temperature > 50:
            reasons.append(f"低风速（{data.wind_speed:.1f}m/s）下机舱温度异常偏高")
            triggered = True
            level = AlertLevel.MEDIUM if level.value < AlertLevel.MEDIUM.value else level

        if not triggered:
            return AlertRuleResult(
                alert_type=AlertType.TEMPERATURE_ANOMALY,
                alert_level=AlertLevel.LOW,
                trigger_reason="",
                suggestion="",
                triggered=False
            )

        reason_str = "；".join(reasons)
        suggestion = AlertRuleEngine._get_temperature_suggestion(level)

        return AlertRuleResult(
            alert_type=AlertType.TEMPERATURE_ANOMALY,
            alert_level=level,
            trigger_reason=reason_str,
            suggestion=suggestion,
            triggered=True
        )

    @staticmethod
    def check_power_deviation(
        data: OperatingData, turbine: Turbine
    ) -> AlertRuleResult:
        triggered = False
        level = AlertLevel.LOW
        reasons = []

        is_high_altitude = data.air_density < AlertRuleEngine.HIGH_ALTITUDE_THRESHOLD

        if is_high_altitude:
            density_correction = (data.air_density / AlertRuleEngine.STANDARD_AIR_DENSITY - 1) * 100
            corrected_deviation = data.power_deviation - density_correction
            abs_corrected = abs(corrected_deviation)

            if abs_corrected > 30:
                reasons.append(f"高海拔修正后功率严重偏离（{corrected_deviation:+.1f}%）")
                triggered = True
                level = AlertLevel.CRITICAL
            elif abs_corrected > 20:
                reasons.append(f"高海拔修正后功率大幅偏离（{corrected_deviation:+.1f}%）")
                triggered = True
                level = AlertLevel.HIGH
            elif abs_corrected > 10:
                reasons.append(f"高海拔修正后功率偏离（{corrected_deviation:+.1f}%）")
                triggered = True
                level = AlertLevel.MEDIUM
            elif abs_corrected > 5:
                reasons.append(f"高海拔修正后功率轻度偏离（{corrected_deviation:+.1f}%）")
        else:
            abs_deviation = abs(data.power_deviation)

            if abs_deviation > 30:
                reasons.append(f"功率曲线严重偏离（{data.power_deviation:+.1f}%）")
                triggered = True
                level = AlertLevel.CRITICAL
            elif abs_deviation > 20:
                reasons.append(f"功率曲线大幅偏离（{data.power_deviation:+.1f}%）")
                triggered = True
                level = AlertLevel.HIGH
            elif abs_deviation > 10:
                reasons.append(f"功率曲线偏离（{data.power_deviation:+.1f}%）")
                triggered = True
                level = AlertLevel.MEDIUM

        if data.power_deviation > 15 and data.wind_speed > 12:
            reasons.append(f"大风速下功率正偏异常，可能存在过发风险")
            triggered = True
            level = AlertLevel.HIGH if level.value < AlertLevel.HIGH.value else level

        if is_high_altitude:
            density_correction = (data.air_density / AlertRuleEngine.STANDARD_AIR_DENSITY - 1) * 100
            corrected_deviation = data.power_deviation - density_correction
            if corrected_deviation < -15 and data.wind_speed > 6:
                reasons.append(f"高海拔修正后中风速以上功率负偏严重，发电效率偏低")
                triggered = True
                level = AlertLevel.HIGH if level.value < AlertLevel.HIGH.value else level
        else:
            if data.power_deviation < -20 and data.wind_speed > 6:
                reasons.append(f"中风速以上功率负偏严重，发电效率偏低")
                triggered = True
                level = AlertLevel.HIGH if level.value < AlertLevel.HIGH.value else level

        if not triggered:
            return AlertRuleResult(
                alert_type=AlertType.POWER_DEVIATION,
                alert_level=AlertLevel.LOW,
                trigger_reason="",
                suggestion="",
                triggered=False
            )

        reason_str = "；".join(reasons)
        if is_high_altitude:
            density_correction = (data.air_density / AlertRuleEngine.STANDARD_AIR_DENSITY - 1) * 100
            corrected_deviation = data.power_deviation - density_correction
            effective_deviation = corrected_deviation
        else:
            effective_deviation = data.power_deviation
        suggestion = AlertRuleEngine._get_power_suggestion(level, effective_deviation)

        return AlertRuleResult(
            alert_type=AlertType.POWER_DEVIATION,
            alert_level=level,
            trigger_reason=reason_str,
            suggestion=suggestion,
            triggered=True
        )

    @staticmethod
    def analyze(
        data: OperatingData, turbine: Turbine
    ) -> List[AlertRuleResult]:
        results = []

        stall_result = AlertRuleEngine.check_stall_tendency(data, turbine)
        if stall_result.triggered:
            results.append(stall_result)

        vortex_result = AlertRuleEngine.check_vortex_vibration(data, turbine)
        if vortex_result.triggered:
            results.append(vortex_result)

        temp_result = AlertRuleEngine.check_temperature_anomaly(data, turbine)
        if temp_result.triggered:
            results.append(temp_result)

        power_result = AlertRuleEngine.check_power_deviation(data, turbine)
        if power_result.triggered:
            results.append(power_result)

        return results

    @staticmethod
    def _get_stall_suggestion(level: AlertLevel, is_high_altitude: bool) -> str:
        base_suggestions = {
            AlertLevel.LOW: "持续监控叶轮转速和功率输出",
            AlertLevel.MEDIUM: "检查变桨系统响应，监控叶片气动性能",
            AlertLevel.HIGH: "建议降载运行，检查叶片前缘污染和翼型状态",
            AlertLevel.CRITICAL: "立即降载至安全运行区间，停机检查叶片状态和变桨系统校准"
        }
        suggestion = base_suggestions.get(level, "")
        if is_high_altitude and level in [AlertLevel.HIGH, AlertLevel.CRITICAL]:
            suggestion += "（高海拔场区需特别注意低空气密度对气动性能的影响）"
        return suggestion

    @staticmethod
    def _get_vortex_suggestion(level: AlertLevel, vibration: float) -> str:
        suggestions = {
            AlertLevel.LOW: "持续监控塔筒振动趋势",
            AlertLevel.MEDIUM: "检查塔筒阻尼系统，评估涡激振动风险",
            AlertLevel.HIGH: "建议调整运行策略避开涡激共振风速区间，检查塔筒连接螺栓",
            AlertLevel.CRITICAL: "立即停机检查塔筒结构完整性和基础稳定性"
        }
        return suggestions.get(level, "")

    @staticmethod
    def _get_temperature_suggestion(level: AlertLevel) -> str:
        suggestions = {
            AlertLevel.LOW: "检查冷却系统运行状态",
            AlertLevel.MEDIUM: "检查温控阀和冷却风扇，清理散热片",
            AlertLevel.HIGH: "建议降载运行，检查润滑油油位和油质",
            AlertLevel.CRITICAL: "立即停机，检查齿轮箱/发电机是否存在局部过热和轴承故障"
        }
        return suggestions.get(level, "")

    @staticmethod
    def _get_power_suggestion(level: AlertLevel, deviation: float) -> str:
        if deviation > 0:
            direction = "正"
            check_item = "变桨校准、风速仪准确性，防止过发损坏设备"
        else:
            direction = "负"
            check_item = "叶片翼型状态、偏航对风精度、传动系统效率"

        suggestions = {
            AlertLevel.LOW: f"持续监控功率{direction}偏趋势",
            AlertLevel.MEDIUM: f"检查{check_item}",
            AlertLevel.HIGH: f"建议停机检查{check_item}，必要时进行功率曲线复算",
            AlertLevel.CRITICAL: f"立即停机全面检查{check_item}，重新进行叶片标定"
        }
        return suggestions.get(level, "")
