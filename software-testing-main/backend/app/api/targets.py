from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Target
from pydantic import BaseModel

router = APIRouter(prefix="/targets", tags=["targets"])

class TargetCreate(BaseModel):
    name: str
    host: str
    description: str

@router.post("/")
def create_target(target: TargetCreate, db: Session = Depends(get_db)):
    db_target = Target(**target.model_dump())
    db.add(db_target)
    db.commit()
    db.refresh(db_target)
    return db_target

@router.get("/")
def list_targets(db: Session = Depends(get_db)):
    return db.query(Target).all()
