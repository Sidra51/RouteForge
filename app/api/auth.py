from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
import uuid

from app.core.database import get_db
from app.core import security
from app.core.config import settings
from app.schemas.auth import UserRegister, UserLogin, Token, TokenRefresh, UserResponse, PlanUpgradeRequest
from app.services.auth_service import AuthService
from app.models.user import User
from sqlalchemy import select

router = APIRouter()
security_bearer = HTTPBearer()

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer)
) -> User:
    """FastAPI dependency to extract JWT from Authorization header and return the current user."""
    token = credentials.credentials
    payload = security.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload contains invalid subject format",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is inactive"
        )
        
    return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(register_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    return await AuthService.register(db, register_data)

@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return access + refresh tokens."""
    user = await AuthService.authenticate_user(db, login_data)
    return await AuthService.create_tokens(db, user.id, user.role)

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token set."""
    return await AuthService.refresh_access_token(db, refresh_data.refresh_token)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(refresh_data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Revoke a refresh token, logging the user out."""
    await AuthService.logout(db, refresh_data.refresh_token)

@router.get("/me", response_model=UserResponse)
async def read_me(current_user: User = Depends(get_current_user)):
    """Retrieve details of the currently authenticated user."""
    return current_user

@router.patch("/upgrade", response_model=UserResponse)
async def upgrade_plan(
    upgrade_data: PlanUpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upgrade or downgrade the authenticated user's plan."""
    plan = upgrade_data.plan_type.lower()
    if plan not in ["free", "pro", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan type. Supported plans: free, pro, enterprise"
        )
        
    current_user.plan_type = plan
    await db.commit()
    await db.refresh(current_user)
    return current_user
