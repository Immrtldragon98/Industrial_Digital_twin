from datetime import datetime
from uuid import UUID
from pydantic import BaseModel,ConfigDict
class EquipmentOut(BaseModel):
 model_config=ConfigDict(from_attributes=True)
 id:UUID; equipment_number:str|None=None; functional_location_id:UUID|None=None; parent_equipment_id:UUID|None=None; name:str; equipment_type:str|None=None; criticality:str|None=None; status:str
class ConditionReadingCreate(BaseModel):
 parameter_id:UUID; timestamp:datetime; value:float|None=None; quality:str='GOOD'; source:str|None=None
class EquipmentCreate(BaseModel):
 equipment_number:str; name:str; functional_location_id:UUID|None=None; parent_equipment_id:UUID|None=None; equipment_type:str|None=None; criticality:str|None=None; status:str='UNKNOWN'
class ComponentChangeCreate(BaseModel):
 equipment_id:UUID; changed_at:datetime; component_name:str; old_component:str|None=None; new_component:str|None=None; reason:str|None=None; performed_by:str|None=None; sap_order_number:str|None=None; running_hours:float|None=None
