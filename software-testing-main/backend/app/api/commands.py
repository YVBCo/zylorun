from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import CommandConfig
from pydantic import BaseModel
import json

router = APIRouter(prefix="/commands", tags=["commands"])

class CommandCreate(BaseModel):
    name: str
    executable: str
    allowed_args: list[str]
    timeout_seconds: int = 60
    regex_rules: dict

from fastapi import HTTPException

@router.post("/")
def create_command(cmd: CommandCreate, db: Session = Depends(get_db)):
    existing = db.query(CommandConfig).filter(CommandConfig.name == cmd.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Command with this name already exists.")
    db_cmd = CommandConfig(
        name=cmd.name,
        executable=cmd.executable,
        allowed_args=json.dumps(cmd.allowed_args),
        timeout_seconds=cmd.timeout_seconds,
        regex_rules=json.dumps(cmd.regex_rules)
    )
    db.add(db_cmd)
    db.commit()
    db.refresh(db_cmd)
    return db_cmd

@router.get("/")
def list_commands(db: Session = Depends(get_db)):
    return db.query(CommandConfig).all()
