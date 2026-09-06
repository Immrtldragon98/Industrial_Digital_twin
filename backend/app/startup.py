from pathlib import Path
from app.core.database import SessionLocal
from app.models.models import FunctionalLocation
from app.ingestion.excel.hierarchy import import_hierarchy
def seed_hierarchy_if_needed():
 path=Path('/data/raw/hiearcy.xlsx'); db=SessionLocal()
 try:
  if path.exists() and db.query(FunctionalLocation).count()==0: print(import_hierarchy(db,str(path)))
 finally: db.close()
