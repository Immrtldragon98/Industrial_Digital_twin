from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Equipment
from app.services.reliability_service import calculate_metrics
router=APIRouter()
@router.get('/summary')
def summary(db:Session=Depends(get_db)):
 eqs=db.query(Equipment).filter(or_(Equipment.equipment_type.is_(None),Equipment.equipment_type.notin_(['ASSEMBLY','COMPONENT','STAND','STAND_SYSTEM']))).all(); metrics=[calculate_metrics(db,e.id) for e in eqs]
 availability=[item['availability_percent'] for item in metrics if item['availability_percent'] is not None]
 reliability=[item['reliability_score'] for item in metrics if item['reliability_score'] is not None]
 return {'equipment_count':len(metrics),'average_availability':round(sum(availability)/len(availability),2) if availability else None,'average_reliability':round(sum(reliability)/len(reliability),2) if reliability else None,'high_risk_count':sum(item['risk_score'] is not None and item['risk_score']>=60 for item in metrics),'metrics_ready_count':len(availability)}
@router.get('/equipment/{equipment_id}')
def eq_rel(equipment_id:str,db:Session=Depends(get_db)):
 if not db.get(Equipment,equipment_id): raise HTTPException(404,'Equipment not found')
 return calculate_metrics(db,equipment_id)
