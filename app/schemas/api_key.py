from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
import uuid

class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="A descriptive name for the API key")
    expires_in_days: Optional[int] = Field(None, ge=1, description="Days until key expires. Leave null for no expiration.")
    rate_limit_rpm: Optional[int] = Field(None, ge=1, description="Custom rate limit overrides (Requests Per Minute).")
    monthly_token_quota: Optional[int] = Field(None, ge=1, description="Custom monthly token quota overrides.")
    guardrail_settings: Optional[dict] = Field(None, description="Custom guardrail configuration settings.")

class APIKeyUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="The updated name of the API key")

class APIKeyUsageSummary(BaseModel):
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0

class APIKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None
    usage: APIKeyUsageSummary = Field(default_factory=APIKeyUsageSummary)
    rate_limit_rpm: Optional[int] = None
    monthly_token_quota: Optional[int] = None
    guardrail_settings: Optional[dict] = None

class APIKeyCreateResponse(APIKeyResponse):
    api_key: str = Field(..., description="The full raw API key. Store it safely, it will not be displayed again!")
