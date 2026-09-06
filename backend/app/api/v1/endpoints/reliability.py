from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Equipment
from app.services.reliability_service import calculate_metrics
router=APIRouter()
@router.get('/summary')
def summary(db:Session=Depends(get_db)):
 eqs=db.query(Equipment).all(); m=[calculate_metrics(db,e.id) for e in eqs]
 return {'equipment_count':len(m),'average_availability':round(sum(x['availability_percent'] for x in m)/len(m),2) if m else 0,'average_reliability':round(sum(x['reliability_score'] for x in m)/len(m),2) if m else 0,'high_risk_count':sum(x['risk_score']>=60 for x in m)}
@router.get('/equipment/{equipment_id}')
def eq_rel(equipment_id:str,db:Session=Depends(get_db)):
 if not db.get(Equipment,equipment_id): raise HTTPException(404,'Equipment not found')
 return calculate_metrics(db,equipment_id)
