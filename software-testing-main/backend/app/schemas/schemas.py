from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.models.models import RoleEnum

class UserBase(BaseModel):
    username: str
    role: RoleEnum = RoleEnum.viewer

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
