import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship

from app.database import Base


class AlertType(str, enum.Enum):
    STALL_TENDENCY = "失速倾向"
    VORTEX_VIBRATION = "涡激振荡"
    TEMPERATURE_ANOMALY = "温控异常"
    POWER_DEVIATION = "功率偏离"


class AlertLevel(str, enum.Enum):
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    CRITICAL = "严重"


class AlertStatus(str, enum.Enum):
    PENDING = "待处理"
    PROCESSING = "处理中"
    CLOSED = "已关闭"


class HandlingType(str, enum.Enum):
    FALSE_ALARM = "误报"
    LOAD_REDUCED = "已降载"
    SHUTDOWN_INSPECTION = "停机检查"
    RESUMED_OPERATION = "恢复运行"


class Turbine(Base):
    __tablename__ = "turbines"

    id = Column(Integer, primary_key=True, index=True)
    turbine_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100))
    ridge_name = Column(String(100), nullable=False)
    position = Column(Integer, nullable=False)
    altitude = Column(Float)
    rated_power = Column(Float)
    rated_wind_speed = Column(Float)
    cut_in_wind_speed = Column(Float)
    cut_out_wind_speed = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    operating_data = relationship("OperatingData", back_populates="turbine")
    alerts = relationship("Alert", back_populates="turbine")


class OperatingData(Base):
    __tablename__ = "operating_data"

    id = Column(Integer, primary_key=True, index=True)
    turbine_id = Column(Integer, ForeignKey("turbines.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    time_window_start = Column(DateTime, nullable=False)
    time_window_end = Column(DateTime, nullable=False)

    wind_speed = Column(Float, nullable=False)
    wind_speed_std = Column(Float)
    wind_direction = Column(Float, nullable=False)
    wind_direction_change = Column(Float)
    air_density = Column(Float, nullable=False)
    rotor_speed = Column(Float, nullable=False)
    rotor_speed_std = Column(Float)
    power_deviation = Column(Float, nullable=False)
    nacelle_temperature = Column(Float, nullable=False)
    gearbox_temperature = Column(Float)
    generator_temperature = Column(Float)
    tower_vibration_x = Column(Float, nullable=False)
    tower_vibration_y = Column(Float, nullable=False)
    tower_vibration_z = Column(Float)
    blade_load_1 = Column(Float, nullable=False)
    blade_load_2 = Column(Float, nullable=False)
    blade_load_3 = Column(Float, nullable=False)
    blade_load_std = Column(Float)

    pitch_angle_1 = Column(Float)
    pitch_angle_2 = Column(Float)
    pitch_angle_3 = Column(Float)
    yaw_angle = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    turbine = relationship("Turbine", back_populates="operating_data")
    alerts = relationship("Alert", back_populates="operating_data")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    turbine_id = Column(Integer, ForeignKey("turbines.id"), nullable=False)
    operating_data_id = Column(Integer, ForeignKey("operating_data.id"), nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    alert_level = Column(Enum(AlertLevel), nullable=False, index=True)
    status = Column(Enum(AlertStatus), default=AlertStatus.PENDING, index=True)
    trigger_reason = Column(Text, nullable=False)
    suggestion = Column(Text, nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    closed_at = Column(DateTime)
    close_note = Column(Text)

    turbine = relationship("Turbine", back_populates="alerts")
    operating_data = relationship("OperatingData", back_populates="alerts")
    handling_records = relationship("AlertHandling", back_populates="alert")


class AlertHandling(Base):
    __tablename__ = "alert_handling"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    handling_type = Column(Enum(HandlingType), nullable=False)
    operator = Column(String(100), nullable=False)
    note = Column(Text)
    handled_at = Column(DateTime, default=datetime.utcnow)

    alert = relationship("Alert", back_populates="handling_records")
