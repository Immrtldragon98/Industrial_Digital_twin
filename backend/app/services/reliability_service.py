def calculate_metrics(db,equipment_id):
 from app.models.models import Failure
 failures=db.query(Failure).filter(Failure.equipment_id==equipment_id).all()
 count=len(failures); downtime=sum((f.downtime_hours or 0) for f in failures); observation=8760.0
 mtbf=observation/count if count else observation; mttr=downtime/count if count else 0.0
 availability=max(0.0,min(100.0,(observation-downtime)/observation*100))
 reliability=max(0.0,min(100.0,availability-min(count*2.0,30.0))); risk=100-reliability
 return {'equipment_id':equipment_id,'mtbf_hours':round(mtbf,2),'mttr_hours':round(mttr,2),'availability_percent':round(availability,2),'failure_count':count,'downtime_hours':round(downtime,2),'reliability_score':round(reliability,2),'risk_score':round(risk,2)}
