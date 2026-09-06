from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import CORS_ORIGINS
from app.api.v1.router import api_router
app=FastAPI(title='Reliability Twin API',version='0.2.0')
app.add_middleware(CORSMiddleware,allow_origins=CORS_ORIGINS,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
app.include_router(api_router,prefix='/api/v1')
@app.get('/')
def root(): return {'name':'Reliability Twin','version':'0.2.0'}
@app.get('/health')
def health(): return {'status':'healthy','service':'industrial-digital-twin'}
@app.on_event('startup')
def startup():
 try:
  from app.startup import seed_hierarchy_if_needed; seed_hierarchy_if_needed()
 except Exception as e: print('[startup]',e)
