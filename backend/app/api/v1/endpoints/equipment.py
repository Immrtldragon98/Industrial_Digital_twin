import re
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Equipment,FunctionalLocation,Parameter,ConditionReading,MaintenanceEvent,Failure,ComponentChange,User
from app.schemas.schemas import EquipmentOut,EquipmentCreate,ComponentChangeCreate
from app.services.auth_service import require_roles
from app.services.equipment_context_service import history_card,parameter_snapshot
router=APIRouter()
def line_for(equipment,by_id):
 current=equipment
 while current:
  metadata=current.metadata_json or {}
  searchable=' '.join([current.name or '',current.equipment_number or '',metadata.get('source_object_id',''),*metadata.get('aliases',[])])
  match=re.search(r'(?:WRM|WIRE ROD MILL)[\s_-]*0?([123])\b',searchable,re.IGNORECASE)
  if match: return f'WRM{match.group(1)}'
  current=by_id.get(current.parent_equipment_id)
 return None
@router.get('',response_model=list[EquipmentOut])
def list_equipment(db:Session=Depends(get_db),limit:int=200,include_parts:bool=False):
 query=db.query(Equipment)
 if not include_parts: query=query.filter(or_(Equipment.equipment_type.is_(None),Equipment.equipment_type.notin_(['ASSEMBLY','COMPONENT','STAND','STAND_SYSTEM'])))
 items=query.order_by(Equipment.name).limit(min(limit,1000)).all()
 by_id={item.id:item for item in db.query(Equipment).all()}
 return [{**EquipmentOut.model_validate(item).model_dump(),'wrm_line':line_for(item,by_id)} for item in items]
@router.post('',response_model=EquipmentOut)
def create_equipment(payload:EquipmentCreate,db:Session=Depends(get_db),_:User=Depends(require_roles('admin'))):
 if db.query(Equipment).filter(Equipment.equipment_number==payload.equipment_number).first(): raise HTTPException(409,'Equipment number already exists')
 obj=Equipment(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
@router.get('/tree')
def tree(db:Session=Depends(get_db)):
 fls=db.query(FunctionalLocation).order_by(FunctionalLocation.level,FunctionalLocation.code).all(); eqs=db.query(Equipment).order_by(Equipment.name).all()
 by_id={e.id:e for e in eqs}
 nodes={str(f.id):{'id':str(f.id),'type':'functional_location','code':f.code,'name':f.name,'level':f.level,'children':[]} for f in fls}; roots=[]
 for f in fls:
  n=nodes[str(f.id)]
  if f.parent_id and str(f.parent_id) in nodes: nodes[str(f.parent_id)]['children'].append(n)
  else: roots.append(n)
 equipment_nodes={str(e.id):{'id':str(e.id),'type':(e.equipment_type or 'equipment').lower(),'code':e.equipment_number,'name':e.name,'status':e.status,'wrm_line':line_for(e,by_id),'children':[]} for e in eqs}
 for e in eqs:
  node=equipment_nodes[str(e.id)]
  if e.parent_equipment_id and str(e.parent_equipment_id) in equipment_nodes: equipment_nodes[str(e.parent_equipment_id)]['children'].append(node)
  elif e.functional_location_id and str(e.functional_location_id) in nodes: nodes[str(e.functional_location_id)]['children'].append(node)
 return roots
@router.get('/{equipment_id}',response_model=EquipmentOut)
def get_equipment(equipment_id:str,db:Session=Depends(get_db)):
 obj=db.get(Equipment,equipment_id)
 if not obj: raise HTTPException(404,'Equipment not found')
 return obj
@router.get('/{equipment_id}/twin')
def get_twin(equipment_id:str,db:Session=Depends(get_db)):
 obj=db.get(Equipment,equipment_id)
 if not obj: raise HTTPException(404,'Equipment not found')
 parameters=[]
 for p in db.query(Parameter).filter(Parameter.equipment_id==equipment_id).all():
  latest=db.query(ConditionReading).filter(ConditionReading.parameter_id==p.id).order_by(ConditionReading.timestamp.desc()).first()
  parameters.append({'parameter_id':str(p.id),'code':p.parameter_code,'name':p.name,'unit':p.unit,'normal_min':p.normal_min,'normal_max':p.normal_max,'latest':None if not latest else {'value':latest.value,'timestamp':latest.timestamp,'quality':latest.quality}})
 def rows(query): return [{c.name:getattr(x,c.name) for c in x.__table__.columns} for x in query]
 return {'equipment':EquipmentOut.model_validate(obj),'parameters':parameters,'maintenance_events':rows(db.query(MaintenanceEvent).filter(MaintenanceEvent.equipment_id==equipment_id).order_by(MaintenanceEvent.actual_start.desc()).limit(50)),'failures':rows(db.query(Failure).filter(Failure.equipment_id==equipment_id).order_by(Failure.failure_start.desc()).limit(50)),'component_changes':rows(db.query(ComponentChange).filter(ComponentChange.equipment_id==equipment_id).order_by(ComponentChange.changed_at.desc()).limit(50))}
@router.get('/{equipment_id}/parameters')
def get_parameters(equipment_id:str,db:Session=Depends(get_db),history_limit:int=30):
 if not db.get(Equipment,equipment_id): raise HTTPException(404,'Equipment not found')
 return parameter_snapshot(db,equipment_id,history_limit)
@router.get('/{equipment_id}/history-card')
def get_history_card(equipment_id:str,db:Session=Depends(get_db)):
 if not db.get(Equipment,equipment_id): raise HTTPException(404,'Equipment not found')
 return history_card(db,equipment_id)
@router.post('/changes')
def create_change(payload:ComponentChangeCreate,db:Session=Depends(get_db),_:User=Depends(require_roles('engineer','admin'))):
 if not db.get(Equipment,payload.equipment_id): raise HTTPException(404,'Equipment not found')
 obj=ComponentChange(**payload.model_dump(),source='manual'); db.add(obj); db.commit(); db.refresh(obj); return {'id':obj.id,'status':'created'}
