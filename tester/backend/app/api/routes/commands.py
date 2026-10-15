import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any
from datetime import datetime

from app.database.session import get_db
from app.database.models import CommandConfig, User
from app.auth.deps import get_current_user, require_role
from app.services.runner import APPROVED_EXECUTABLES

router = APIRouter(prefix="/commands", tags=["commands"])

class CommandCreate(BaseModel):
    name: str
    executable: str
    allowed_args: Any = []  # Can be list or JSON string
    timeout_seconds: int = 60
    regex_rules: Any = {}  # Can be dict or JSON string

    @field_validator("executable")
    @classmethod
    def validate_executable(cls, v: str) -> str:
        clean = v.strip().lower().split("/")[-1].split("\\")[-1]
        if clean not in APPROVED_EXECUTABLES:
            raise ValueError(f"Executable '{v}' is not in the approved security tools allowlist ({', '.join(sorted(APPROVED_EXECUTABLES))}).")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Command name cannot be empty.")
        return clean

from pydantic import BaseModel, field_validator, ConfigDict

class CommandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    executable: str
    allowed_args: str
    timeout_seconds: int
    regex_rules: str
    created_at: Optional[datetime] = None

@router.post("", response_model=CommandResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=CommandResponse, status_code=status.HTTP_201_CREATED)
async def create_command(
    cmd_in: CommandCreate,
    current_user: User = Depends(require_role(["Admin", "Analyst"])),
    db: AsyncSession = Depends(get_db)
):
    # Check if duplicate name exists
    existing = await db.execute(select(CommandConfig).where(CommandConfig.name == cmd_in.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="A tool with this name already exists.")

    allowed_args_str = json.dumps(cmd_in.allowed_args) if not isinstance(cmd_in.allowed_args, str) else cmd_in.allowed_args
    regex_rules_str = json.dumps(cmd_in.regex_rules) if not isinstance(cmd_in.regex_rules, str) else cmd_in.regex_rules

    new_cmd = CommandConfig(
        name=cmd_in.name,
        executable=cmd_in.executable,
        allowed_args=allowed_args_str,
        timeout_seconds=min(max(cmd_in.timeout_seconds, 5), 300),
        regex_rules=regex_rules_str
    )
    db.add(new_cmd)
    await db.commit()
    await db.refresh(new_cmd)
    return new_cmd

@router.get("", response_model=List[CommandResponse])
@router.get("/", response_model=List[CommandResponse])
async def list_commands(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(CommandConfig).order_by(CommandConfig.id.asc())
    result = await db.execute(query)
    return result.scalars().all()

@router.delete("/{command_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_command(
    command_id: int,
    current_user: User = Depends(require_role(["Admin"])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CommandConfig).where(CommandConfig.id == command_id))
    cmd = result.scalars().first()
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")

    await db.delete(cmd)
    await db.commit()
    return None
