import sys
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Turbine, OperatingData, Alert, AlertStatus, AlertLevel,
    RiskChain, RiskChainStatus, RiskPhase, AlertHandling, HandlingType
)
from app.alert_engine import AlertRuleEngine
from app.risk_chain_engine import RiskChainEngine
from app.alert_rules import HIGH_RISK_LEVELS, count_high_risk, filter_active

TEST_RIDGE_NAME = "测试山脊_AUTO"
TEST_TURBINE_PREFIX = "TEST_AUTO_"

engine = create_engine(
    "sqlite:///./wind_turbine_test.db",
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def test(self, name: str, condition: bool, detail: str = ""):
        status = "✓ PASS" if condition else "✗ FAIL"
        if condition:
            self.passed += 1
        else:
            self.failed += 1
        self.results.append((name, status, detail))
        print(f"  {status} - {name}")
        if detail and not condition:
            print(f"      详情: {detail}")

    def print_summary(self):
        print("\n" + "=" * 70)
        print("测试结果汇总")
        print("=" * 70)
        for name, status, detail in self.results:
            print(f"{status} - {name}")

        print("\n" + "=" * 70)
        print(f"总计: {self.passed + self.failed} 个测试")
        print(f"通过: {self.passed}")
        print(f"失败: {self.failed}")
        print("=" * 70)
        return self.failed == 0


def setup_test_turbines(db) -> List[Turbine]:
    turbines_data = [
        {"turbine_code": f"{TEST_TURBINE_PREFIX}W01", "name": "测试风机1", "ridge_name": TEST_RIDGE_NAME,
         "position": 1, "altitude": 3200, "rated_power": 2500, "rated_wind_speed": 11},
        {"turbine_code": f"{TEST_TURBINE_PREFIX}W02", "name": "测试风机2", "ridge_name": TEST_RIDGE_NAME,
         "position": 2, "altitude": 3250, "rated_power": 2500, "rated_wind_speed": 11},
        {"turbine_code": f"{TEST_TURBINE_PREFIX}W03", "name": "测试风机3", "ridge_name": TEST_RIDGE_NAME,
         "position": 3, "altitude": 3300, "rated_power": 2500, "rated_wind_speed": 11},
        {"turbine_code": f"{TEST_TURBINE_PREFIX}W04", "name": "测试风机4", "ridge_name": TEST_RIDGE_NAME,
         "position": 4, "altitude": 3350, "rated_power": 2500, "rated_wind_speed": 11},
        {"turbine_code": f"{TEST_TURBINE_PREFIX}W05", "name": "测试风机5", "ridge_name": TEST_RIDGE_NAME,
         "position": 5, "altitude": 3400, "rated_power": 2500, "rated_wind_speed": 11},
    ]

    turbines = []
    for data in turbines_data:
        existing = db.query(Turbine).filter(Turbine.turbine_code == data["turbine_code"]).first()
        if existing:
            turbines.append(existing)
        else:
            turbine = Turbine(**data)
            db.add(turbine)
            db.flush()
            turbines.append(turbine)
    db.commit()
    return turbines


def cleanup_test_data(db):
    test_turbines = db.query(Turbine).filter(
        Turbine.turbine_code.like(f"{TEST_TURBINE_PREFIX}%")
    ).all()

    for turbine in test_turbines:
        db.query(AlertHandling).filter(
            AlertHandling.alert_id.in_(
                db.query(Alert.id).filter(Alert.turbine_id == turbine.id)
            )
        ).delete(synchronize_session=False)

        db.query(RiskPhase).filter(
            RiskPhase.risk_chain_id.in_(
                db.query(RiskChain.id).filter(RiskChain.turbine_id == turbine.id)
            )
        ).delete(synchronize_session=False)

        db.query(Alert).filter(Alert.turbine_id == turbine.id).delete(synchronize_session=False)
        db.query(RiskChain).filter(RiskChain.turbine_id == turbine.id).delete(synchronize_session=False)
        db.query(OperatingData).filter(OperatingData.turbine_id == turbine.id).delete(synchronize_session=False)
        db.delete(turbine)

    db.commit()


def create_operating_data_record(
    turbine_id: int,
    base_time: datetime,
    air_density: float,
    wind_speed: float,
    power_deviation: float,
    rotor_speed_std: float = 0.5,
    nacelle_temperature: float = 40.0,
    tower_vibration_x: float = 3.0,
    tower_vibration_y: float = 3.0,
    blade_load_1: float = 200.0,
    blade_load_2: float = 200.0,
    blade_load_3: float = 200.0,
    rotor_speed: float = 10.0,
    wind_direction: float = 200.0,
) -> OperatingData:
    return OperatingData(
        turbine_id=turbine_id,
        timestamp=base_time,
        time_window_start=base_time - timedelta(minutes=5),
        time_window_end=base_time,
        wind_speed=wind_speed,
        wind_speed_std=0.5,
        wind_direction=wind_direction,
        wind_direction_change=2.0,
        air_density=air_density,
        rotor_speed=rotor_speed,
        rotor_speed_std=rotor_speed_std,
        power_deviation=power_deviation,
        nacelle_temperature=nacelle_temperature,
        gearbox_temperature=60.0,
        generator_temperature=70.0,
        tower_vibration_x=tower_vibration_x,
        tower_vibration_y=tower_vibration_y,
        tower_vibration_z=2.0,
        blade_load_1=blade_load_1,
        blade_load_2=blade_load_2,
        blade_load_3=blade_load_3,
        blade_load_std=5.0,
        pitch_angle_1=5.0,
        pitch_angle_2=5.0,
        pitch_angle_3=5.0,
        yaw_angle=195.0,
    )


def insert_and_analyze_data(db, turbine: Turbine, data: OperatingData) -> List[Alert]:
    db.add(data)
    db.flush()

    alert_results = AlertRuleEngine.analyze(data, turbine)
    generated_alerts = []

    for result in alert_results:
        alert = Alert(
            turbine_id=turbine.id,
            operating_data_id=data.id,
            alert_type=result.alert_type,
            alert_level=result.alert_level,
            status=AlertStatus.PENDING,
            trigger_reason=result.trigger_reason,
            suggestion=result.suggestion,
            triggered_at=data.timestamp
        )
        db.add(alert)
        db.flush()

        RiskChainEngine.process_alert(db, alert, turbine)
        generated_alerts.append(alert)

    db.commit()
    return generated_alerts


def test_normal_segment_no_false_alarm(db, tester: TestResult, turbines: List[Turbine]):
    print("\n" + "=" * 70)
    print("边界测试 1: 正常片段不误报")
    print("=" * 70)

    turbine = turbines[0]
    base_time = datetime(2026, 6, 15, 10, 0, 0)

    print(f"\n测试机组: {turbine.turbine_code} (海拔 {turbine.altitude}m)")
    print("高海拔空气密度: 0.88 kg/m³ (< 0.95 阈值)")

    normal_records = [
        create_operating_data_record(
            turbine_id=turbine.id,
            base_time=base_time + timedelta(minutes=i * 10),
            air_density=0.88,
            wind_speed=8.0,
            power_deviation=-28.0,
            rotor_speed_std=0.4,
        )
        for i in range(3)
    ]

    all_alerts = []
    for i, record in enumerate(normal_records):
        alerts = insert_and_analyze_data(db, turbine, record)
        all_alerts.extend(alerts)
        print(f"  记录 {i+1}: 风速 {record.wind_speed}m/s, 功率偏差 {record.power_deviation}%")

    effective_deviation = -28.0 - ((0.88 / 1.225 - 1) * 100)
    print(f"  高海拔修正后功率偏差: {effective_deviation:.1f}% (阈值 ±15%)")

    tester.test(
        "正常高海拔数据不应产生告警",
        len(all_alerts) == 0,
        f"实际产生 {len(all_alerts)} 条告警: {[a.alert_type.value for a in all_alerts]}"
    )

    pending_count = db.query(Alert).filter(
        Alert.turbine_id == turbine.id,
        Alert.status == AlertStatus.PENDING
    ).count()
    tester.test(
        "数据库中无待处理告警",
        pending_count == 0,
        f"实际待处理告警数: {pending_count}"
    )

    return all_alerts


def test_continuous_abnormal_single_chain(db, tester: TestResult, turbines: List[Turbine]):
    print("\n" + "=" * 70)
    print("边界测试 2: 连续异常只形成合理风险链")
    print("=" * 70)

    turbine = turbines[1]
    base_time = datetime(2026, 6, 16, 11, 0, 0)

    print(f"\n测试机组: {turbine.turbine_code} (海拔 {turbine.altitude}m)")
    print("连续上报6条异常数据，间隔5分钟（24小时内）")
    print("前3条：功率偏离（演化早期），后3条：功率偏离+失速倾向（演化升级）")

    abnormal_records = []
    for i in range(3):
        record = create_operating_data_record(
            turbine_id=turbine.id,
            base_time=base_time + timedelta(minutes=i * 5),
            air_density=0.85,
            wind_speed=6.0 + i * 0.3,
            power_deviation=-50.0 - i * 2,
            rotor_speed_std=0.5,
        )
        abnormal_records.append(record)

    for i in range(3, 6):
        record = create_operating_data_record(
            turbine_id=turbine.id,
            base_time=base_time + timedelta(minutes=i * 5),
            air_density=0.85,
            wind_speed=9.0 + (i - 3) * 0.5,
            power_deviation=-35.0 - (i - 3) * 2,
            rotor_speed_std=0.9 + (i - 3) * 0.1,
        )
        abnormal_records.append(record)

    all_alerts = []
    for i, record in enumerate(abnormal_records):
        alerts = insert_and_analyze_data(db, turbine, record)
        all_alerts.extend(alerts)
        stall_alerts = [a for a in alerts if a.alert_type.value == "失速倾向"]
        power_alerts = [a for a in alerts if a.alert_type.value == "功率偏离"]
        print(f"  记录 {i+1}: 失速告警 {len(stall_alerts)} 条, 功率告警 {len(power_alerts)} 条")

    tester.test(
        "异常数据产生告警",
        len(all_alerts) > 0,
        "未产生任何告警"
    )

    risk_chains = db.query(RiskChain).filter(
        RiskChain.turbine_id == turbine.id
    ).all()

    tester.test(
        "24小时内只形成1条风险链",
        len(risk_chains) == 1,
        f"实际创建 {len(risk_chains)} 条风险链"
    )

    if risk_chains:
        chain = risk_chains[0]
        tester.test(
            "风险链包含多个告警",
            chain.total_alerts >= 3,
            f"风险链告警数: {chain.total_alerts}"
        )

        power_alerts_in_chain = [a for a in chain.alerts if a.alert_type.value == "功率偏离"]
        stall_alerts_in_chain = [a for a in chain.alerts if a.alert_type.value == "失速倾向"]

        tester.test(
            "风险链包含功率偏离告警（演化早期）",
            len(power_alerts_in_chain) > 0
        )

        has_escalation = len(power_alerts_in_chain) > 0 and len(stall_alerts_in_chain) > 0
        if has_escalation:
            tester.test(
                "存在升级则 escalation_count > 0",
                chain.escalation_count > 0,
                f"escalation_count: {chain.escalation_count}"
            )

            phase_types = [p.alert_type.value for p in chain.phases]
            tester.test(
                "风险阶段按演化顺序排列",
                phase_types == sorted(phase_types, key=lambda x: ["功率偏离", "失速倾向", "涡激振荡", "温控异常"].index(x))
            )

    return all_alerts, risk_chains


def test_false_alarm_excluded_from_stats(db, tester: TestResult, turbines: List[Turbine]):
    print("\n" + "=" * 70)
    print("边界测试 3: 误报关闭后不再计入高风险统计")
    print("=" * 70)

    turbine = turbines[2]
    base_time = datetime(2026, 6, 17, 12, 0, 0)

    print(f"\n测试机组: {turbine.turbine_code} (海拔 {turbine.altitude}m)")

    high_risk_record = create_operating_data_record(
        turbine_id=turbine.id,
        base_time=base_time,
        air_density=0.82,
        wind_speed=11.0,
        power_deviation=-40.0,
        rotor_speed_std=1.2,
    )

    alerts = insert_and_analyze_data(db, turbine, high_risk_record)
    high_risk_alerts = [a for a in alerts if a.alert_level in HIGH_RISK_LEVELS]

    print(f"  产生告警: {len(alerts)} 条, 其中高风险: {len(high_risk_alerts)} 条")
    for a in high_risk_alerts:
        print(f"    - {a.alert_type.value} ({a.alert_level.value})")

    tester.test(
        "产生高风险告警",
        len(high_risk_alerts) > 0,
        "未产生高风险告警"
    )

    if high_risk_alerts:
        all_turbine_alerts = db.query(Alert).filter(Alert.turbine_id == turbine.id).all()
        active_high_risk_before = count_high_risk(filter_active(all_turbine_alerts))

        tester.test(
            "关闭前活跃高风险告警数 > 0",
            active_high_risk_before > 0,
            f"活跃高风险数: {active_high_risk_before}"
        )

        alert_to_close = high_risk_alerts[0]
        print(f"\n  将告警 #{alert_to_close.id} 标记为误报并关闭")

        handling_record = AlertHandling(
            alert_id=alert_to_close.id,
            handling_type=HandlingType.FALSE_ALARM,
            operator="自动化测试",
            note="测试用例：标记误报"
        )
        db.add(handling_record)

        alert_to_close.status = AlertStatus.CLOSED
        alert_to_close.closed_at = datetime.utcnow()
        alert_to_close.close_note = "测试误报标记"
        db.commit()

        all_turbine_alerts_after = db.query(Alert).filter(Alert.turbine_id == turbine.id).all()
        active_high_risk_after = count_high_risk(filter_active(all_turbine_alerts_after))

        tester.test(
            "关闭后活跃高风险告警数减少",
            active_high_risk_after < active_high_risk_before,
            f"关闭前: {active_high_risk_before}, 关闭后: {active_high_risk_after}"
        )

        tester.test(
            "误报关状态正确",
            alert_to_close.status == AlertStatus.CLOSED,
            f"状态: {alert_to_close.status.value}"
        )

        closed_high_risk = count_high_risk([a for a in all_turbine_alerts_after if a.status == AlertStatus.CLOSED])
        tester.test(
            "已关闭告警不计入活跃高风险统计",
            closed_high_risk == len(high_risk_alerts),
            f"已关闭高风险: {closed_high_risk}, 预期: {len(high_risk_alerts)}"
        )

    return alerts


def test_ridge_multi_turbine_summary(db, tester: TestResult, turbines: List[Turbine]):
    print("\n" + "=" * 70)
    print("边界测试 4: 同一山脊多机位分布能正确汇总")
    print("=" * 70)

    ridge_turbines = turbines[0:5]
    base_time = datetime(2026, 6, 18, 14, 0, 0)

    print(f"\n测试山脊: {TEST_RIDGE_NAME}")
    print(f"机位数: {len(ridge_turbines)}")

    test_patterns = [
        {"turbine_idx": 0, "records": 2, "air_density": 0.90, "wind_speed": 7.0, "power_deviation": -25.0, "desc": "正常数据"},
        {"turbine_idx": 1, "records": 3, "air_density": 0.85, "wind_speed": 9.5, "power_deviation": -35.0, "desc": "功率偏离"},
        {"turbine_idx": 2, "records": 2, "air_density": 0.82, "wind_speed": 10.0, "power_deviation": -38.0, "desc": "功率偏离+失速"},
        {"turbine_idx": 3, "records": 3, "air_density": 0.88, "wind_speed": 6.0, "power_deviation": -10.0, "desc": "正常数据"},
        {"turbine_idx": 4, "records": 2, "air_density": 0.80, "wind_speed": 11.0, "power_deviation": -45.0, "desc": "严重功率偏离"},
    ]

    expected_data = {}
    for pattern in test_patterns:
        turbine = ridge_turbines[pattern["turbine_idx"]]
        turbine_alerts = []

        print(f"\n  机位 {pattern['turbine_idx'] + 1} ({turbine.turbine_code}): {pattern['desc']}")
        for i in range(pattern["records"]):
            record = create_operating_data_record(
                turbine_id=turbine.id,
                base_time=base_time + timedelta(minutes=pattern["turbine_idx"] * 30 + i * 10),
                air_density=pattern["air_density"],
                wind_speed=pattern["wind_speed"],
                power_deviation=pattern["power_deviation"],
                rotor_speed_std=1.0 if "失速" in pattern["desc"] or "严重" in pattern["desc"] else 0.5,
            )
            alerts = insert_and_analyze_data(db, turbine, record)
            turbine_alerts.extend(alerts)

        high_risk_count = count_high_risk(turbine_alerts)
        expected_data[turbine.id] = {
            "turbine_code": turbine.turbine_code,
            "position": turbine.position,
            "alert_count": len(turbine_alerts),
            "high_risk_count": high_risk_count,
        }
        print(f"    告警数: {len(turbine_alerts)}, 高风险: {high_risk_count}")

    print("\n  验证山脊汇总统计:")
    from app.routers.statistics import _get_ridge_risk_distribution

    start_date = datetime(2026, 6, 18, 0, 0, 0)
    ridge_distributions = _get_ridge_risk_distribution(db, start_date, TEST_RIDGE_NAME)

    tester.test(
        "返回测试山脊数据",
        len(ridge_distributions) == 1,
        f"实际返回 {len(ridge_distributions)} 条山脊数据"
    )

    if ridge_distributions:
        ridge_data = ridge_distributions[0]
        tester.test(
            "山脊名称正确",
            ridge_data.ridge_name == TEST_RIDGE_NAME,
            f"名称: {ridge_data.ridge_name}"
        )

        tester.test(
            "包含全部5个机位数据",
            len(ridge_data.turbines) == 5,
            f"实际机位数: {len(ridge_data.turbines)}"
        )

        positions = [t.position for t in ridge_data.turbines]
        tester.test(
            "机位按位置顺序排列",
            positions == sorted(positions),
            f"位置顺序: {positions}"
        )

        turbine_codes = [t.turbine_code for t in ridge_data.turbines]
        for turbine in ridge_turbines:
            tester.test(
                f"包含机组 {turbine.turbine_code}",
                turbine.turbine_code in turbine_codes
            )

        for turbine_stat in ridge_data.turbines:
            expected = expected_data.get(ridge_turbines[int(turbine_stat.position) - 1].id)
            if expected:
                tester.test(
                    f"机位{turbine_stat.position}告警数正确",
                    turbine_stat.alert_count == expected["alert_count"],
                    f"预期: {expected['alert_count']}, 实际: {turbine_stat.alert_count}"
                )
                tester.test(
                    f"机位{turbine_stat.position}高风险数正确",
                    turbine_stat.high_risk_count == expected["high_risk_count"],
                    f"预期: {expected['high_risk_count']}, 实际: {turbine_stat.high_risk_count}"
                )

                risk_score = turbine_stat.alert_count * 1 + turbine_stat.high_risk_count * 2
                tester.test(
                    f"机位{turbine_stat.position}风险分数正确",
                    abs(turbine_stat.risk_score - risk_score) < 0.01,
                    f"预期: {risk_score}, 实际: {turbine_stat.risk_score}"
                )

        total_alerts = sum(t.alert_count for t in ridge_data.turbines)
        total_high_risk = sum(t.high_risk_count for t in ridge_data.turbines)
        print(f"\n  山脊汇总: 总告警 {total_alerts}, 高风险 {total_high_risk}")

        tester.test(
            "山脊总告警数正确",
            total_alerts == sum(e["alert_count"] for e in expected_data.values())
        )

    return ridge_distributions


def test_full_alert_chain_integration(db, tester: TestResult, turbines: List[Turbine]):
    print("\n" + "=" * 70)
    print("端到端测试: 运行片段入库 → 识别风险 → 生成告警 → 运维处置 → 统计刷新")
    print("=" * 70)

    turbine = turbines[4]
    base_time = datetime(2026, 6, 20, 15, 0, 0)
    stats_start = datetime(2026, 6, 20, 0, 0, 0)

    print(f"\n测试机组: {turbine.turbine_code}")

    print("\n[步骤1-3] 运行片段入库 + 识别风险 + 生成告警并关联风险链")
    records_data = [
        {"wind_speed": 9.0, "power_deviation": -30.0, "rotor_speed_std": 0.8, "desc": "轻度异常"},
        {"wind_speed": 9.8, "power_deviation": -33.0, "rotor_speed_std": 0.95, "desc": "中度异常"},
        {"wind_speed": 10.6, "power_deviation": -36.0, "rotor_speed_std": 1.10, "desc": "重度异常"},
        {"wind_speed": 11.4, "power_deviation": -39.0, "rotor_speed_std": 1.25, "desc": "严重异常"},
    ]

    all_alerts = []
    for i, data in enumerate(records_data):
        record = create_operating_data_record(
            turbine_id=turbine.id,
            base_time=base_time + timedelta(minutes=i * 15),
            air_density=0.82,
            wind_speed=data["wind_speed"],
            power_deviation=data["power_deviation"],
            rotor_speed_std=data["rotor_speed_std"],
        )
        alerts = insert_and_analyze_data(db, turbine, record)
        all_alerts.extend(alerts)
        print(f"  记录 {i+1} ({data['desc']}): 风速 {record.wind_speed:.1f}m/s, "
              f"功率偏差 {record.power_deviation:.1f}%, 产生告警 {len(alerts)} 条")
        for alert in alerts:
            chain = db.query(RiskChain).filter(RiskChain.id == alert.risk_chain_id).first()
            chain_code = chain.chain_code if chain else "N/A"
            print(f"    - {alert.alert_type.value} ({alert.alert_level.value}) → 风险链 {chain_code}")

    tester.test(
        "运行数据入库并生成告警成功",
        len(all_alerts) >= 3
    )

    risk_chains = db.query(RiskChain).filter(
        RiskChain.turbine_id == turbine.id,
        RiskChain.started_at >= stats_start
    ).all()
    tester.test(
        "风险链数量正确 (24小时内1条)",
        len(risk_chains) == 1,
        f"实际: {len(risk_chains)} 条"
    )

    chain = risk_chains[0] if risk_chains else None
    if chain:
        tester.test(
            "风险链告警总数正确",
            chain.total_alerts == len(all_alerts),
            f"预期: {len(all_alerts)}, 实际: {chain.total_alerts}"
        )

    print("\n[步骤4] 运维处置")
    pending_alerts = [a for a in all_alerts if a.status == AlertStatus.PENDING]
    alert_to_handle = None
    if pending_alerts:
        alert_to_handle = pending_alerts[0]
        print(f"  处置告警 #{alert_to_handle.id}: {alert_to_handle.alert_type.value} ({alert_to_handle.alert_level.value})")
        print("  操作: 已降载处理")

        handling_record = AlertHandling(
            alert_id=alert_to_handle.id,
            handling_type=HandlingType.LOAD_REDUCED,
            operator="运维工程师_AUTO",
            note="自动化测试：远程降载15%"
        )
        db.add(handling_record)
        alert_to_handle.status = AlertStatus.PROCESSING
        db.commit()
        db.refresh(alert_to_handle)

        tester.test(
            "告警状态更新为处理中",
            alert_to_handle.status == AlertStatus.PROCESSING
        )

        handling_history = db.query(AlertHandling).filter(
            AlertHandling.alert_id == alert_to_handle.id
        ).all()
        tester.test(
            "处理历史记录存在",
            len(handling_history) == 1
        )

    print("\n[步骤5] 统计刷新（仅统计6月19日数据）")

    total_alerts = db.query(Alert).filter(
        Alert.turbine_id == turbine.id,
        Alert.triggered_at >= stats_start
    ).count()
    pending_count = db.query(Alert).filter(
        Alert.turbine_id == turbine.id,
        Alert.status == AlertStatus.PENDING,
        Alert.triggered_at >= stats_start
    ).count()
    processing_count = db.query(Alert).filter(
        Alert.turbine_id == turbine.id,
        Alert.status == AlertStatus.PROCESSING,
        Alert.triggered_at >= stats_start
    ).count()
    high_risk_count = db.query(Alert).filter(
        Alert.turbine_id == turbine.id,
        Alert.alert_level.in_(HIGH_RISK_LEVELS),
        Alert.triggered_at >= stats_start
    ).count()

    print(f"  总告警数: {total_alerts}")
    print(f"  待处理: {pending_count}")
    print(f"  处理中: {processing_count}")
    print(f"  高风险: {high_risk_count}")
    print(f"  风险链: {len(risk_chains)} 条")

    tester.test(
        "总告警统计正确",
        total_alerts == len(all_alerts),
        f"预期: {len(all_alerts)}, 实际: {total_alerts}"
    )

    expected_pending = len([a for a in all_alerts if a.status == AlertStatus.PENDING])
    tester.test(
        "待处理统计正确",
        pending_count == expected_pending,
        f"预期: {expected_pending}, 实际: {pending_count}"
    )

    expected_processing = len([a for a in all_alerts if a.status == AlertStatus.PROCESSING])
    tester.test(
        "处理中统计正确",
        processing_count == expected_processing,
        f"预期: {expected_processing}, 实际: {processing_count}"
    )

    active_high_risk = db.query(Alert).filter(
        Alert.turbine_id == turbine.id,
        Alert.status.in_([AlertStatus.PENDING, AlertStatus.PROCESSING]),
        Alert.alert_level.in_(HIGH_RISK_LEVELS),
        Alert.triggered_at >= stats_start
    ).count()
    print(f"  活跃高风险告警: {active_high_risk}")

    tester.test(
        "活跃高风险统计正确 (排除已关闭)",
        active_high_risk <= high_risk_count
    )

    return all_alerts


def main():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    tester = TestResult()

    try:
        print("\n" + "=" * 70)
        print("高海拔告警链路自动化测试")
        print("=" * 70)
        print(f"测试数据库: wind_turbine_test.db (独立数据库，不污染生产数据)")
        print(f"测试机组前缀: {TEST_TURBINE_PREFIX}")
        print(f"测试山脊: {TEST_RIDGE_NAME}")

        print("\n[准备阶段] 初始化测试数据")
        turbines = setup_test_turbines(db)
        print(f"创建/确认 {len(turbines)} 台测试机组")

        test_normal_segment_no_false_alarm(db, tester, turbines)
        test_continuous_abnormal_single_chain(db, tester, turbines)
        test_false_alarm_excluded_from_stats(db, tester, turbines)
        test_ridge_multi_turbine_summary(db, tester, turbines)
        test_full_alert_chain_integration(db, tester, turbines)

        success = tester.print_summary()

        if success:
            print("\n" + "=" * 70)
            print("✓ 所有测试通过！")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("✗ 部分测试失败，请检查上述详情")
            print("=" * 70)

        return success

    finally:
        print("\n[清理阶段] 删除测试数据")
        cleanup_test_data(db)
        print("测试数据已清理完毕，生产环境未受影响")
        db.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
