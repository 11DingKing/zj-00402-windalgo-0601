from typing import Callable, Dict
from app.models import AlertType, AlertLevel


SUGGESTION_TEMPLATES: Dict[AlertType, Dict[AlertLevel, str]] = {
    AlertType.STALL_TENDENCY: {
        AlertLevel.LOW: "持续监控叶轮转速和功率输出",
        AlertLevel.MEDIUM: "检查变桨系统响应，监控叶片气动性能",
        AlertLevel.HIGH: "建议降载运行，检查叶片前缘污染和翼型状态",
        AlertLevel.CRITICAL: "立即降载至安全运行区间，停机检查叶片状态和变桨系统校准",
    },
    AlertType.VORTEX_VIBRATION: {
        AlertLevel.LOW: "持续监控塔筒振动趋势",
        AlertLevel.MEDIUM: "检查塔筒阻尼系统，评估涡激振动风险",
        AlertLevel.HIGH: "建议调整运行策略避开涡激共振风速区间，检查塔筒连接螺栓",
        AlertLevel.CRITICAL: "立即停机检查塔筒结构完整性和基础稳定性",
    },
    AlertType.TEMPERATURE_ANOMALY: {
        AlertLevel.LOW: "检查冷却系统运行状态",
        AlertLevel.MEDIUM: "检查温控阀和冷却风扇，清理散热片",
        AlertLevel.HIGH: "建议降载运行，检查润滑油油位和油质",
        AlertLevel.CRITICAL: "立即停机，检查齿轮箱/发电机是否存在局部过热和轴承故障",
    },
}


def get_base_suggestion(alert_type: AlertType, level: AlertLevel) -> str:
    templates = SUGGESTION_TEMPLATES.get(alert_type, {})
    return templates.get(level, "")


def build_stall_suggestion(ctx, level: AlertLevel) -> str:
    suggestion = get_base_suggestion(AlertType.STALL_TENDENCY, level)
    is_high_altitude = ctx.extra.get("is_high_altitude", False)
    if is_high_altitude and level in [AlertLevel.HIGH, AlertLevel.CRITICAL]:
        suggestion += "（高海拔场区需特别注意低空气密度对气动性能的影响）"
    return suggestion


def build_vortex_suggestion(ctx, level: AlertLevel) -> str:
    return get_base_suggestion(AlertType.VORTEX_VIBRATION, level)


def build_temperature_suggestion(ctx, level: AlertLevel) -> str:
    return get_base_suggestion(AlertType.TEMPERATURE_ANOMALY, level)


def build_power_suggestion(ctx, level: AlertLevel) -> str:
    effective_deviation = ctx.extra.get("effective_deviation", 0)
    if effective_deviation > 0:
        direction = "正"
        check_item = "变桨校准、风速仪准确性，防止过发损坏设备"
    else:
        direction = "负"
        check_item = "叶片翼型状态、偏航对风精度、传动系统效率"

    suggestions = {
        AlertLevel.LOW: f"持续监控功率{direction}偏趋势",
        AlertLevel.MEDIUM: f"检查{check_item}",
        AlertLevel.HIGH: f"建议停机检查{check_item}，必要时进行功率曲线复算",
        AlertLevel.CRITICAL: f"立即停机全面检查{check_item}，重新进行叶片标定",
    }
    return suggestions.get(level, "")


SUGGESTION_BUILDERS: Dict[AlertType, Callable] = {
    AlertType.STALL_TENDENCY: build_stall_suggestion,
    AlertType.VORTEX_VIBRATION: build_vortex_suggestion,
    AlertType.TEMPERATURE_ANOMALY: build_temperature_suggestion,
    AlertType.POWER_DEVIATION: build_power_suggestion,
}


def get_suggestion(alert_type: AlertType, ctx, level: AlertLevel) -> str:
    builder = SUGGESTION_BUILDERS.get(alert_type)
    if builder:
        return builder(ctx, level)
    return ""
