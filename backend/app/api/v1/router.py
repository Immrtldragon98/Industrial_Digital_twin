from fastapi import APIRouter,Depends
from app.api.v1.endpoints import auth,health,equipment,reliability,condition,imports,knowledge
from app.services.auth_service import get_current_user
api_router=APIRouter()
api_router.include_router(health.router,prefix='/health',tags=['Health'])
api_router.include_router(auth.router,prefix='/auth',tags=['Authentication'])
protected=[Depends(get_current_user)]
api_router.include_router(equipment.router,prefix='/equipment',tags=['Equipment'],dependencies=protected)
api_router.include_router(reliability.router,prefix='/reliability',tags=['Reliability'],dependencies=protected)
api_router.include_router(condition.router,prefix='/condition',tags=['Condition'],dependencies=protected)
api_router.include_router(imports.router,prefix='/imports',tags=['Imports'],dependencies=protected)
api_router.include_router(knowledge.router,prefix='/knowledge',tags=['Knowledge & RAG'],dependencies=protected)
