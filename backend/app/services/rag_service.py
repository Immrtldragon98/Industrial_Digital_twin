import httpx
from sqlalchemy import or_
from app.core.config import AI_ENABLED,OLLAMA_URL,OLLAMA_CHAT_MODEL
from app.models.models import Document,DocumentChunk
from app.services.equipment_context_service import equipment_scope_ids,history_card,parameter_snapshot
from app.services.knowledge_service import embed

SYSTEM='''You are a senior plant reliability engineer teaching mechanical, electrical and operations engineers. Use ONLY the supplied plant evidence for plant-specific claims. Separate observed facts, calculations, hypotheses, life-extension actions and recommended checks. Explain why each recommendation matters in clear engineering language. Never invent equipment codes, measurements, limits, causes or SAP records. Do not claim causation from correlation. If evidence is insufficient, state exactly what is missing. Cite every plant-specific claim using [S1], [S2] style source IDs. Do not issue automatic SAP changes, bypass safety controls or provide unsafe operating instructions.'''

def retrieve(db,question,equipment_id=None,limit=6):
 base=db.query(DocumentChunk,Document).join(Document,Document.id==DocumentChunk.document_id)
 if equipment_id: base=base.filter(Document.equipment_id.in_(equipment_scope_ids(db,equipment_id)))
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

def operational_evidence(db,equipment_id,start_index=1):
 if not equipment_id: return []
 snapshots=parameter_snapshot(db,equipment_id,history_limit=3)
 card=history_card(db,equipment_id)
 sources=[]
 if snapshots:
  lines=[]
  for item in snapshots[:30]:
   latest=item['latest']
   reading='no reading' if not latest else f"{latest['value']} {item['unit'] or ''} at {latest['timestamp']}"
   lines.append(f"{item['equipment_number']} / {item['name']}: {reading}; status {item['status']}; limits {item['limits']}")
  sources.append({'source_id':f'S{start_index}','title':'Current parameter snapshot','document_type':'LIVE_CONDITION','equipment_id':str(equipment_id),'chunk_index':0,'excerpt':'\n'.join(lines)})
 if card['timeline']:
  lines=[]
  for item in card['timeline'][:30]:
   lines.append(f"{item['date']} | {item['type']} | {item.get('equipment_number')} | {item['title']} | {item.get('description') or ''} | SAP {item.get('sap_reference') or 'not recorded'} | downtime {item.get('downtime_hours')}")
  sources.append({'source_id':f'S{start_index+len(sources)}','title':'Equipment history card','document_type':'HISTORY_CARD','equipment_id':str(equipment_id),'chunk_index':0,'excerpt':'\n'.join(lines)})
 metrics=card['metrics']
 sources.append({'source_id':f'S{start_index+len(sources)}','title':'Calculated reliability metrics','document_type':'CALCULATION','equipment_id':str(equipment_id),'chunk_index':0,'excerpt':f"Observation {metrics['observation_hours']} h from {metrics['observation_start']}; operating time {metrics['operating_hours']} h; MTBF {metrics['mtbf_hours']} h; MTTR {metrics['mttr_hours']} h; availability {metrics['availability_percent']}%; failures {metrics['failure_count']}; downtime {metrics['downtime_hours']} h. Basis: {metrics['calculation_basis']}."})
 return sources

def answer(db,question,equipment_id=None,coach=False):
 mode,sources=retrieve(db,question,equipment_id)
 operational=operational_evidence(db,equipment_id)
 if operational:
  for index,source in enumerate(sources,start=len(operational)+1): source['source_id']=f'S{index}'
  sources=operational+sources
 if not sources: return {'answer':'Insufficient plant data: no relevant indexed evidence was found.','sources':[],'retrieval_mode':mode,'model_status':'not_called'}
 if not AI_ENABLED: return {'answer':'AI generation is disabled. Relevant evidence is shown below.','sources':sources,'retrieval_mode':mode,'model_status':'disabled'}
 evidence='\n\n'.join(f"[{s['source_id']}] {s['title']}\n{s['excerpt']}" for s in sources)
 try:
  learning_format='''\nUse this response structure:\n1. Current health\n2. What the history indicates\n3. Actions that can increase equipment life\n4. Checks and measurements to perform\n5. Missing evidence\n6. Engineer learning note (explain the reliability principle).''' if coach else ''
  response=httpx.post(f'{OLLAMA_URL}/api/chat',json={'model':OLLAMA_CHAT_MODEL,'stream':False,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':f'Question: {question}{learning_format}\n\nPlant evidence:\n{evidence}'}]},timeout=120)
  response.raise_for_status(); content=response.json()['message']['content']
  return {'answer':content,'sources':sources,'retrieval_mode':mode,'model_status':'online','model':OLLAMA_CHAT_MODEL}
 except Exception:
  return {'answer':'The local AI model is offline. The core twin remains available; review the retrieved evidence below.','sources':sources,'retrieval_mode':mode,'model_status':'offline'}
