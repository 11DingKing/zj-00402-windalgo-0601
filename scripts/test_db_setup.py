import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base, SessionLocal
from app.models import *

print("开始创建数据库表...")
Base.metadata.create_all(bind=engine)
print("表创建成功")

db = SessionLocal()
try:
    from app.models import Turbine, RiskChain, RiskPhase, Alert

    turbines = db.query(Turbine).all()
    print(f"机组数: {len(turbines)}")

    risk_chains = db.query(RiskChain).all()
    print(f"风险链数: {len(risk_chains)}")

    alerts = db.query(Alert).all()
    print(f"告警数: {len(alerts)}")

    print("\n表结构验证通过！")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
