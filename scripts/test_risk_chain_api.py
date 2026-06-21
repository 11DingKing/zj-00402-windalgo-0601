import sys
import os
import json
import requests
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000/api/v1"


def test_risk_chain_api():
    print("=" * 60)
    print("测试：风险链 API 接口")
    print("=" * 60)

    passed = 0
    failed = 0

    def test(name, condition, detail=""):
        nonlocal passed, failed
        status = "✓ PASS" if condition else "✗ FAIL"
        if condition:
            passed += 1
        else:
            failed += 1
        print(f"  {status} - {name}")
        if detail and not condition:
            print(f"      详情: {detail}")

    print("\n1. 测试上报数据生成风险链")
    print("-" * 40)

    turbine_code = "W01-02"

    base_time = datetime(2024, 1, 15, 10, 0, 0)

    data1 = {
        "turbine_code": turbine_code,
        "timestamp": base_time.isoformat(),
        "time_window_start": (base_time - timedelta(minutes=5)).isoformat(),
        "time_window_end": base_time.isoformat(),
        "wind_speed": 9.0,
        "wind_speed_std": 0.6,
        "wind_direction": 270.0,
        "wind_direction_change": 2.0,
        "air_density": 0.92,
        "rotor_speed": 15.5,
        "rotor_speed_std": 0.4,
        "power_deviation": -22.0,
        "nacelle_temperature": 48.0,
        "gearbox_temperature": 62.0,
        "generator_temperature": 78.0,
        "tower_vibration_x": 6.0,
        "tower_vibration_y": 5.0,
        "blade_load_1": 105.0,
        "blade_load_2": 108.0,
        "blade_load_3": 102.0,
        "blade_load_std": 3.0
    }

    response = requests.post(f"{BASE_URL}/operating-data", json=data1)
    test("上报阶段1数据成功", response.status_code == 200, f"状态码: {response.status_code}")

    alerts1 = response.json()
    print(f"  阶段1生成告警数: {len(alerts1)}")
    if alerts1:
        has_risk_chain = all("risk_chain_id" in a for a in alerts1)
        test("告警包含风险链ID", has_risk_chain)

    time2 = base_time + timedelta(hours=2)
    data2 = {
        "turbine_code": turbine_code,
        "timestamp": time2.isoformat(),
        "time_window_start": (time2 - timedelta(minutes=5)).isoformat(),
        "time_window_end": time2.isoformat(),
        "wind_speed": 11.0,
        "wind_speed_std": 0.9,
        "wind_direction": 275.0,
        "wind_direction_change": 3.5,
        "air_density": 0.92,
        "rotor_speed": 17.0,
        "rotor_speed_std": 1.3,
        "power_deviation": -20.0,
        "nacelle_temperature": 52.0,
        "gearbox_temperature": 68.0,
        "generator_temperature": 82.0,
        "tower_vibration_x": 12.0,
        "tower_vibration_y": 10.0,
        "blade_load_1": 120.0,
        "blade_load_2": 125.0,
        "blade_load_3": 110.0,
        "blade_load_std": 7.5
    }

    response = requests.post(f"{BASE_URL}/operating-data", json=data2)
    test("上报阶段2数据成功", response.status_code == 200)

    alerts2 = response.json()
    print(f"  阶段2生成告警数: {len(alerts2)}")

    time3 = base_time + timedelta(hours=4)
    data3 = {
        "turbine_code": turbine_code,
        "timestamp": time3.isoformat(),
        "time_window_start": (time3 - timedelta(minutes=5)).isoformat(),
        "time_window_end": time3.isoformat(),
        "wind_speed": 12.0,
        "wind_speed_std": 0.7,
        "wind_direction": 280.0,
        "wind_direction_change": 3.0,
        "air_density": 0.92,
        "rotor_speed": 17.5,
        "rotor_speed_std": 1.0,
        "power_deviation": -15.0,
        "nacelle_temperature": 70.0,
        "gearbox_temperature": 85.0,
        "generator_temperature": 100.0,
        "tower_vibration_x": 8.0,
        "tower_vibration_y": 7.0,
        "blade_load_1": 115.0,
        "blade_load_2": 118.0,
        "blade_load_3": 112.0,
        "blade_load_std": 3.0
    }

    response = requests.post(f"{BASE_URL}/operating-data", json=data3)
    test("上报阶段3数据成功", response.status_code == 200)

    alerts3 = response.json()
    print(f"  阶段3生成告警数: {len(alerts3)}")

    escalation_alerts = [a for a in alerts3 if a.get("is_escalation")]
    print(f"  升级告警数: {len(escalation_alerts)}")

    print("\n2. 测试风险链列表查询")
    print("-" * 40)

    response = requests.get(f"{BASE_URL}/risk-chains")
    test("查询风险链列表成功", response.status_code == 200, f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        test("响应包含total字段", "total" in data)
        test("响应包含items字段", "items" in data)
        test("风险链数量 > 0", data["total"] > 0)

        if data["items"]:
            chain = data["items"][0]
            test("风险链包含chain_code", "chain_code" in chain)
            test("风险链包含status", "status" in chain)
            test("风险链包含current_phase", "current_phase" in chain)
            test("风险链包含phases", "phases" in chain)

    print("\n3. 测试风险链详情查询")
    print("-" * 40)

    chain_id = None
    if response.status_code == 200 and data["items"]:
        chain_id = data["items"][0]["id"]

    if chain_id:
        response = requests.get(f"{BASE_URL}/risk-chains/{chain_id}")
        test("查询风险链详情成功", response.status_code == 200)

        if response.status_code == 200:
            detail = response.json()
            test("详情包含alerts", "alerts" in detail)
            test("详情包含phases", "phases" in detail)
            test("详情包含overall_suggestion", "overall_suggestion" in detail)
            print(f"  风险链状态: {detail['status']}")
            print(f"  当前阶段: {detail['current_phase']}")
            print(f"  阶段数: {len(detail['phases'])}")
            print(f"  告警数: {len(detail['alerts'])}")

    print("\n4. 测试风险链阶段查询")
    print("-" * 40)

    if chain_id:
        response = requests.get(f"{BASE_URL}/risk-chains/{chain_id}/phases")
        test("查询阶段列表成功", response.status_code == 200)
        if response.status_code == 200:
            phases = response.json()
            test("阶段数 > 0", len(phases) > 0)
            if phases:
                test("阶段包含phase_index", "phase_index" in phases[0])
                test("阶段包含alert_type", "alert_type" in phases[0])

    print("\n5. 测试统计接口（包含风险链数据）")
    print("-" * 40)

    response = requests.get(f"{BASE_URL}/statistics?days=7")
    test("获取综合统计成功", response.status_code == 200)

    if response.status_code == 200:
        stats = response.json()
        test("包含total_risk_chains", "total_risk_chains" in stats)
        test("包含active_risk_chains", "active_risk_chains" in stats)
        test("包含escalating_risk_chains", "escalating_risk_chains" in stats)
        print(f"  总风险链数: {stats['total_risk_chains']}")
        print(f"  活跃风险链数: {stats['active_risk_chains']}")
        print(f"  升级中风险链数: {stats['escalating_risk_chains']}")

    print("\n6. 测试山脊风险分布（包含风险链数据）")
    print("-" * 40)

    response = requests.get(f"{BASE_URL}/statistics/ridge-distribution?days=7")
    test("获取山脊分布成功", response.status_code == 200)

    if response.status_code == 200:
        ridges = response.json()
        if ridges:
            ridge = ridges[0]
            if ridge["turbines"]:
                turbine = ridge["turbines"][0]
                test("包含active_risk_chain_count", "active_risk_chain_count" in turbine)
                test("包含high_risk_chain_count", "high_risk_chain_count" in turbine)
                test("包含chain_risk_score", "chain_risk_score" in turbine)
                print(f"  机组{turbine['turbine_code']}:")
                print(f"    活跃风险链: {turbine['active_risk_chain_count']}")
                print(f"    高风险链: {turbine['high_risk_chain_count']}")
                print(f"    链风险得分: {turbine['chain_risk_score']}")

    print("\n7. 测试重复告警机组（包含风险链数据）")
    print("-" * 40)

    response = requests.get(f"{BASE_URL}/statistics/repeated-alert-turbines?days=7&min_alerts=1")
    test("获取重复告警机组成功", response.status_code == 200)

    if response.status_code == 200:
        repeated = response.json()
        if repeated:
            top = repeated[0]
            test("包含active_risk_chains", "active_risk_chains" in top)
            test("包含max_chain_phases", "max_chain_phases" in top)
            test("包含has_escalation_chain", "has_escalation_chain" in top)
            print(f"  机组{top['turbine_code']}:")
            print(f"    总告警数: {top['total_alerts']}")
            print(f"    活跃风险链: {top['active_risk_chains']}")
            print(f"    最多阶段数: {top['max_chain_phases']}")
            print(f"    有升级链: {top['has_escalation_chain']}")

    print("\n8. 测试告警处置与风险链同步")
    print("-" * 40)

    alerts_response = requests.get(f"{BASE_URL}/alerts", params={"status": "待处理", "limit": 5})
    if alerts_response.status_code == 200:
        pending_alerts = alerts_response.json()
        if pending_alerts:
            alert_id = pending_alerts[0]["id"]
            print(f"  处理告警ID: {alert_id}")

            response = requests.post(
                f"{BASE_URL}/alerts/{alert_id}/handle",
                json={
                    "alert_id": alert_id,
                    "handling_type": "已降载",
                    "operator": "测试运维",
                    "note": "测试风险链同步"
                }
            )
            test("处理告警成功", response.status_code == 200)

            if response.status_code == 200:
                result = response.json()
                test("告警状态变为处理中", result["alert"]["status"] == "处理中")

    print("\n9. 测试关闭风险链")
    print("-" * 40)

    if chain_id:
        response = requests.post(
            f"{BASE_URL}/risk-chains/{chain_id}/close",
            json={
                "close_note": "测试关闭风险链",
                "close_condition": "人工确认风险已消除",
                "operator": "测试运维"
            }
        )
        test("关闭风险链成功", response.status_code == 200)

        if response.status_code == 200:
            closed_chain = response.json()
            test("风险链状态变为已关闭", closed_chain["status"] == "已关闭")
            test("有关闭时间", closed_chain["closed_at"] is not None)
            test("有关闭说明", closed_chain["close_note"] is not None)

    print("\n" + "=" * 60)
    print(f"测试结果: 通过 {passed} / {passed + failed}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = test_risk_chain_api()
    sys.exit(0 if success else 1)
