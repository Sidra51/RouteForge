import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator

class UsageLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    api_key_id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    request_id: uuid.UUID
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    cost_saved: Optional[float] = 0.0
    cache_type: Optional[str] = "none"
    latency_ms: int
    status_code: int
    error_message: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    @field_validator('cost_saved', mode='before')
    @classmethod
    def default_cost_saved(cls, v):
        return v if v is not None else 0.0

    @field_validator('cache_type', mode='before')
    @classmethod
    def default_cache_type(cls, v):
        return v if v is not None else "none"

class UsageSummaryResponse(BaseModel):
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost: float
    average_latency_ms: float
    logs: List[UsageLogResponse]

class QuotaUsageResponse(BaseModel):
    plan: str
    requests_today: int
    request_limit: int
    tokens_this_month: int
    token_limit: int
