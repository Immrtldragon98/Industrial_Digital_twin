import shutil,uuid
from pathlib import Path
from fastapi import APIRouter,Depends,File,Form,HTTPException,UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import UPLOAD_DIR
from app.core.database import get_db
from app.models.models import Document,DocumentChunk,Equipment
from app.services.knowledge_service import extract_text,chunks,embed,sha256
from app.services.rag_service import answer
router=APIRouter()

class AskRequest(BaseModel): question:str; equipment_id:str|None=None

@router.post('/documents')
async def upload_document(file:UploadFile=File(...),document_type:str=Form('OTHER'),equipment_number:str|None=Form(None),db:Session=Depends(get_db)):
 eq=None
 if equipment_number:
  eq=db.query(Equipment).filter(Equipment.equipment_number==equipment_number.strip()).first()
  if not eq: raise HTTPException(422,'Exact equipment number is not mapped; document was not imported')
 root=Path(UPLOAD_DIR); root.mkdir(parents=True,exist_ok=True)
 safe=f'{uuid.uuid4()}_{Path(file.filename or "document").name}'; target=root/safe
 with target.open('wb') as out: shutil.copyfileobj(file.file,out)
 try: text=extract_text(target)
 except Exception as exc: target.unlink(missing_ok=True); raise HTTPException(400,str(exc))
 if not text.strip(): target.unlink(missing_ok=True); raise HTTPException(422,'No readable text was extracted')
 digest=sha256(target)
 duplicate=db.query(Document).filter(Document.metadata_json['sha256'].astext==digest).first()
 if duplicate: target.unlink(missing_ok=True); return {'status':'duplicate','document_id':duplicate.id,'chunks':db.query(DocumentChunk).filter(DocumentChunk.document_id==duplicate.id).count()}
 doc=Document(equipment_id=eq.id if eq else None,title=file.filename or safe,document_type=document_type.upper(),source='upload',file_path=str(target),content=None,metadata_json={'sha256':digest,'equipment_number':equipment_number}); db.add(doc); db.flush()
 parts=chunks(text); vectors=None
 try: vectors=embed(parts)
 except Exception: vectors=[None]*len(parts)
 for i,(part,vector) in enumerate(zip(parts,vectors)): db.add(DocumentChunk(document_id=doc.id,chunk_index=i,content=part,embedding=vector,metadata_json={'page_or_chunk':i+1}))
 db.commit(); return {'status':'indexed','document_id':doc.id,'chunks':len(parts),'embedding_status':'ready' if any(v is not None for v in vectors) else 'keyword_only'}

@router.post('/ask')
def ask(payload:AskRequest,db:Session=Depends(get_db)):
 if len(payload.question.strip())<3: raise HTTPException(422,'Question is too short')
 if payload.equipment_id and not db.get(Equipment,payload.equipment_id): raise HTTPException(404,'Equipment not found')
 return answer(db,payload.question.strip(),payload.equipment_id)

@router.get('/documents')
def list_documents(db:Session=Depends(get_db)):
 return [{'id':d.id,'title':d.title,'document_type':d.document_type,'equipment_id':d.equipment_id,'created_at':d.created_at,'chunks':db.query(DocumentChunk).filter(DocumentChunk.document_id==d.id).count()} for d in db.query(Document).order_by(Document.created_at.desc()).all()]
