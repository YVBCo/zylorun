from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class RepositoryBase(BaseModel):
    name: str
    url: str

class RepositoryCreate(RepositoryBase):
    pass

class RepositoryResponse(RepositoryBase):
    id: int
    owner_id: int
    provider: Optional[str] = "github"
    github_owner: Optional[str] = None
    default_branch: Optional[str] = None
    is_public: Optional[bool] = True
    github_created_at: Optional[datetime] = None
    github_updated_at: Optional[datetime] = None
    monitoring_status: Optional[str] = "NOT_CONFIGURED"
    last_polled_at: Optional[datetime] = None
    last_successful_poll_at: Optional[datetime] = None
    last_processed_sha: Optional[str] = None
    last_seen_sha: Optional[str] = None
    last_poll_error: Optional[str] = None
    pr_gate_enabled: Optional[bool] = False
    pr_gate_block_critical: Optional[bool] = True
    pr_gate_block_high: Optional[bool] = True
    pr_gate_block_medium: Optional[bool] = False
    pr_gate_block_incomplete: Optional[bool] = True

    model_config = ConfigDict(from_attributes=True)


class PRGatePolicyUpdate(BaseModel):
    pr_gate_enabled: Optional[bool] = None
    pr_gate_block_critical: Optional[bool] = None
    pr_gate_block_high: Optional[bool] = None
    pr_gate_block_medium: Optional[bool] = None
    pr_gate_block_incomplete: Optional[bool] = None


class PRGatePolicyResponse(BaseModel):
    pr_gate_enabled: bool
    pr_gate_block_critical: bool
    pr_gate_block_high: bool
    pr_gate_block_medium: bool
    pr_gate_block_incomplete: bool

    model_config = ConfigDict(from_attributes=True)

