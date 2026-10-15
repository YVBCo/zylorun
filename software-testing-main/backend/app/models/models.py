from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone
from app.db.database import Base

class RoleEnum(str, enum.Enum):
    admin = "Admin"
    analyst = "Analyst"
    viewer = "Viewer"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default=RoleEnum.viewer.value)

class Target(Base):
    __tablename__ = "targets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    host = Column(String, nullable=False)
    description = Column(String)

class CommandConfig(Base):
    __tablename__ = "command_configs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    executable = Column(String, nullable=False)
    allowed_args = Column(Text, nullable=False) # JSON
    timeout_seconds = Column(Integer, default=60)
    regex_rules = Column(Text, nullable=False) # JSON

class RunHistory(Base):
    __tablename__ = "run_history"
    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(Integer, ForeignKey("command_configs.id"))
    target_id = Column(Integer, ForeignKey("targets.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    raw_output = Column(Text, nullable=True)
    findings = Column(Text, nullable=True) # JSON
