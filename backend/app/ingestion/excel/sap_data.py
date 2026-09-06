from datetime import datetime
import pandas as pd
from app.models.models import Equipment, Parameter, ConditionReading, MaintenanceEvent, Failure, ComponentChange

ALIASES={
 'equipment_number':['equipment','equipment number','equipment no','eq no','technical object'],
 'timestamp':['timestamp','reading date','date time','measuring time'], 'value':['value','measurement reading','reading'],
 'parameter_code':['parameter code','measurement point','measuring point','characteristic'], 'parameter_name':['parameter name','parameter','description'],
 'unit':['unit','uom'], 'order':['order','order number','maintenance order','sap order'], 'notification':['notification','notification number'],
 'description':['description','long text','short text','problem'], 'start':['start','actual start','malfunction start'], 'end':['end','actual end','malfunction end'],
 'downtime':['downtime','breakdown duration','downtime hours'], 'component':['component','component name','part'], 'reason':['reason','cause','change reason']}
def norm(v): return str(v).strip().lower().replace('_',' ') if v is not None else ''
def colmap(df):
 result={}; cols={norm(c):c for c in df.columns}
 for key,names in ALIASES.items():
  for name in names:
   if name in cols: result[key]=cols[name]; break
 return result
def val(row,m,key,default=None):
 v=row.get(m.get(key)) if m.get(key) is not None else default
 return default if pd.isna(v) else v
def equipment(db,number): return db.query(Equipment).filter(Equipment.equipment_number==str(number).strip()).first()
def import_sap_data(db,path,kind):
 df=pd.read_excel(path); m=colmap(df); created=skipped=0; errors=[]
 if 'equipment_number' not in m: raise ValueError('Equipment Number column is required')
 for index,row in df.iterrows():
  try:
   eq=equipment(db,val(row,m,'equipment_number'))
   if not eq: skipped+=1; errors.append({'row':int(index)+2,'error':'Equipment not mapped'}); continue
   if kind=='condition':
    code=str(val(row,m,'parameter_code',val(row,m,'parameter_name','PARAM'))).strip(); p=db.query(Parameter).filter(Parameter.equipment_id==eq.id,Parameter.parameter_code==code).first()
    if not p: p=Parameter(equipment_id=eq.id,parameter_code=code,name=str(val(row,m,'parameter_name',code)),unit=str(val(row,m,'unit','')),source='sap_excel'); db.add(p); db.flush()
    db.add(ConditionReading(parameter_id=p.id,timestamp=pd.to_datetime(val(row,m,'timestamp')).to_pydatetime(),value=float(val(row,m,'value')),source='sap_excel'))
   elif kind=='maintenance': db.add(MaintenanceEvent(equipment_id=eq.id,sap_order_number=str(val(row,m,'order','')),title=str(val(row,m,'description','Maintenance event')),description=str(val(row,m,'description','')),actual_start=pd.to_datetime(val(row,m,'start')).to_pydatetime() if val(row,m,'start') else None,actual_end=pd.to_datetime(val(row,m,'end')).to_pydatetime() if val(row,m,'end') else None,downtime_hours=float(val(row,m,'downtime',0) or 0),source='sap_excel'))
   elif kind=='failure': db.add(Failure(equipment_id=eq.id,notification_number=str(val(row,m,'notification','')),failure_start=pd.to_datetime(val(row,m,'start')).to_pydatetime() if val(row,m,'start') else None,failure_end=pd.to_datetime(val(row,m,'end')).to_pydatetime() if val(row,m,'end') else None,description=str(val(row,m,'description','')),failure_cause=str(val(row,m,'reason','')),downtime_hours=float(val(row,m,'downtime',0) or 0),breakdown=True))
   elif kind=='changes': db.add(ComponentChange(equipment_id=eq.id,changed_at=pd.to_datetime(val(row,m,'timestamp',datetime.utcnow())).to_pydatetime(),component_name=str(val(row,m,'component','Component')),reason=str(val(row,m,'reason','')),sap_order_number=str(val(row,m,'order','')),source='sap_excel'))
   created+=1
  except Exception as exc: skipped+=1; errors.append({'row':int(index)+2,'error':str(exc)})
 db.commit(); return {'rows_read':len(df),'rows_created':created,'rows_updated':0,'rows_skipped':skipped,'errors':errors,'detected_columns':{k:str(v) for k,v in m.items()}}
