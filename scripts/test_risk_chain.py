import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models import Turbine, Alert, OperatingData, RiskChain, RiskPhase
from app.alert_engine import AlertRuleEngine
from app.risk_chain_engine import RiskChainEngine

def test_risk_chain_evolution():
    print("=" * 60)
    print("测试：风险链演化功能")
    print("=" * 60)

    db = SessionLocal()

    turbine = db.query(Turbine).filter(Turbine.turbine_code == "W01-01").first()
    if not turbine:
        print("错误：找不到测试机组")
        db.close()
        return False

    print(f"\n测试机组: {turbine.turbine_code} ({turbine.name})")
    print(f"海拔: {turbine.altitude}m")

    base_time = datetime(2024, 1, 15, 10, 0, 0)

    print("\n" + "-" * 40)
    print("阶段1：功率偏离告警（风险链起始）")
    print("-" * 40)

    data1 = OperatingData(
        turbine_id=turbine.id,
        timestamp=base_time,
        time_window_start=base_time - timedelta(minutes=5),
        time_window_end=base_time,
        wind_speed=8.5,
        wind_speed_std=0.5,
        wind_direction=270.0,
        wind_direction_change=2.0,
        air_density=0.92,
        rotor_speed=15.0,
        rotor_speed_std=0.3,
        power_deviation=-25.0,
        nacelle_temperature=45.0,
        gearbox_temperature=60.0,
        generator_temperature=75.0,
        tower_vibration_x=5.0,
        tower_vibration_y=4.0,
        blade_load_1=100.0,
        blade_load_2=102.0,
        blade_load_3=98.0,
        blade_load_std=2.0
    )
    db.add(data1)
    db.flush()

    alert_results = AlertRuleEngine.analyze(data1, turbine)
    print(f"  生成告警数: {len(alert_results)}")

    for result in alert_results:
        alert = Alert(
            turbine_id=turbine.id,
            operating_data_id=data1.id,
            alert_type=result.alert_type,
            alert_level=result.alert_level,
            trigger_reason=result.trigger_reason,
            suggestion=result.suggestion,
            triggered_at=base_time
        )
        db.add(alert)
        db.flush()

        chain_result = RiskChainEngine.process_alert(db, alert, turbine)
        print(f"  告警类型: {result.alert_type.value}, 级别: {result.alert_level.value}")
        print(f"  风险链ID: {chain_result.risk_chain.id}, 代码: {chain_result.risk_chain.chain_code}")
        print(f"  是否新链: {chain_result.is_new_chain}, 是否升级: {chain_result.is_escalation}")
        print(f"  风险链阶段数: {len(chain_result.risk_chain.phases)}")
        print(f"  风险链状态: {chain_result.risk_chain.status.value}")
        print(f"  综合建议: {chain_result.risk_chain.overall_suggestion}")

    print("\n" + "-" * 40)
    print("阶段2：失速倾向告警（风险升级）")
    print("-" * 40)

    time2 = base_time + timedelta(hours=2)
    data2 = OperatingData(
        turbine_id=turbine.id,
        timestamp=time2,
        time_window_start=time2 - timedelta(minutes=5),
        time_window_end=time2,
        wind_speed=10.5,
        wind_speed_std=0.8,
        wind_direction=275.0,
        wind_direction_change=3.0,
        air_density=0.92,
        rotor_speed=16.5,
        rotor_speed_std=1.2,
        power_deviation=-22.0,
        nacelle_temperature=48.0,
        gearbox_temperature=62.0,
        generator_temperature=78.0,
        tower_vibration_x=6.0,
        tower_vibration_y=5.0,
        blade_load_1=115.0,
        blade_load_2=120.0,
        blade_load_3=105.0,
        blade_load_std=6.0
    )
    db.add(data2)
    db.flush()

    alert_results2 = AlertRuleEngine.analyze(data2, turbine)
    print(f"  生成告警数: {len(alert_results2)}")

    for result in alert_results2:
        alert = Alert(
            turbine_id=turbine.id,
            operating_data_id=data2.id,
            alert_type=result.alert_type,
            alert_level=result.alert_level,
            trigger_reason=result.trigger_reason,
            suggestion=result.suggestion,
            triggered_at=time2
        )
        db.add(alert)
        db.flush()

        chain_result = RiskChainEngine.process_alert(db, alert, turbine)
        print(f"  告警类型: {result.alert_type.value}, 级别: {result.alert_level.value}")
        print(f"  风险链ID: {chain_result.risk_chain.id}")
        print(f"  是否新链: {chain_result.is_new_chain}, 是否升级: {chain_result.is_escalation}")
        print(f"  风险链阶段数: {len(chain_result.risk_chain.phases)}")
        print(f"  风险链当前阶段: {chain_result.risk_chain.current_phase.value}")
        print(f"  风险链状态: {chain_result.risk_chain.status.value}")
        print(f"  升级次数: {chain_result.risk_chain.escalation_count}")

    print("\n" + "-" * 40)
    print("阶段3：温控异常告警（继续升级）")
    print("-" * 40)

    time3 = base_time + timedelta(hours=4)
    data3 = OperatingData(
        turbine_id=turbine.id,
        timestamp=time3,
        time_window_start=time3 - timedelta(minutes=5),
        time_window_end=time3,
        wind_speed=11.0,
        wind_speed_std=0.6,
        wind_direction=280.0,
        wind_direction_change=2.5,
        air_density=0.92,
        rotor_speed=17.0,
        rotor_speed_std=0.9,
        power_deviation=-18.0,
        nacelle_temperature=68.0,
        gearbox_temperature=82.0,
        generator_temperature=98.0,
        tower_vibration_x=7.0,
        tower_vibration_y=6.0,
        blade_load_1=110.0,
        blade_load_2=115.0,
        blade_load_3=108.0,
        blade_load_std=3.5
    )
    db.add(data3)
    db.flush()

    alert_results3 = AlertRuleEngine.analyze(data3, turbine)
    print(f"  生成告警数: {len(alert_results3)}")

    for result in alert_results3:
        alert = Alert(
            turbine_id=turbine.id,
            operating_data_id=data3.id,
            alert_type=result.alert_type,
            alert_level=result.alert_level,
            trigger_reason=result.trigger_reason,
            suggestion=result.suggestion,
            triggered_at=time3
        )
        db.add(alert)
        db.flush()

        chain_result = RiskChainEngine.process_alert(db, alert, turbine)
        print(f"  告警类型: {result.alert_type.value}, 级别: {result.alert_level.value}")
        print(f"  风险链ID: {chain_result.risk_chain.id}")
        print(f"  是否升级: {chain_result.is_escalation}")
        print(f"  风险链阶段数: {len(chain_result.risk_chain.phases)}")
        print(f"  风险链当前阶段: {chain_result.risk_chain.current_phase.value}")
        print(f"  风险链状态: {chain_result.risk_chain.status.value}")
        print(f"  总告警数: {chain_result.risk_chain.total_alerts}")

    print("\n" + "-" * 40)
    print("阶段4：验证风险链详情")
    print("-" * 40)

    chain = db.query(RiskChain).filter(RiskChain.turbine_id == turbine.id).first()
    if chain:
        print(f"  风险链代码: {chain.chain_code}")
        print(f"  状态: {chain.status.value}")
        print(f"  当前阶段: {chain.current_phase.value}")
        print(f"  当前级别: {chain.current_level.value}")
        print(f"  开始时间: {chain.started_at}")
        print(f"  最后更新: {chain.last_updated_at}")
        print(f"  总告警数: {chain.total_alerts}")
        print(f"  升级次数: {chain.escalation_count}")
        print(f"  阶段数: {len(chain.phases)}")
        print(f"  关联告警数: {len(chain.alerts)}")

        print("\n  阶段详情:")
        for phase in chain.phases:
            print(f"    阶段{phase.phase_index}: {phase.alert_type.value} ({phase.alert_level.value})")
            print(f"      开始时间: {phase.started_at}")
            print(f"      是否升级: {bool(phase.is_escalation)}")
            print(f"      建议: {phase.phase_suggestion[:50]}...")

        print(f"\n  综合建议: {chain.overall_suggestion}")
    else:
        print("  未找到风险链！")

    db.commit()
    db.close()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_risk_chain_evolution()
    sys.exit(0 if success else 1)
