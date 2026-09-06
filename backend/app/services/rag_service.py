import httpx
from sqlalchemy import or_
from app.core.config import AI_ENABLED,OLLAMA_URL,OLLAMA_CHAT_MODEL
from app.models.models import Document,DocumentChunk
from app.services.knowledge_service import embed

SYSTEM='''You are a plant reliability engineering copilot for mechanical, electrical, operations and SAP PM work. Use ONLY the supplied plant evidence for plant-specific claims. Separate observed facts, calculations, hypotheses and recommended checks. Never invent equipment codes, measurements, limits, causes or SAP records. If evidence is insufficient, state exactly what is missing. Cite evidence using [S1], [S2]. Do not issue automatic SAP changes or unsafe operating instructions.'''

def retrieve(db,question,equipment_id=None,limit=6):
 base=db.query(DocumentChunk,Document).join(Document,Document.id==DocumentChunk.document_id)
 if equipment_id: base=base.filter(Document.equipment_id==equipment_id)
 mode='semantic'
 try:
  vector=embed([question])[0]
  rows=base.filter(DocumentChunk.embedding.is_not(None)).order_by(DocumentChunk.embedding.cosine_distance(vector)).limit(limit).all()
 except Exception:
  mode='keyword-fallback'; terms=[x for x in question.split() if len(x)>3][:8]
  query=base
  if terms: query=query.filter(or_(*[DocumentChunk.content.ilike(f'%{term}%') for term in terms]))
  rows=query.limit(limit).all()
 return mode,[{'source_id':f'S{i+1}','document_id':str(d.id),'title':d.title,'document_type':d.document_type,'equipment_id':str(d.equipment_id) if d.equipment_id else None,'chunk_index':c.chunk_index,'excerpt':c.content[:900]} for i,(c,d) in enumerate(rows)]

def answer(db,question,equipment_id=None):
 mode,sources=retrieve(db,question,equipment_id)
 if not sources: return {'answer':'Insufficient plant data: no relevant indexed evidence was found.','sources':[],'retrieval_mode':mode,'model_status':'not_called'}
 if not AI_ENABLED: return {'answer':'AI generation is disabled. Relevant evidence is shown below.','sources':sources,'retrieval_mode':mode,'model_status':'disabled'}
 evidence='\n\n'.join(f"[{s['source_id']}] {s['title']}\n{s['excerpt']}" for s in sources)
 try:
  response=httpx.post(f'{OLLAMA_URL}/api/chat',json={'model':OLLAMA_CHAT_MODEL,'stream':False,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':f'Question: {question}\n\nPlant evidence:\n{evidence}'}]},timeout=120)
  response.raise_for_status(); content=response.json()['message']['content']
  return {'answer':content,'sources':sources,'retrieval_mode':mode,'model_status':'online','model':OLLAMA_CHAT_MODEL}
 except Exception:
  return {'answer':'The local AI model is offline. The core twin remains available; review the retrieved evidence below.','sources':sources,'retrieval_mode':mode,'model_status':'offline'}
