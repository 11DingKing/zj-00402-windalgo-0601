import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import OperatingData, Turbine, AlertType, AlertLevel
from app.alert_engine import AlertRuleEngine
from datetime import datetime


def create_test_turbine():
    return Turbine(
        id=1,
        turbine_code="TEST-001",
        name="测试风机1号",
        ridge_name="测试山脊",
        position=1,
        altitude=1500,
        created_at=datetime.utcnow(),
    )


def create_operating_data(**kwargs):
    defaults = {
        "id": 1,
        "turbine_id": 1,
        "timestamp": datetime.utcnow(),
        "time_window_start": datetime.utcnow(),
        "time_window_end": datetime.utcnow(),
        "wind_speed": 10.0,
        "wind_speed_std": 1.0,
        "wind_direction": 180.0,
        "wind_direction_change": 5.0,
        "air_density": 1.225,
        "rotor_speed": 15.0,
        "rotor_speed_std": 0.5,
        "power_deviation": 0.0,
        "nacelle_temperature": 45.0,
        "gearbox_temperature": 60.0,
        "generator_temperature": 70.0,
        "tower_vibration_x": 5.0,
        "tower_vibration_y": 5.0,
        "tower_vibration_z": 3.0,
        "blade_load_1": 100.0,
        "blade_load_2": 100.0,
        "blade_load_3": 100.0,
        "blade_load_std": 5.0,
        "created_at": datetime.utcnow(),
    }
    defaults.update(kwargs)
    return OperatingData(**defaults)


def test_normal_data():
    print("\n" + "="*60)
    print("测试1: 正常数据不应产生告警")
    print("="*60)
    turbine = create_test_turbine()
    data = create_operating_data()

    results = AlertRuleEngine.analyze(data, turbine)
    assert len(results) == 0, f"正常数据不应产生告警，实际产生了 {len(results)} 条"
    print("✓ 正常数据无告警，符合预期")


def test_stall_tendency():
    print("\n" + "="*60)
    print("测试2: 失速倾向告警")
    print("="*60)
    turbine = create_test_turbine()

    print("\n2.1 叶轮转速波动 > 0.8 (应触发 MEDIUM)")
    data = create_operating_data(rotor_speed_std=0.9)
    result = AlertRuleEngine.check_stall_tendency(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.MEDIUM
    assert "叶轮转速波动过大" in result.trigger_reason
    assert len(result.suggestion) > 0
    print(f"  ✓ 触发级别: {result.alert_level.value}, 原因: {result.trigger_reason}")

    print("\n2.2 风速>8且功率负偏<-15 (应触发 HIGH)")
    data = create_operating_data(wind_speed=9.0, power_deviation=-16.0)
    result = AlertRuleEngine.check_stall_tendency(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.HIGH
    assert "功率负偏" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}, 原因: {result.trigger_reason}")

    print("\n2.3 三叶片载荷差>30 (应触发 HIGH)")
    data = create_operating_data(blade_load_1=80.0, blade_load_2=100.0, blade_load_3=120.0)
    result = AlertRuleEngine.check_stall_tendency(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.HIGH
    assert "三叶片载荷差过大" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}, 原因: {result.trigger_reason}")

    print("\n2.4 高海拔大风速下转速波动异常 (应触发 CRITICAL)")
    data = create_operating_data(
        air_density=0.9,
        wind_speed=11.0,
        rotor_speed_std=1.5
    )
    result = AlertRuleEngine.check_stall_tendency(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.CRITICAL
    assert "高海拔" in result.trigger_reason
    assert "高海拔" in result.suggestion
    print(f"  ✓ 触发级别: {result.alert_level.value}, 原因: {result.trigger_reason}")
    print(f"  ✓ 建议包含高海拔提示: {result.suggestion[:50]}...")

    print("\n✓ 失速倾向所有测试通过")


def test_vortex_vibration():
    print("\n" + "="*60)
    print("测试3: 涡激振荡告警")
    print("="*60)
    turbine = create_test_turbine()

    print("\n3.1 合成振动 > 15 (应触发 HIGH)")
    data = create_operating_data(tower_vibration_x=12.0, tower_vibration_y=10.0)
    result = AlertRuleEngine.check_vortex_vibration(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.HIGH
    assert "塔筒合成振动超过阈值" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n3.2 合成振动 > 10 且 <=15 (应触发 MEDIUM)")
    data = create_operating_data(tower_vibration_x=8.0, tower_vibration_y=7.0)
    result = AlertRuleEngine.check_vortex_vibration(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.MEDIUM
    assert "塔筒合成振动偏高" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n3.3 轴向振动 > 8 (应触发 HIGH)")
    data = create_operating_data(tower_vibration_z=9.0)
    result = AlertRuleEngine.check_vortex_vibration(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.HIGH
    assert "塔筒轴向振动异常" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n3.4 涡激共振区间(4-10m/s)振动偏高 (应触发 HIGH)")
    data = create_operating_data(wind_speed=7.0, tower_vibration_x=6.0, tower_vibration_y=6.0)
    result = AlertRuleEngine.check_vortex_vibration(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.HIGH
    assert "涡激共振区间" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n3.5 叶片载荷波动 > 20 (应触发，级别继承其他条件或LOW)")
    data = create_operating_data(blade_load_std=25.0)
    result = AlertRuleEngine.check_vortex_vibration(data, turbine)
    assert result.triggered == True
    assert "叶片载荷波动异常" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n✓ 涡激振荡所有测试通过")


def test_temperature_anomaly():
    print("\n" + "="*60)
    print("测试4: 温控异常告警")
    print("="*60)
    turbine = create_test_turbine()

    print("\n4.1 机舱温度 > 65 (应触发 HIGH)")
    data = create_operating_data(nacelle_temperature=66.0)
    result = AlertRuleEngine.check_temperature_anomaly(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.HIGH
    assert "机舱温度过高" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n4.2 机舱温度 > 55 且 <=65 (应触发 MEDIUM)")
    data = create_operating_data(nacelle_temperature=56.0)
    result = AlertRuleEngine.check_temperature_anomaly(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.MEDIUM
    assert "机舱温度偏高" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n4.3 齿轮箱温度 > 80 (应触发 CRITICAL)")
    data = create_operating_data(gearbox_temperature=81.0)
    result = AlertRuleEngine.check_temperature_anomaly(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.CRITICAL
    assert "齿轮箱温度过高" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n4.4 齿轮箱温度 > 70 且 <=80 (应触发 HIGH)")
    data = create_operating_data(gearbox_temperature=71.0)
    result = AlertRuleEngine.check_temperature_anomaly(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.HIGH
    assert "齿轮箱温度偏高" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n4.5 发电机温度 > 95 (应触发 CRITICAL)")
    data = create_operating_data(generator_temperature=96.0)
    result = AlertRuleEngine.check_temperature_anomaly(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.CRITICAL
    assert "发电机温度过高" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n4.6 低风速下机舱温度 > 50 (应触发 MEDIUM)")
    data = create_operating_data(wind_speed=5.0, nacelle_temperature=51.0)
    result = AlertRuleEngine.check_temperature_anomaly(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.MEDIUM
    assert "低风速" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n✓ 温控异常所有测试通过")


def test_power_deviation():
    print("\n" + "="*60)
    print("测试5: 功率偏离告警")
    print("="*60)
    turbine = create_test_turbine()

    print("\n5.1 正常海拔功率偏离 > 30 (应触发 CRITICAL)")
    data = create_operating_data(power_deviation=35.0)
    result = AlertRuleEngine.check_power_deviation(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.CRITICAL
    assert "功率曲线严重偏离" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}, 建议: {result.suggestion[:30]}...")

    print("\n5.2 正常海拔功率偏离 > 20 且 <=30 (应触发 HIGH)")
    data = create_operating_data(power_deviation=25.0)
    result = AlertRuleEngine.check_power_deviation(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.HIGH
    assert "功率曲线大幅偏离" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n5.3 正常海拔功率偏离 > 10 且 <=20 (应触发 MEDIUM)")
    data = create_operating_data(power_deviation=15.0)
    result = AlertRuleEngine.check_power_deviation(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.MEDIUM
    assert "功率曲线偏离" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n5.4 高海拔修正后偏离 > 30 (应触发 CRITICAL)")
    data = create_operating_data(air_density=0.9, power_deviation=20.0)
    result = AlertRuleEngine.check_power_deviation(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.CRITICAL
    assert "高海拔修正后功率严重偏离" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n5.5 大风速下功率正偏 > 15 (应触发 HIGH)")
    data = create_operating_data(wind_speed=13.0, power_deviation=16.0)
    result = AlertRuleEngine.check_power_deviation(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.HIGH
    assert "大风速下功率正偏异常" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n5.6 正常海拔中风速以上功率负偏 < -20 (应触发 HIGH)")
    data = create_operating_data(wind_speed=7.0, power_deviation=-21.0)
    result = AlertRuleEngine.check_power_deviation(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.HIGH
    assert "中风速以上功率负偏严重" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n5.7 高海拔修正后中风速以上功率负偏 < -15 (应触发 HIGH)")
    data = create_operating_data(air_density=0.9, wind_speed=7.0, power_deviation=-45.0)
    result = AlertRuleEngine.check_power_deviation(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.HIGH
    assert "高海拔修正后中风速以上功率负偏严重" in result.trigger_reason
    print(f"  ✓ 触发级别: {result.alert_level.value}")

    print("\n✓ 功率偏离所有测试通过")


def test_combined_alerts():
    print("\n" + "="*60)
    print("测试6: 多条件组合触发")
    print("="*60)
    turbine = create_test_turbine()

    print("\n6.1 同时触发多个条件，级别取最高")
    data = create_operating_data(
        rotor_speed_std=0.9,
        wind_speed=9.0,
        power_deviation=-16.0,
    )
    result = AlertRuleEngine.check_stall_tendency(data, turbine)
    assert result.triggered == True
    assert result.alert_level == AlertLevel.HIGH
    assert "叶轮转速波动过大" in result.trigger_reason
    assert "功率负偏" in result.trigger_reason
    print(f"  ✓ 多原因同时记录: {result.trigger_reason}")
    print(f"  ✓ 最高级别: {result.alert_level.value}")

    print("\n6.2 analyze() 返回所有触发的告警")
    data = create_operating_data(
        wind_speed=9.0,
        power_deviation=-16.0,
        nacelle_temperature=66.0,
    )
    results = AlertRuleEngine.analyze(data, turbine)
    alert_types = [r.alert_type for r in results]
    assert AlertType.STALL_TENDENCY in alert_types
    assert AlertType.TEMPERATURE_ANOMALY in alert_types
    print(f"  ✓ 同时产生 {len(results)} 条告警，类型: {[t.value for t in alert_types]}")

    print("\n✓ 多条件组合测试通过")


def test_sample_data():
    print("\n" + "="*60)
    print("测试7: 使用真实样本数据验证")
    print("="*60)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sample_dir = os.path.join(script_dir, "sample_data")

    turbine = create_test_turbine()

    test_cases = [
        ("stall_samples.json", AlertType.STALL_TENDENCY, "失速"),
        ("vortex_samples.json", AlertType.VORTEX_VIBRATION, "涡激"),
        ("temperature_samples.json", AlertType.TEMPERATURE_ANOMALY, "温控"),
        ("power_deviation_samples.json", AlertType.POWER_DEVIATION, "功率"),
    ]

    for filename, expected_type, description in test_cases:
        filepath = os.path.join(sample_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            sample = json.load(f)

        print(f"\n7.{test_cases.index((filename, expected_type, description))+1} {description}样本数据")
        print(f"  描述: {sample.get('description', 'N/A')}")

        triggered_count = 0
        for record in sample["data"]:
            record["turbine_code"] = sample["turbine_code"]
            data_dict = {k: v for k, v in record.items() if k not in ["turbine_code"]}
            data_dict["id"] = 1
            data_dict["turbine_id"] = 1
            data_dict["timestamp"] = datetime.fromisoformat(data_dict["timestamp"].replace("Z", "+00:00"))
            data_dict["time_window_start"] = datetime.fromisoformat(data_dict["time_window_start"].replace("Z", "+00:00"))
            data_dict["time_window_end"] = datetime.fromisoformat(data_dict["time_window_end"].replace("Z", "+00:00"))
            data_dict["created_at"] = datetime.utcnow()

            data = create_operating_data(**data_dict)
            results = AlertRuleEngine.analyze(data, turbine)

            for r in results:
                if r.alert_type == expected_type:
                    triggered_count += 1

        print(f"  记录数: {len(sample['data'])}, 触发{description}告警: {triggered_count}次")
        assert triggered_count > 0, f"{description}样本应产生告警"
        print(f"  ✓ {description}样本测试通过")

    print("\n✓ 所有样本数据测试通过")


def run_all_tests():
    print("\n" + "="*60)
    print("告警规则业务逻辑一致性测试")
    print("="*60)

    try:
        test_normal_data()
        test_stall_tendency()
        test_vortex_vibration()
        test_temperature_anomaly()
        test_power_deviation()
        test_combined_alerts()
        test_sample_data()

        print("\n" + "="*60)
        print("✅ 所有测试通过！重构后的业务逻辑与原逻辑完全一致")
        print("="*60)
        return True
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
