from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.database.session import get_db
from app.database.models import Target, User
from app.auth.deps import get_current_user
from app.services.runner import CommandRunner

router = APIRouter(prefix="/targets", tags=["targets"])

class TargetCreate(BaseModel):
    name: str
    host: str
    description: Optional[str] = None

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        clean_host = v.strip()
        if not CommandRunner.validate_target_host(clean_host):
            raise ValueError("Target host must be a valid domain name, IPv4, IPv6, or localhost.")
        return clean_host

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean_name = v.strip()
        if not clean_name:
            raise ValueError("Target name cannot be empty.")
        return clean_name

from pydantic import BaseModel, field_validator, ConfigDict

class TargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    host: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

@router.post("", response_model=TargetResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TargetResponse, status_code=status.HTTP_201_CREATED)
async def create_target(
    target_in: TargetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_target = Target(
        name=target_in.name,
        host=target_in.host,
        description=target_in.description,
        user_id=current_user.id
    )
    db.add(new_target)
    await db.commit()
    await db.refresh(new_target)
    return new_target

@router.get("", response_model=List[TargetResponse])
@router.get("/", response_model=List[TargetResponse])
async def list_targets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Target).where(Target.user_id == current_user.id).order_by(Target.id.desc())
    result = await db.execute(query)
    return result.scalars().all()

@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    target_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Target).where(Target.id == target_id, Target.user_id == current_user.id))
    target = result.scalars().first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    await db.delete(target)
    await db.commit()
    return None
