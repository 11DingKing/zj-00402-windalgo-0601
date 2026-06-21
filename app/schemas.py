from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models import AlertType, AlertLevel, AlertStatus, HandlingType, RiskChainStatus


class TurbineBase(BaseModel):
    turbine_code: str = Field(..., max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    ridge_name: str = Field(..., max_length=100)
    position: int
    altitude: Optional[float] = None
    rated_power: Optional[float] = None
    rated_wind_speed: Optional[float] = None
    cut_in_wind_speed: Optional[float] = None
    cut_out_wind_speed: Optional[float] = None


class TurbineCreate(TurbineBase):
    pass


class Turbine(TurbineBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class OperatingDataBase(BaseModel):
    turbine_code: str
    timestamp: datetime
    time_window_start: datetime
    time_window_end: datetime

    wind_speed: float
    wind_speed_std: Optional[float] = None
    wind_direction: float
    wind_direction_change: Optional[float] = None
    air_density: float
    rotor_speed: float
    rotor_speed_std: Optional[float] = None
    power_deviation: float
    nacelle_temperature: float
    gearbox_temperature: Optional[float] = None
    generator_temperature: Optional[float] = None
    tower_vibration_x: float
    tower_vibration_y: float
    tower_vibration_z: Optional[float] = None
    blade_load_1: float
    blade_load_2: float
    blade_load_3: float
    blade_load_std: Optional[float] = None

    pitch_angle_1: Optional[float] = None
    pitch_angle_2: Optional[float] = None
    pitch_angle_3: Optional[float] = None
    yaw_angle: Optional[float] = None


class OperatingDataCreate(OperatingDataBase):
    pass


class OperatingData(OperatingDataBase):
    id: int
    turbine_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AlertBase(BaseModel):
    turbine_code: Optional[str] = None
    alert_type: AlertType
    alert_level: AlertLevel
    status: AlertStatus = AlertStatus.PENDING
    trigger_reason: str
    suggestion: str
    triggered_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    close_note: Optional[str] = None


class AlertCreate(AlertBase):
    turbine_id: int
    operating_data_id: int


class Alert(AlertBase):
    id: int
    turbine_id: int
    operating_data_id: int
    risk_chain_id: Optional[int] = None

    class Config:
        from_attributes = True


class AlertHandlingBase(BaseModel):
    alert_id: int
    handling_type: HandlingType
    operator: str
    note: Optional[str] = None


class AlertHandlingCreate(AlertHandlingBase):
    pass


class AlertHandling(AlertHandlingBase):
    id: int
    handled_at: datetime

    class Config:
        from_attributes = True


class AlertHandlingResponse(BaseModel):
    success: bool
    message: str
    alert: Optional[Alert] = None


class RiskDistributionItem(BaseModel):
    turbine_code: str
    position: int
    alert_count: int
    high_risk_count: int
    risk_score: float
    active_alert_count: int = 0
    active_high_risk_count: int = 0
    active_risk_score: float = 0.0
    closed_alert_count: int = 0
    active_risk_chain_count: int = 0
    high_risk_chain_count: int = 0
    chain_risk_score: float = 0.0


class RidgeRiskDistribution(BaseModel):
    ridge_name: str
    turbines: List[RiskDistributionItem]


class HighRiskPeriodItem(BaseModel):
    hour: int
    alert_count: int
    high_risk_count: int


class RepeatedAlertTurbine(BaseModel):
    turbine_code: str
    ridge_name: str
    total_alerts: int
    alert_types: List[str]
    active_alerts: int = 0
    active_alert_types: List[str] = []
    closed_alerts: int = 0
    active_risk_chains: int = 0
    max_chain_phases: int = 0
    has_escalation_chain: bool = False


class StatisticsResponse(BaseModel):
    total_turbines: int
    total_alerts: int
    pending_alerts: int
    processing_alerts: int
    closed_alerts: int
    active_alerts: int
    high_risk_alerts: int
    active_high_risk_alerts: int
    total_risk_chains: int
    active_risk_chains: int
    escalating_risk_chains: int
    ridge_distributions: List[RidgeRiskDistribution]
    high_risk_periods: List[HighRiskPeriodItem]
    repeated_alert_turbines: List[RepeatedAlertTurbine]


class BatchDataResponse(BaseModel):
    success: bool
    records_processed: int
    alerts_generated: int
    message: str


class RiskPhaseBase(BaseModel):
    phase_index: int
    alert_type: AlertType
    alert_level: AlertLevel
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    trigger_reason: Optional[str] = None
    phase_suggestion: Optional[str] = None
    is_escalation: int = 0


class RiskPhase(RiskPhaseBase):
    id: int
    risk_chain_id: int

    class Config:
        from_attributes = True


class RiskChainBase(BaseModel):
    turbine_code: Optional[str] = None
    chain_code: str
    status: RiskChainStatus
    current_phase: AlertType
    current_level: AlertLevel
    started_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    close_condition: Optional[str] = None
    close_note: Optional[str] = None
    total_alerts: int = 0
    escalation_count: int = 0
    overall_suggestion: Optional[str] = None


class RiskChain(RiskChainBase):
    id: int
    turbine_id: int
    phases: List[RiskPhase] = []

    class Config:
        from_attributes = True


class RiskChainDetail(RiskChain):
    alerts: List[Alert] = []


class RiskChainCloseRequest(BaseModel):
    close_note: Optional[str] = None
    close_condition: Optional[str] = None
    operator: str


class RiskChainListResponse(BaseModel):
    total: int
    items: List[RiskChain]

