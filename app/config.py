from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./wind_turbine.db"
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "高海拔风电机组运行监控系统"

    class Config:
        case_sensitive = True


settings = Settings()
