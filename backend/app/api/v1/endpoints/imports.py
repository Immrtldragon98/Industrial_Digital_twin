from pathlib import Path
from fastapi import APIRouter,Depends,UploadFile,File,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import ImportJob,User
from app.services.auth_service import require_roles
from app.ingestion.excel.hierarchy import import_hierarchy
from app.ingestion.excel.sap_data import import_sap_data
router=APIRouter()
@router.post('/hierarchy')
async def upload_hierarchy(file:UploadFile=File(...),db:Session=Depends(get_db),_:User=Depends(require_roles('admin'))):
 if Path(file.filename or '').suffix.lower() not in {'.xlsx','.xls'}: raise HTTPException(400,'Upload an Excel file')
 target=Path('/tmp')/(file.filename or 'hierarchy.xlsx'); target.write_bytes(await file.read())
 job=ImportJob(filename=file.filename or 'unknown',import_type='HIERARCHY',status='PROCESSING'); db.add(job); db.commit(); db.refresh(job)
 try:
  result=import_hierarchy(db,str(target)); job.status='COMPLETED' if not result['errors'] else 'COMPLETED_WITH_ERRORS'; job.rows_read=result['rows_read']; job.rows_created=result['rows_created']; job.rows_updated=result['rows_updated']; job.rows_skipped=result['rows_skipped']; job.errors=result['errors']; db.commit(); return {'job_id':job.id,'status':job.status,**result}
 except Exception as e:
  job.status='FAILED'; job.errors=[{'error':str(e)}]; db.commit(); raise HTTPException(400,str(e))
@router.post('/sap/{import_type}')
async def upload_sap(import_type:str,file:UploadFile=File(...),db:Session=Depends(get_db),_:User=Depends(require_roles('engineer','admin'))):
 if import_type not in {'condition','maintenance','failure','changes'}: raise HTTPException(400,'Type must be condition, maintenance, failure, or changes')
 if Path(file.filename or '').suffix.lower() not in {'.xlsx','.xls'}: raise HTTPException(400,'Upload an Excel file')
 target=Path('/tmp')/f'{import_type}_{file.filename or "import.xlsx"}'; target.write_bytes(await file.read())
 job=ImportJob(filename=file.filename or 'unknown',import_type=import_type.upper(),status='PROCESSING'); db.add(job); db.commit(); db.refresh(job)
 try:
  result=import_sap_data(db,str(target),import_type); job.status='COMPLETED' if not result['errors'] else 'COMPLETED_WITH_ERRORS'; job.rows_read=result['rows_read']; job.rows_created=result['rows_created']; job.rows_updated=result['rows_updated']; job.rows_skipped=result['rows_skipped']; job.errors=result['errors']; db.commit(); return {'job_id':job.id,'status':job.status,**result}
 except Exception as exc: job.status='FAILED'; job.errors=[{'error':str(exc)}]; db.commit(); raise HTTPException(400,str(exc))
