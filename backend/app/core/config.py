import os
DATABASE_URL=os.getenv("DATABASE_URL","postgresql+psycopg://digital_twin:digital_twin_dev@localhost:5432/digital_twin")
CORS_ORIGINS=[x.strip() for x in os.getenv("CORS_ORIGINS","http://localhost:3000").split(",") if x.strip()]
OLLAMA_URL=os.getenv('OLLAMA_URL','http://localhost:11434')
OLLAMA_CHAT_MODEL=os.getenv('OLLAMA_CHAT_MODEL','qwen3:1.7b')
EMBEDDING_MODEL=os.getenv('EMBEDDING_MODEL','embeddinggemma')
AI_ENABLED=os.getenv('AI_ENABLED','false').lower()=='true'
UPLOAD_DIR=os.getenv('UPLOAD_DIR','/data/documents')
AUTH_SECRET=os.getenv('AUTH_SECRET','development-only-change-this-secret')
AUTH_TOKEN_HOURS=int(os.getenv('AUTH_TOKEN_HOURS','12'))
ADMIN_USERNAME=os.getenv('ADMIN_USERNAME','admin')
ADMIN_PASSWORD=os.getenv('ADMIN_PASSWORD','change-me-now')
