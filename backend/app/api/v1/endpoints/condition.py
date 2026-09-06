from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import ConditionReading,User
from app.schemas.schemas import ConditionReadingCreate
from app.services.auth_service import require_roles
router=APIRouter()
@router.post('/readings')
def create_reading(payload:ConditionReadingCreate,db:Session=Depends(get_db),_:User=Depends(require_roles('engineer','admin'))):
 obj=ConditionReading(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return {'id':obj.id,'status':'created'}
