from typing import Tuple, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.api_key import APIKey
from app.schemas.gateway import ChatRequest, ChatResponse
from app.services.api_key_service import APIKeyService
from app.services.llm_service import LLMService

router = APIRouter()
security_bearer = HTTPBearer()

from app.core import security

async def get_api_key_context(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> Tuple[User, Optional[APIKey]]:
    """Dependency to validate gateway API key or user JWT token and retrieve user context."""
    raw_key = credentials.credentials
    
    if raw_key and raw_key.startswith("gw_live_"):
        api_key = await APIKeyService.validate_key(db, raw_key)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or deactivated gateway API key."
            )
        stmt = select(User).where(User.id == api_key.user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key owner not found or deactivated."
            )
        return user, api_key
    else:
        # Check if JWT token from dashboard UI session
        payload = security.decode_access_token(raw_key)
        if payload and payload.get("sub"):
            try:
                u_id = uuid.UUID(payload["sub"])
                stmt = select(User).where(User.id == u_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    return user, None
            except Exception:
                pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or deactivated gateway API key."
        )

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, BackgroundTasks
import uuid

@router.post("/chat", response_model=ChatResponse)
async def gateway_chat(
    chat_request: ChatRequest,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    context: Tuple[User, APIKey] = Depends(get_api_key_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Inbound chat completion endpoint. 
    Requires authorization via a valid gateway API key: 'Authorization: Bearer gw_live_...'
    """
    user, api_key = context
    client_ip = request.client.host if request.client else None
    
    # Generate overall Request Trace correlation ID
    trace_id = f"trace_{uuid.uuid4().hex[:12]}"
    request.state.trace_id = trace_id
    response.headers["X-Trace-ID"] = trace_id
    
    return await LLMService.route_request(
        db=db,
        user_id=user.id,
        api_key_id=api_key.id if api_key else None,
        request_data=chat_request,
        trace_id=trace_id,
        ip_address=client_ip,
        background_tasks=background_tasks
    )

