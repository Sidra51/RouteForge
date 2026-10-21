from typing import Optional, List
import uuid
from pydantic import BaseModel, Field

from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    provider: Optional[str] = Field(None, description="LLM provider name (e.g., 'gemini'). Optional if routing_policy is specified.")
    model: Optional[str] = Field(None, description="Model name. If null, gateway defaults to provider default model (e.g., 'gemini-2.5-flash')")
    message: Optional[str] = Field(None, description="The text prompt to send to the LLM. Optional if using prompt_template_name.")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(1000, ge=1, description="Maximum tokens to generate")
    routing_policy: Optional[str] = Field(None, description="Routing policy: 'cheapest', 'fastest', 'best_quality', 'auto'")
    fallback_chain: Optional[List[str]] = Field(None, description="Ordered list of fallback providers")
    bypass_cache: Optional[bool] = Field(False, description="Force bypass caching and fetch fresh response from upstream model")
    
    # Phase 9 fields
    prompt_template_name: Optional[str] = Field(None, description="Name of the prompt template in the registry")
    prompt_template_version: Optional[str] = Field(None, description="Specific version of prompt template to use")
    variables: Optional[Dict[str, Any]] = Field(None, description="Variables to interpolate into the prompt template")


class CacheMetadata(BaseModel):
    hit: bool = False
    type: Optional[str] = None  # "exact" or "semantic"
    similarity: Optional[float] = None

class ChatResponse(BaseModel):
    request_id: uuid.UUID = Field(..., description="Unique transaction ID for tracking usage and debugging")
    provider: str = Field(..., description="The LLM provider that processed this request")
    model: str = Field(..., description="The specific model used")
    response_text: str = Field(..., description="The generated response text from the model")
    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(..., description="Number of tokens in the generation")
    total_tokens: int = Field(..., description="Sum of prompt and completion tokens")
    cost: float = Field(..., description="Estimated cost of request in USD")
    latency_ms: int = Field(..., description="Total execution latency in milliseconds")
    cache: Optional[CacheMetadata] = Field(None, description="Detailed caching hit metadata")
