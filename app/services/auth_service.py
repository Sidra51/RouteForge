import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse
from app.core import security
from app.core.config import settings

class AuthService:
    @staticmethod
    async def register(db: AsyncSession, register_data: UserRegister) -> User:
        """Register a new user in the system."""
        # Check if user already exists
        stmt = select(User).where(User.email == register_data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if this is the first user; if so, make them an admin
        count_stmt = select(User)
        count_res = await db.execute(count_stmt)
        is_first_user = len(count_res.scalars().all()) == 0
        role = "ADMIN" if is_first_user else "USER"
        
        hashed_password = security.get_password_hash(register_data.password)
        db_user = User(
            email=register_data.email,
            hashed_password=hashed_password,
            role=role
        )
        
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def authenticate_user(db: AsyncSession, login_data: UserLogin) -> User:
        """Authenticate a user with password and email."""
        stmt = select(User).where(User.email == login_data.email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not security.verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
            
        return user

    @staticmethod
    async def create_tokens(db: AsyncSession, user_id: uuid.UUID, role: str) -> Token:
        """Create access and refresh tokens for a user, saving refresh token hash in DB."""
        # Generate access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            subject=user_id,
            role=role,
            expires_delta=access_token_expires
        )
        
        # Generate refresh token
        raw_refresh_token = security.generate_refresh_token()
        token_hash = security.hash_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        db_refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        db.add(db_refresh_token)
        await db.commit()
        
        return Token(
            access_token=access_token,
            refresh_token=raw_refresh_token
        )

    @staticmethod
    async def refresh_access_token(db: AsyncSession, refresh_token: str) -> Token:
        """Validate a refresh token and issue a new set of tokens."""
        token_hash = security.hash_token(refresh_token)
        
        # Find matching refresh token
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()
        
        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
            
        if db_token.expires_at < datetime.now(timezone.utc):
            # Delete expired token
            await db.delete(db_token)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Expired refresh token"
            )
        
        # Fetch user
        stmt_user = select(User).where(User.id == db_token.user_id)
        res_user = await db.execute(stmt_user)
        user = res_user.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
            
        # Clean up old refresh token
        await db.delete(db_token)
        await db.commit()
        
        # Issue new tokens
        return await AuthService.create_tokens(db, user.id, user.role)
        
    @staticmethod
    async def logout(db: AsyncSession, refresh_token: str) -> None:
        """Revoke a refresh token on logout."""
        token_hash = security.hash_token(refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()
        
        if db_token:
            await db.delete(db_token)
            await db.commit()
