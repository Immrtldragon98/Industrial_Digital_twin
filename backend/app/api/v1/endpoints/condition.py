from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import ConditionReading
from app.schemas.schemas import ConditionReadingCreate
router=APIRouter()
@router.post('/readings')
def create_reading(payload:ConditionReadingCreate,db:Session=Depends(get_db)):
 obj=ConditionReading(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return {'id':obj.id,'status':'created'}
