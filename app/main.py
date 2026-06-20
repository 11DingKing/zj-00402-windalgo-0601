from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import turbines, operating_data, alerts, statistics

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="高海拔风电机组运行监控告警系统 - 实时监测机组运行状态，智能识别失速倾向、涡激振荡、温控异常和功率偏离等风险",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(turbines.router, prefix=settings.API_V1_STR, tags=["机组管理"])
app.include_router(operating_data.router, prefix=settings.API_V1_STR, tags=["运行数据"])
app.include_router(alerts.router, prefix=settings.API_V1_STR, tags=["告警管理"])
app.include_router(statistics.router, prefix=settings.API_V1_STR, tags=["统计分析"])


@app.get("/", tags=["系统"])
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "running",
        "api_docs": "/docs"
    }


@app.get("/health", tags=["系统"])
async def health_check():
    return {"status": "healthy"}
