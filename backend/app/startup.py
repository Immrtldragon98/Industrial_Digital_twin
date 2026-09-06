from pathlib import Path
from app.core.config import ADMIN_PASSWORD,ADMIN_USERNAME
from app.core.database import SessionLocal,engine
from app.models.models import Base,FunctionalLocation,User
from app.services.auth_service import hash_password
from app.ingestion.excel.hierarchy import import_hierarchy
def seed_hierarchy_if_needed():
 Base.metadata.create_all(bind=engine)
 db=SessionLocal()
 try:
  if not db.query(User).filter(User.username==ADMIN_USERNAME.strip().lower()).first():
   db.add(User(username=ADMIN_USERNAME.strip().lower(),password_hash=hash_password(ADMIN_PASSWORD),role='admin'))
   db.commit()
 finally: db.close()
 path=Path('/data/raw/hiearcy.xlsx'); db=SessionLocal()
 try:
  if path.exists() and db.query(FunctionalLocation).count()==0: print(import_hierarchy(db,str(path)))
 finally: db.close()
