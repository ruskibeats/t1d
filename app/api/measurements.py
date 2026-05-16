from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.measurements.schemas import CustomMeasurementCreate, CustomMeasurementResponse
from app.measurements.service import MeasurementService

route = APIRouter(prefix="/measurements", tags=["measurements"])

@route.post("", response_model=CustomMeasurementResponse, status_code=status.HTTP_201_CREATED)
async def create_measurement(data: CustomMeasurementCreate, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    return await MeasurementService(db).create_measurement(user_id, data)

@route.get("", response_model=list[CustomMeasurementResponse])
async def list_measurements(
    user_id: int = Query(..., ge=1), 
    limit: int = 100, 
    offset: int = 0,
    metric_name: str = Query(None, max_length=100),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    from datetime import datetime
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    return await MeasurementService(db).list_measurements(
        user_id=user_id, 
        limit=limit, 
        offset=offset,
        metric_name=metric_name,
        start_date=start,
        end_date=end
    )

@route.get("/{measurement_id}", response_model=CustomMeasurementResponse)
async def get_measurement(measurement_id: int, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    measurement = await MeasurementService(db).get_measurement(user_id, measurement_id)
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    return measurement

@route.put("/{measurement_id}", response_model=CustomMeasurementResponse)
async def update_measurement(measurement_id: int, data: CustomMeasurementCreate, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    measurement = await MeasurementService(db).update_measurement(user_id, measurement_id, data)
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    return measurement

@route.delete("/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_measurement(measurement_id: int, user_id: int = Query(..., ge=1), db: AsyncSession = Depends(get_db)):
    success = await MeasurementService(db).delete_measurement(user_id, measurement_id)
    if not success:
        raise HTTPException(status_code=404, detail="Measurement not found")

@route.get("/stats/{metric_name}")
async def get_metric_stats(
    metric_name: str,
    user_id: int = Query(..., ge=1),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    from datetime import datetime
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    stats = await MeasurementService(db).get_metric_stats(user_id, metric_name, start, end)
    if not stats:
        raise HTTPException(status_code=404, detail="No measurements found for this metric")
    return stats