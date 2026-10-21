from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

class PromptTemplateCreate(BaseModel):
    name: str = Field(..., description="Unique name/identifier for the prompt template")
    description: Optional[str] = Field(None, description="Detailed description of the template")
    tags: Optional[List[str]] = Field(None, description="Optional categorization tags")

class PromptTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PromptVersionCreate(BaseModel):
    version: str = Field(..., description="Version string, e.g., 'v1', 'v2'")
    description: Optional[str] = Field(None, description="Release notes / change notes for this version")
    system_prompt: Optional[str] = Field(None, description="System instructions template text")
    user_prompt: str = Field(..., description="User prompt template text (required)")
    is_active: bool = Field(False, description="Set this version as the default active version")

class PromptVersionResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    version: str
    description: Optional[str]
    system_prompt: Optional[str]
    user_prompt: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class PromptPreviewRequest(BaseModel):
    system_prompt: Optional[str] = None
    user_prompt: str
    variables: Optional[Dict[str, Any]] = None

class PromptPreviewResponse(BaseModel):
    valid: bool
    rendered_user: str
    rendered_system: Optional[str]
    errors: Dict[str, List[str]]

class VariantWeight(BaseModel):
    version_id: uuid.UUID
    weight: float = Field(..., ge=0.0, le=1.0)

class PromptExperimentCreate(BaseModel):
    name: str = Field(..., description="Descriptive name for the A/B test")
    is_active: bool = Field(True, description="Enable this experiment immediately")
    variants: List[VariantWeight] = Field(..., description="List of variants and their traffic split weights")

class PromptExperimentResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    name: str
    is_active: bool
    variants: List[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

class VersionEvalMetric(BaseModel):
    version_id: uuid.UUID
    version_str: str
    total_calls: int
    success_rate: float
    failure_rate: float
    guardrail_block_rate: float
    cache_hit_rate: float
    avg_latency_ms: float
    avg_cost: float
    
    # Detailed Judge Dimension Scores
    avg_helpfulness: float
    avg_accuracy: float
    avg_safety: float
    avg_tone: float
    avg_completeness: float
    avg_overall_score: float

class TemplateEvalResponse(BaseModel):
    template_name: str
    versions: List[VersionEvalMetric]
