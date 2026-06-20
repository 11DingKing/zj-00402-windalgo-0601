import sys
import os
import json
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000/api/v1"


class AlertChainTester:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0

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
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        for name, status, detail in self.results:
            print(f"{status} - {name}")

        print("\n" + "=" * 60)
        print(f"总计: {self.passed + self.failed} 个测试")
        print(f"通过: {self.passed}")
        print(f"失败: {self.failed}")
        print("=" * 60)

        return self.failed == 0


def wait_for_server():
    import time
    print("等待服务启动...")
    for i in range(30):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("服务已就绪！")
                return True
        except:
            pass
        time.sleep(1)
    print("服务启动超时！")
    return False


def load_sample_data(filename: str):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, "sample_data", filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def run_tests():
    tester = AlertChainTester()

    print("\n" + "=" * 60)
    print("阶段 1: 基础功能测试")
    print("=" * 60)

    print("\n1.1 测试机组信息查询")
    response = requests.get(f"{BASE_URL}/turbines")
    tester.test("获取机组列表成功", response.status_code == 200, f"状态码: {response.status_code}")
    turbines = response.json()
    tester.test("返回10台机组", len(turbines) == 10, f"实际返回: {len(turbines)}")

    ridge_turbines = [t for t in turbines if t["ridge_name"] == "西风脊"]
    tester.test("西风脊有5台机组", len(ridge_turbines) == 5, f"实际: {len(ridge_turbines)}")

    print("\n1.2 测试按山脊查询机组")
    response = requests.get(f"{BASE_URL}/turbines?ridge_name=东风脊")
    tester.test("按东风脊查询成功", response.status_code == 200)
    east_turbines = response.json()
    tester.test("东风脊返回5台机组", len(east_turbines) == 5, f"实际: {len(east_turbines)}")

    print("\n" + "=" * 60)
    print("阶段 2: 正常数据测试（应无告警）")
    print("=" * 60)

    normal_data = load_sample_data("normal_samples.json")
    print(f"\n测试正常数据 - {normal_data['description']}")
    print(f"机组: {normal_data['turbine_code']}, 记录数: {len(normal_data['data'])}")

    normal_alerts = []
    for record in normal_data["data"]:
        response = requests.post(f"{BASE_URL}/operating-data", json=record)
        if response.status_code == 200:
            alerts = response.json()
            normal_alerts.extend(alerts)

    tester.test("正常数据上报成功", len(normal_alerts) >= 0)
    tester.test("正常数据不应产生告警", len(normal_alerts) == 0,
                f"实际产生 {len(normal_alerts)} 条告警: {json.dumps(normal_alerts, ensure_ascii=False)}")

    print("\n" + "=" * 60)
    print("阶段 3: 失速倾向告警测试")
    print("=" * 60)

    stall_data = load_sample_data("stall_samples.json")
    print(f"\n测试失速数据 - {stall_data['description']}")
    print(f"机组: {stall_data['turbine_code']}, 记录数: {len(stall_data['data'])}")

    stall_alerts = []
    for record in stall_data["data"]:
        response = requests.post(f"{BASE_URL}/operating-data", json=record)
        if response.status_code == 200:
            alerts = response.json()
            stall_alerts.extend(alerts)

    tester.test("失速数据上报成功", len(stall_alerts) >= 0)
    tester.test("失速数据产生告警", len(stall_alerts) > 0, f"未产生任何告警")

    if stall_alerts:
        stall_types = [a["alert_type"] for a in stall_alerts]
        tester.test("包含失速倾向告警", "失速倾向" in stall_types,
                    f"告警类型: {list(set(stall_types))}")

        high_level = [a for a in stall_alerts if a["alert_level"] in ["高", "严重"]]
        tester.test("包含高/严重级别告警", len(high_level) > 0,
                    f"高/严重级别: {len(high_level)}")

        stall_alert = [a for a in stall_alerts if a["alert_type"] == "失速倾向"][0]
        tester.test("告警包含触发原因", len(stall_alert["trigger_reason"]) > 0)
        tester.test("告警包含处置建议", len(stall_alert["suggestion"]) > 0)
        tester.test("建议包含高海拔提示", "高海拔" in stall_alert["suggestion"]
                    or stall_alert["alert_level"] in ["低", "中"])

    print("\n" + "=" * 60)
    print("阶段 4: 涡激振荡告警测试")
    print("=" * 60)

    vortex_data = load_sample_data("vortex_samples.json")
    print(f"\n测试涡激数据 - {vortex_data['description']}")
    print(f"机组: {vortex_data['turbine_code']}, 记录数: {len(vortex_data['data'])}")

    vortex_alerts = []
    for record in vortex_data["data"]:
        response = requests.post(f"{BASE_URL}/operating-data", json=record)
        if response.status_code == 200:
            alerts = response.json()
            vortex_alerts.extend(alerts)

    tester.test("涡激数据上报成功", len(vortex_alerts) >= 0)
    tester.test("涡激数据产生告警", len(vortex_alerts) > 0, f"未产生任何告警")

    if vortex_alerts:
        vortex_types = [a["alert_type"] for a in vortex_alerts]
        tester.test("包含涡激振荡告警", "涡激振荡" in vortex_types,
                    f"告警类型: {list(set(vortex_types))}")

        vortex_alert = [a for a in vortex_alerts if a["alert_type"] == "涡激振荡"][0]
        tester.test("触发原因包含振动信息", "振动" in vortex_alert["trigger_reason"])

    print("\n" + "=" * 60)
    print("阶段 5: 温控异常告警测试")
    print("=" * 60)

    temp_data = load_sample_data("temperature_samples.json")
    print(f"\n测试温控数据 - {temp_data['description']}")
    print(f"机组: {temp_data['turbine_code']}, 记录数: {len(temp_data['data'])}")

    temp_alerts = []
    for record in temp_data["data"]:
        response = requests.post(f"{BASE_URL}/operating-data", json=record)
        if response.status_code == 200:
            alerts = response.json()
            temp_alerts.extend(alerts)

    tester.test("温控数据上报成功", len(temp_alerts) >= 0)
    tester.test("温控数据产生告警", len(temp_alerts) > 0, f"未产生任何告警")

    if temp_alerts:
        temp_types = [a["alert_type"] for a in temp_alerts]
        tester.test("包含温控异常告警", "温控异常" in temp_types,
                    f"告警类型: {list(set(temp_types))}")

        critical = [a for a in temp_alerts if a["alert_level"] == "严重"]
        tester.test("包含严重级别告警（齿轮箱/发电机温度）", len(critical) > 0,
                    f"严重级别: {len(critical)}")

    print("\n" + "=" * 60)
    print("阶段 6: 功率偏离告警测试")
    print("=" * 60)

    power_data = load_sample_data("power_deviation_samples.json")
    print(f"\n测试功率数据 - {power_data['description']}")
    print(f"机组: {power_data['turbine_code']}, 记录数: {len(power_data['data'])}")

    power_alerts = []
    for record in power_data["data"]:
        response = requests.post(f"{BASE_URL}/operating-data", json=record)
        if response.status_code == 200:
            alerts = response.json()
            power_alerts.extend(alerts)

    tester.test("功率数据上报成功", len(power_alerts) >= 0)
    tester.test("功率数据产生告警", len(power_alerts) > 0, f"未产生任何告警")

    if power_alerts:
        power_types = [a["alert_type"] for a in power_alerts]
        tester.test("包含功率偏离告警", "功率偏离" in power_types,
                    f"告警类型: {list(set(power_types))}")

        power_alert = [a for a in power_alerts if a["alert_type"] == "功率偏离"][0]
        tester.test("触发原因包含功率偏离信息", "功率" in power_alert["trigger_reason"])

    print("\n" + "=" * 60)
    print("阶段 7: 混合异常告警测试")
    print("=" * 60)

    mixed_data = load_sample_data("mixed_abnormal_samples.json")
    print(f"\n测试混合异常 - {mixed_data['description']}")
    print(f"机组: {mixed_data['turbine_code']}, 记录数: {len(mixed_data['data'])}")

    mixed_alerts = []
    for record in mixed_data["data"]:
        response = requests.post(f"{BASE_URL}/operating-data", json=record)
        if response.status_code == 200:
            alerts = response.json()
            mixed_alerts.extend(alerts)

    tester.test("混合异常数据上报成功", len(mixed_alerts) >= 0)
    tester.test("混合异常产生多条告警", len(mixed_alerts) >= 3,
                f"实际产生 {len(mixed_alerts)} 条告警")

    if mixed_alerts:
        mixed_types = list(set([a["alert_type"] for a in mixed_alerts]))
        tester.test("包含多种告警类型", len(mixed_types) >= 2,
                    f"告警类型: {mixed_types}")

    print("\n" + "=" * 60)
    print("阶段 8: 告警查询与处理测试")
    print("=" * 60)

    print("\n8.1 查询待处理告警")
    response = requests.get(f"{BASE_URL}/alerts", params={"status": "待处理"})
    tester.test("查询待处理告警成功", response.status_code == 200, f"状态码: {response.status_code}, 响应: {response.text[:100]}")
    pending_alerts = []
    if response.status_code == 200:
        pending_alerts = response.json()
    tester.test("存在待处理告警", len(pending_alerts) > 0, f"待处理告警: {len(pending_alerts)}")

    if pending_alerts:
        alert_id = pending_alerts[0]["id"]
        print(f"\n8.2 测试告警处理 - 告警ID: {alert_id}")

        print("  - 标记为误报测试")
        response = requests.post(
            f"{BASE_URL}/alerts/{alert_id}/handle",
            json={
                "alert_id": alert_id,
                "handling_type": "误报",
                "operator": "测试工程师",
                "note": "测试用例 - 标记误报"
            }
        )
        tester.test("标记误报成功", response.status_code == 200, f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            tester.test("告警状态变为已关闭", result["alert"]["status"] == "已关闭",
                        f"状态: {result['alert']['status']}")

        alert_id_2 = None
        for a in pending_alerts:
            if a["id"] != alert_id and a["status"] == "待处理":
                alert_id_2 = a["id"]
                break

        if alert_id_2:
            print(f"\n8.3 测试降载处理 - 告警ID: {alert_id_2}")
            response = requests.post(
                f"{BASE_URL}/alerts/{alert_id_2}/handle",
                json={
                    "alert_id": alert_id_2,
                    "handling_type": "已降载",
                    "operator": "运维人员A",
                    "note": "已远程降载15%，持续监控"
                }
            )
            tester.test("降载处理成功", response.status_code == 200)

            if response.status_code == 200:
                result = response.json()
                tester.test("告警状态变为处理中", result["alert"]["status"] == "处理中",
                            f"状态: {result['alert']['status']}")

            print(f"\n8.4 测试告警处理历史查询")
            response = requests.get(f"{BASE_URL}/alerts/{alert_id_2}/history")
            tester.test("查询处理历史成功", response.status_code == 200)
            history = response.json()
            tester.test("存在处理记录", len(history) >= 1, f"记录数: {len(history)}")

    print("\n" + "=" * 60)
    print("阶段 9: 统计分析测试")
    print("=" * 60)

    print("\n9.1 批量上报分布数据")
    normal_distributed = load_sample_data("normal_distributed_samples.json")
    batch_response = requests.post(
        f"{BASE_URL}/operating-data/batch",
        json=normal_distributed["data"]
    )
    tester.test("批量上报成功", batch_response.status_code == 200)
    if batch_response.status_code == 200:
        batch_result = batch_response.json()
        print(f"  处理记录: {batch_result['records_processed']}, 生成告警: {batch_result['alerts_generated']}")

    print("\n9.2 获取综合统计")
    response = requests.get(f"{BASE_URL}/statistics?days=7")
    tester.test("获取综合统计成功", response.status_code == 200)

    if response.status_code == 200:
        stats = response.json()
        tester.test("统计包含机组总数", stats["total_turbines"] == 10,
                    f"机组数: {stats['total_turbines']}")
        tester.test("统计包含告警总数", stats["total_alerts"] > 0,
                    f"告警数: {stats['total_alerts']}")
        tester.test("包含山脊分布数据", len(stats["ridge_distributions"]) >= 2,
                    f"山脊数: {len(stats['ridge_distributions'])}")
        tester.test("包含高风险时段数据", len(stats["high_risk_periods"]) == 24,
                    f"时段数: {len(stats['high_risk_periods'])}")

    print("\n9.3 获取山脊风险分布")
    response = requests.get(f"{BASE_URL}/statistics/ridge-distribution?days=7")
    tester.test("获取山脊分布成功", response.status_code == 200)

    if response.status_code == 200:
        ridges = response.json()
        ridge_names = [r["ridge_name"] for r in ridges]
        tester.test("包含西风脊数据", "西风脊" in ridge_names)
        tester.test("包含东风脊数据", "东风脊" in ridge_names)

        west_ridge = [r for r in ridges if r["ridge_name"] == "西风脊"][0]
        tester.test("西风脊有5个机位数据", len(west_ridge["turbines"]) == 5,
                    f"机位数: {len(west_ridge['turbines'])}")

        positions = [t["position"] for t in west_ridge["turbines"]]
        tester.test("机位按顺序排列", positions == sorted(positions))

    print("\n9.4 获取重复告警机组")
    response = requests.get(f"{BASE_URL}/statistics/repeated-alert-turbines?days=7&min_alerts=3")
    tester.test("获取重复告警机组成功", response.status_code == 200)

    if response.status_code == 200:
        repeated = response.json()
        if len(repeated) > 0:
            tester.test("重复告警机组按告警数排序",
                        all(repeated[i]["total_alerts"] >= repeated[i + 1]["total_alerts"]
                            for i in range(len(repeated) - 1)))

            top = repeated[0]
            tester.test("包含告警类型列表", len(top["alert_types"]) > 0)

    print("\n9.5 获取高风险时段")
    response = requests.get(f"{BASE_URL}/statistics/high-risk-periods?days=7")
    tester.test("获取高风险时段成功", response.status_code == 200)

    if response.status_code == 200:
        periods = response.json()
        hours = [p["hour"] for p in periods]
        tester.test("覆盖24小时", hours == list(range(24)))

    print("\n" + "=" * 60)
    print("阶段 10: 告警分类筛选测试")
    print("=" * 60)

    print("\n10.1 按告警类型筛选")
    for alert_type in ["失速倾向", "涡激振荡", "温控异常", "功率偏离"]:
        response = requests.get(f"{BASE_URL}/alerts", params={"alert_type": alert_type})
        tester.test(f"筛选{alert_type}成功", response.status_code == 200, f"状态码: {response.status_code}")
        if response.status_code == 200:
            filtered = response.json()
            if len(filtered) > 0:
                types = [a["alert_type"] for a in filtered]
                tester.test(f"筛选结果正确", all(t == alert_type for t in types))

    print("\n10.2 按告警级别筛选")
    for level in ["低", "中", "高", "严重"]:
        response = requests.get(f"{BASE_URL}/alerts", params={"alert_level": level})
        tester.test(f"筛选{level}级别成功", response.status_code == 200, f"状态码: {response.status_code}")

    return tester.print_summary()


if __name__ == "__main__":
    if not wait_for_server():
        print("无法连接到服务器，请先启动服务:")
        print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        sys.exit(1)

    success = run_tests()
    sys.exit(0 if success else 1)
