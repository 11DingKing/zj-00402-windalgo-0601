import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models import Turbine

Base.metadata.create_all(bind=engine)

db = SessionLocal()

turbines_data = [
    {"turbine_code": "W01-01", "name": "1号风机", "ridge_name": "西风脊", "position": 1,
     "altitude": 3200, "rated_power": 2500, "rated_wind_speed": 11, "cut_in_wind_speed": 3, "cut_out_wind_speed": 25},
    {"turbine_code": "W01-02", "name": "2号风机", "ridge_name": "西风脊", "position": 2,
     "altitude": 3250, "rated_power": 2500, "rated_wind_speed": 11, "cut_in_wind_speed": 3, "cut_out_wind_speed": 25},
    {"turbine_code": "W01-03", "name": "3号风机", "ridge_name": "西风脊", "position": 3,
     "altitude": 3300, "rated_power": 2500, "rated_wind_speed": 11, "cut_in_wind_speed": 3, "cut_out_wind_speed": 25},
    {"turbine_code": "W01-04", "name": "4号风机", "ridge_name": "西风脊", "position": 4,
     "altitude": 3350, "rated_power": 2500, "rated_wind_speed": 11, "cut_in_wind_speed": 3, "cut_out_wind_speed": 25},
    {"turbine_code": "W01-05", "name": "5号风机", "ridge_name": "西风脊", "position": 5,
     "altitude": 3400, "rated_power": 2500, "rated_wind_speed": 11, "cut_in_wind_speed": 3, "cut_out_wind_speed": 25},
    {"turbine_code": "E01-01", "name": "6号风机", "ridge_name": "东风脊", "position": 1,
     "altitude": 3150, "rated_power": 3000, "rated_wind_speed": 10.5, "cut_in_wind_speed": 2.5, "cut_out_wind_speed": 25},
    {"turbine_code": "E01-02", "name": "7号风机", "ridge_name": "东风脊", "position": 2,
     "altitude": 3200, "rated_power": 3000, "rated_wind_speed": 10.5, "cut_in_wind_speed": 2.5, "cut_out_wind_speed": 25},
    {"turbine_code": "E01-03", "name": "8号风机", "ridge_name": "东风脊", "position": 3,
     "altitude": 3280, "rated_power": 3000, "rated_wind_speed": 10.5, "cut_in_wind_speed": 2.5, "cut_out_wind_speed": 25},
    {"turbine_code": "E01-04", "name": "9号风机", "ridge_name": "东风脊", "position": 4,
     "altitude": 3350, "rated_power": 3000, "rated_wind_speed": 10.5, "cut_in_wind_speed": 2.5, "cut_out_wind_speed": 25},
    {"turbine_code": "E01-05", "name": "10号风机", "ridge_name": "东风脊", "position": 5,
     "altitude": 3420, "rated_power": 3000, "rated_wind_speed": 10.5, "cut_in_wind_speed": 2.5, "cut_out_wind_speed": 25},
]

for data in turbines_data:
    existing = db.query(Turbine).filter(Turbine.turbine_code == data["turbine_code"]).first()
    if not existing:
        turbine = Turbine(**data)
        db.add(turbine)
        print(f"创建机组: {data['turbine_code']} - {data['name']} ({data['ridge_name']} 机位{data['position']})")
    else:
        print(f"机组已存在: {data['turbine_code']}")

db.commit()
db.close()

print("\n初始化完成！共创建/确认 10 台机组")
print("  - 西风脊: 5 台 (W01-01 ~ W01-05)")
print("  - 东风脊: 5 台 (E01-01 ~ E01-05)")
