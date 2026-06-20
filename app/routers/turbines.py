from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Turbine
from app.schemas import TurbineCreate, Turbine as TurbineSchema

router = APIRouter(prefix="/turbines")


@router.post("", response_model=TurbineSchema, summary="新增机组")
def create_turbine(turbine_in: TurbineCreate, db: Session = Depends(get_db)):
    existing = db.query(Turbine).filter(Turbine.turbine_code == turbine_in.turbine_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"机组编号 {turbine_in.turbine_code} 已存在")

    turbine = Turbine(**turbine_in.model_dump())
    db.add(turbine)
    db.commit()
    db.refresh(turbine)
    return turbine


@router.get("", response_model=List[TurbineSchema], summary="获取机组列表")
def get_turbines(ridge_name: str = None, db: Session = Depends(get_db)):
    query = db.query(Turbine)
    if ridge_name:
        query = query.filter(Turbine.ridge_name == ridge_name)
    return query.order_by(Turbine.ridge_name, Turbine.position).all()


@router.get("/{turbine_code}", response_model=TurbineSchema, summary="获取机组详情")
def get_turbine(turbine_code: str, db: Session = Depends(get_db)):
    turbine = db.query(Turbine).filter(Turbine.turbine_code == turbine_code).first()
    if not turbine:
        raise HTTPException(status_code=404, detail=f"机组 {turbine_code} 不存在")
    return turbine


@router.put("/{turbine_code}", response_model=TurbineSchema, summary="更新机组信息")
def update_turbine(turbine_code: str, turbine_in: TurbineCreate, db: Session = Depends(get_db)):
    turbine = db.query(Turbine).filter(Turbine.turbine_code == turbine_code).first()
    if not turbine:
        raise HTTPException(status_code=404, detail=f"机组 {turbine_code} 不存在")

    for key, value in turbine_in.model_dump().items():
        setattr(turbine, key, value)

    db.commit()
    db.refresh(turbine)
    return turbine


@router.delete("/{turbine_code}", summary="删除机组")
def delete_turbine(turbine_code: str, db: Session = Depends(get_db)):
    turbine = db.query(Turbine).filter(Turbine.turbine_code == turbine_code).first()
    if not turbine:
        raise HTTPException(status_code=404, detail=f"机组 {turbine_code} 不存在")

    db.delete(turbine)
    db.commit()
    return {"message": f"机组 {turbine_code} 已删除"}
