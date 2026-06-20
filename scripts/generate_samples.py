import sys
import os
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_normal_data(turbine_code: str, base_time: datetime, count: int = 10) -> List[Dict]:
    data = []
    for i in range(count):
        timestamp = base_time + timedelta(minutes=i * 10)
        wind_speed = random.uniform(6, 9)
        air_density = random.uniform(0.88, 0.92)
        density_correction = (air_density / 1.225 - 1) * 100
        base_load = random.uniform(190, 205)

        raw_deviation = density_correction + random.uniform(-3, 3)

        data.append({
            "turbine_code": turbine_code,
            "timestamp": timestamp.isoformat(),
            "time_window_start": (timestamp - timedelta(minutes=5)).isoformat(),
            "time_window_end": timestamp.isoformat(),
            "wind_speed": round(wind_speed, 2),
            "wind_speed_std": round(random.uniform(0.3, 0.6), 2),
            "wind_direction": round(random.uniform(180, 220), 1),
            "wind_direction_change": round(random.uniform(-5, 5), 1),
            "air_density": round(air_density, 4),
            "rotor_speed": round(wind_speed * 1.2 + random.uniform(-0.3, 0.3), 2),
            "rotor_speed_std": round(random.uniform(0.2, 0.5), 2),
            "power_deviation": round(raw_deviation, 1),
            "nacelle_temperature": round(random.uniform(35, 48), 1),
            "gearbox_temperature": round(random.uniform(55, 65), 1),
            "generator_temperature": round(random.uniform(65, 78), 1),
            "tower_vibration_x": round(random.uniform(2, 5), 2),
            "tower_vibration_y": round(random.uniform(2, 5), 2),
            "tower_vibration_z": round(random.uniform(1, 3), 2),
            "blade_load_1": round(base_load + random.uniform(-3, 3), 1),
            "blade_load_2": round(base_load + random.uniform(-3, 3), 1),
            "blade_load_3": round(base_load + random.uniform(-3, 3), 1),
            "blade_load_std": round(random.uniform(5, 10), 1),
            "pitch_angle_1": round(random.uniform(2, 8), 1),
            "pitch_angle_2": round(random.uniform(2, 8), 1),
            "pitch_angle_3": round(random.uniform(2, 8), 1),
            "yaw_angle": round(random.uniform(185, 215), 1)
        })
    return data


def generate_stall_data(turbine_code: str, base_time: datetime, count: int = 5) -> List[Dict]:
    data = []
    for i in range(count):
        timestamp = base_time + timedelta(minutes=i * 10)
        wind_speed = random.uniform(9, 13)

        data.append({
            "turbine_code": turbine_code,
            "timestamp": timestamp.isoformat(),
            "time_window_start": (timestamp - timedelta(minutes=5)).isoformat(),
            "time_window_end": timestamp.isoformat(),
            "wind_speed": round(wind_speed, 2),
            "wind_speed_std": round(random.uniform(0.8, 1.5), 2),
            "wind_direction": round(random.uniform(190, 210), 1),
            "wind_direction_change": round(random.uniform(-8, 8), 1),
            "air_density": round(random.uniform(0.82, 0.88), 4),
            "rotor_speed": round(wind_speed * 1.0 + random.uniform(-1, 1), 2),
            "rotor_speed_std": round(random.uniform(0.9, 1.8), 2),
            "power_deviation": round(random.uniform(-25, -15), 1),
            "nacelle_temperature": round(random.uniform(42, 52), 1),
            "gearbox_temperature": round(random.uniform(62, 72), 1),
            "generator_temperature": round(random.uniform(72, 82), 1),
            "tower_vibration_x": round(random.uniform(4, 8), 2),
            "tower_vibration_y": round(random.uniform(4, 8), 2),
            "tower_vibration_z": round(random.uniform(2, 5), 2),
            "blade_load_1": round(random.uniform(220, 260), 1),
            "blade_load_2": round(random.uniform(190, 210), 1),
            "blade_load_3": round(random.uniform(230, 270), 1),
            "blade_load_std": round(random.uniform(18, 28), 1),
            "pitch_angle_1": round(random.uniform(5, 12), 1),
            "pitch_angle_2": round(random.uniform(5, 12), 1),
            "pitch_angle_3": round(random.uniform(5, 12), 1),
            "yaw_angle": round(random.uniform(195, 205), 1)
        })
    return data


def generate_vortex_data(turbine_code: str, base_time: datetime, count: int = 5) -> List[Dict]:
    data = []
    for i in range(count):
        timestamp = base_time + timedelta(minutes=i * 10)
        wind_speed = random.uniform(5, 9)

        data.append({
            "turbine_code": turbine_code,
            "timestamp": timestamp.isoformat(),
            "time_window_start": (timestamp - timedelta(minutes=5)).isoformat(),
            "time_window_end": timestamp.isoformat(),
            "wind_speed": round(wind_speed, 2),
            "wind_speed_std": round(random.uniform(0.4, 0.8), 2),
            "wind_direction": round(random.uniform(170, 230), 1),
            "wind_direction_change": round(random.uniform(-3, 3), 1),
            "air_density": round(random.uniform(0.86, 0.90), 4),
            "rotor_speed": round(wind_speed * 1.15 + random.uniform(-0.2, 0.2), 2),
            "rotor_speed_std": round(random.uniform(0.3, 0.6), 2),
            "power_deviation": round(random.uniform(-8, 3), 1),
            "nacelle_temperature": round(random.uniform(38, 48), 1),
            "gearbox_temperature": round(random.uniform(58, 68), 1),
            "generator_temperature": round(random.uniform(68, 78), 1),
            "tower_vibration_x": round(random.uniform(8, 16), 2),
            "tower_vibration_y": round(random.uniform(8, 16), 2),
            "tower_vibration_z": round(random.uniform(5, 10), 2),
            "blade_load_1": round(random.uniform(190, 230), 1),
            "blade_load_2": round(random.uniform(190, 230), 1),
            "blade_load_3": round(random.uniform(190, 230), 1),
            "blade_load_std": round(random.uniform(22, 35), 1),
            "pitch_angle_1": round(random.uniform(3, 7), 1),
            "pitch_angle_2": round(random.uniform(3, 7), 1),
            "pitch_angle_3": round(random.uniform(3, 7), 1),
            "yaw_angle": round(random.uniform(185, 215), 1)
        })
    return data


def generate_temperature_data(turbine_code: str, base_time: datetime, count: int = 5) -> List[Dict]:
    data = []
    for i in range(count):
        timestamp = base_time + timedelta(minutes=i * 10)
        wind_speed = random.uniform(4, 7)

        data.append({
            "turbine_code": turbine_code,
            "timestamp": timestamp.isoformat(),
            "time_window_start": (timestamp - timedelta(minutes=5)).isoformat(),
            "time_window_end": timestamp.isoformat(),
            "wind_speed": round(wind_speed, 2),
            "wind_speed_std": round(random.uniform(0.2, 0.5), 2),
            "wind_direction": round(random.uniform(185, 215), 1),
            "wind_direction_change": round(random.uniform(-2, 2), 1),
            "air_density": round(random.uniform(0.88, 0.92), 4),
            "rotor_speed": round(wind_speed * 1.1 + random.uniform(-0.2, 0.2), 2),
            "rotor_speed_std": round(random.uniform(0.2, 0.4), 2),
            "power_deviation": round(random.uniform(-3, 3), 1),
            "nacelle_temperature": round(random.uniform(58, 72), 1),
            "gearbox_temperature": round(random.uniform(72, 88), 1),
            "generator_temperature": round(random.uniform(85, 102), 1),
            "tower_vibration_x": round(random.uniform(3, 6), 2),
            "tower_vibration_y": round(random.uniform(3, 6), 2),
            "tower_vibration_z": round(random.uniform(2, 4), 2),
            "blade_load_1": round(random.uniform(160, 190), 1),
            "blade_load_2": round(random.uniform(160, 190), 1),
            "blade_load_3": round(random.uniform(160, 190), 1),
            "blade_load_std": round(random.uniform(6, 12), 1),
            "pitch_angle_1": round(random.uniform(1, 4), 1),
            "pitch_angle_2": round(random.uniform(1, 4), 1),
            "pitch_angle_3": round(random.uniform(1, 4), 1),
            "yaw_angle": round(random.uniform(190, 210), 1)
        })
    return data


def generate_power_deviation_data(turbine_code: str, base_time: datetime, count: int = 5) -> List[Dict]:
    data = []
    for i in range(count):
        timestamp = base_time + timedelta(minutes=i * 10)
        wind_speed = random.uniform(7, 14)
        air_density = random.uniform(0.85, 0.90)
        density_correction = (air_density / 1.225 - 1) * 100
        raw_deviation = density_correction + random.uniform(15, 30)

        data.append({
            "turbine_code": turbine_code,
            "timestamp": timestamp.isoformat(),
            "time_window_start": (timestamp - timedelta(minutes=5)).isoformat(),
            "time_window_end": timestamp.isoformat(),
            "wind_speed": round(wind_speed, 2),
            "wind_speed_std": round(random.uniform(0.4, 0.8), 2),
            "wind_direction": round(random.uniform(180, 220), 1),
            "wind_direction_change": round(random.uniform(-3, 3), 1),
            "air_density": round(air_density, 4),
            "rotor_speed": round(wind_speed * 1.1 + random.uniform(-0.3, 0.3), 2),
            "rotor_speed_std": round(random.uniform(0.4, 0.7), 2),
            "power_deviation": round(raw_deviation, 1),
            "nacelle_temperature": round(random.uniform(40, 52), 1),
            "gearbox_temperature": round(random.uniform(58, 70), 1),
            "generator_temperature": round(random.uniform(70, 82), 1),
            "tower_vibration_x": round(random.uniform(3, 7), 2),
            "tower_vibration_y": round(random.uniform(3, 7), 2),
            "tower_vibration_z": round(random.uniform(2, 5), 2),
            "blade_load_1": round(random.uniform(170, 210), 1),
            "blade_load_2": round(random.uniform(170, 210), 1),
            "blade_load_3": round(random.uniform(170, 210), 1),
            "blade_load_std": round(random.uniform(8, 15), 1),
            "pitch_angle_1": round(random.uniform(3, 9), 1),
            "pitch_angle_2": round(random.uniform(3, 9), 1),
            "pitch_angle_3": round(random.uniform(3, 9), 1),
            "yaw_angle": round(random.uniform(175, 225), 1)
        })
    return data


def generate_mixed_abnormal_data(turbine_code: str, base_time: datetime, count: int = 8) -> List[Dict]:
    data = []
    for i in range(count):
        timestamp = base_time + timedelta(minutes=i * 10)
        wind_speed = random.uniform(9, 14)

        data.append({
            "turbine_code": turbine_code,
            "timestamp": timestamp.isoformat(),
            "time_window_start": (timestamp - timedelta(minutes=5)).isoformat(),
            "time_window_end": timestamp.isoformat(),
            "wind_speed": round(wind_speed, 2),
            "wind_speed_std": round(random.uniform(0.8, 1.4), 2),
            "wind_direction": round(random.uniform(185, 215), 1),
            "wind_direction_change": round(random.uniform(-6, 6), 1),
            "air_density": round(random.uniform(0.80, 0.86), 4),
            "rotor_speed": round(wind_speed * 0.95 + random.uniform(-0.8, 0.8), 2),
            "rotor_speed_std": round(random.uniform(1.0, 1.6), 2),
            "power_deviation": round(random.uniform(-28, -15), 1),
            "nacelle_temperature": round(random.uniform(52, 68), 1),
            "gearbox_temperature": round(random.uniform(68, 82), 1),
            "generator_temperature": round(random.uniform(78, 92), 1),
            "tower_vibration_x": round(random.uniform(7, 13), 2),
            "tower_vibration_y": round(random.uniform(7, 13), 2),
            "tower_vibration_z": round(random.uniform(4, 8), 2),
            "blade_load_1": round(random.uniform(240, 290), 1),
            "blade_load_2": round(random.uniform(200, 230), 1),
            "blade_load_3": round(random.uniform(240, 290), 1),
            "blade_load_std": round(random.uniform(22, 35), 1),
            "pitch_angle_1": round(random.uniform(6, 14), 1),
            "pitch_angle_2": round(random.uniform(6, 14), 1),
            "pitch_angle_3": round(random.uniform(6, 14), 1),
            "yaw_angle": round(random.uniform(180, 220), 1)
        })
    return data


def main():
    random.seed(42)

    base_time = datetime.utcnow() - timedelta(hours=12)

    samples = {
        "normal": {
            "description": "正常运行数据 - 无告警",
            "turbine_code": "W01-01",
            "data": generate_normal_data("W01-01", base_time, 10)
        },
        "stall": {
            "description": "失速倾向数据 - 高海拔低空气密度下转速波动、功率负偏",
            "turbine_code": "W01-03",
            "data": generate_stall_data("W01-03", base_time + timedelta(hours=1), 5)
        },
        "vortex": {
            "description": "涡激振荡数据 - 特定风速区塔筒振动异常",
            "turbine_code": "E01-02",
            "data": generate_vortex_data("E01-02", base_time + timedelta(hours=2), 5)
        },
        "temperature": {
            "description": "温控异常数据 - 低风速下机舱、齿轮箱、发电机温度过高",
            "turbine_code": "W01-05",
            "data": generate_temperature_data("W01-05", base_time + timedelta(hours=3), 5)
        },
        "power_deviation": {
            "description": "功率偏离数据 - 中风速以上功率严重负偏",
            "turbine_code": "E01-04",
            "data": generate_power_deviation_data("E01-04", base_time + timedelta(hours=4), 5)
        },
        "mixed_abnormal": {
            "description": "混合异常数据 - 多指标同时异常，典型高风险机组",
            "turbine_code": "W01-02",
            "data": generate_mixed_abnormal_data("W01-02", base_time + timedelta(hours=5), 8)
        },
        "normal_distributed": {
            "description": "各机组正常运行数据 - 用于山脊分布统计",
            "turbines": ["W01-01", "W01-02", "W01-03", "W01-04", "W01-05", "E01-01", "E01-02", "E01-03", "E01-04", "E01-05"],
            "data": []
        }
    }

    for idx, turbine_code in enumerate(samples["normal_distributed"]["turbines"]):
        turbine_data = generate_normal_data(
            turbine_code,
            base_time + timedelta(hours=6 + idx * 0.5),
            3
        )
        samples["normal_distributed"]["data"].extend(turbine_data)

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_data")
    os.makedirs(output_dir, exist_ok=True)

    for key, value in samples.items():
        output_file = os.path.join(output_dir, f"{key}_samples.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
        print(f"生成样本: {key} -> {output_file}")
        if "data" in value:
            print(f"  记录数: {len(value['data'])}")

    all_data = []
    for key in ["normal", "stall", "vortex", "temperature", "power_deviation", "mixed_abnormal", "normal_distributed"]:
        all_data.extend(samples[key]["data"])

    full_output = os.path.join(output_dir, "all_samples.json")
    with open(full_output, "w", encoding="utf-8") as f:
        json.dump({"description": "所有样本数据合集", "data": all_data}, f, ensure_ascii=False, indent=2)
    print(f"\n生成完整数据集: {full_output}")
    print(f"总记录数: {len(all_data)}")


if __name__ == "__main__":
    main()
