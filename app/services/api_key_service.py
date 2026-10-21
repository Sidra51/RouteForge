import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyCreateResponse, APIKeyUsageSummary

class APIKeyService:
    @staticmethod
    async def create_key(
        db: AsyncSession, 
        user_id: uuid.UUID, 
        key_data: APIKeyCreate
    ) -> APIKeyCreateResponse:
        """Create a new API Key for a user and return the raw unhashed key once."""
        # Generate 24 bytes of random entropy (48 hex chars)
        entropy = secrets.token_hex(24)
        raw_key = f"gw_live_{entropy}"
        
        # Public prefix e.g., "gw_live_a1b2" (first 12 chars: gw_live_ + 4 chars of entropy)
        key_prefix = raw_key[:12]
        
        # Calculate SHA-256 hash for lookup
        hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
        
        expires_at = None
        if key_data.expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=key_data.expires_in_days)
            
        db_key = APIKey(
            user_id=user_id,
            name=key_data.name,
            key_prefix=key_prefix,
            hashed_key=hashed_key,
            expires_at=expires_at,
            rate_limit_rpm=key_data.rate_limit_rpm,
            monthly_token_quota=key_data.monthly_token_quota,
            guardrail_settings=key_data.guardrail_settings
        )
        
        db.add(db_key)
        await db.commit()
        await db.refresh(db_key)
        
        usage = APIKeyUsageSummary()
        
        # Build schema response with the raw key included
        return APIKeyCreateResponse(
            id=db_key.id,
            user_id=db_key.user_id,
            name=db_key.name,
            key_prefix=db_key.key_prefix,
            is_active=db_key.is_active,
            expires_at=db_key.expires_at,
            created_at=db_key.created_at,
            updated_at=db_key.updated_at,
            last_used_at=db_key.last_used_at,
            api_key=raw_key,
            usage=usage,
            rate_limit_rpm=db_key.rate_limit_rpm,
            monthly_token_quota=db_key.monthly_token_quota,
            guardrail_settings=db_key.guardrail_settings
        )

    @staticmethod
    async def validate_key(db: AsyncSession, raw_key: str) -> Optional[APIKey]:
        """Validate a raw API key, updating its last used timestamp if valid."""
        if not raw_key.startswith("gw_live_"):
            return None
            
        hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
        
        stmt = select(APIKey).where(APIKey.hashed_key == hashed_key)
        result = await db.execute(stmt)
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            return None
            
        if not api_key.is_active:
            return None
            
        if api_key.deleted_at is not None:
            return None
            
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            # Deactivate expired key
            api_key.is_active = False
            await db.commit()
            return None
            
        # Update usage timestamp
        api_key.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(api_key)
        return api_key

    @staticmethod
    async def list_keys(db: AsyncSession, user_id: uuid.UUID) -> List[APIKey]:
        """List active/inactive (non-soft-deleted) API keys belonging to a user, with usage aggregates."""
        stmt = select(APIKey).where(
            APIKey.user_id == user_id, 
            APIKey.deleted_at.is_(None)
        ).order_by(APIKey.created_at.desc())
        
        result = await db.execute(stmt)
        keys = list(result.scalars().all())
        
        # Aggregate usage logs by key_id for this user
        from app.models.usage import UsageLog
        
        usage_stmt = (
            select(
                UsageLog.api_key_id,
                func.count(UsageLog.id).label("total_requests"),
                func.sum(UsageLog.total_tokens).label("total_tokens"),
                func.sum(UsageLog.cost).label("total_cost")
            )
            .where(UsageLog.user_id == user_id, UsageLog.api_key_id.is_not(None))
            .group_by(UsageLog.api_key_id)
        )
        usage_result = await db.execute(usage_stmt)
        usage_map = {row.api_key_id: row for row in usage_result.all()}
        
        for key in keys:
            row = usage_map.get(key.id)
            if row:
                key.usage = APIKeyUsageSummary(
                    total_requests=row.total_requests or 0,
                    total_tokens=int(row.total_tokens or 0),
                    total_cost=float(row.total_cost or 0.0)
                )
            else:
                key.usage = APIKeyUsageSummary()
                
        return keys

    @staticmethod
    async def get_key(db: AsyncSession, user_id: uuid.UUID, key_id: uuid.UUID) -> Optional[APIKey]:
        """Get a single active (non-soft-deleted) API key by ID, with usage summary."""
        stmt = select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == user_id,
            APIKey.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        key = result.scalar_one_or_none()
        
        if not key:
            return None
            
        from app.models.usage import UsageLog
        
        usage_stmt = (
            select(
                func.count(UsageLog.id).label("total_requests"),
                func.sum(UsageLog.total_tokens).label("total_tokens"),
                func.sum(UsageLog.cost).label("total_cost")
            )
            .where(UsageLog.api_key_id == key.id)
        )
        usage_result = await db.execute(usage_stmt)
        row = usage_result.first()
        
        if row and (row.total_requests or row.total_tokens or row.total_cost):
            key.usage = APIKeyUsageSummary(
                total_requests=row.total_requests or 0,
                total_tokens=int(row.total_tokens or 0),
                total_cost=float(row.total_cost or 0.0)
            )
        else:
            key.usage = APIKeyUsageSummary()
            
        return key

    @staticmethod
    async def toggle_key_status(
        db: AsyncSession, 
        user_id: uuid.UUID, 
        key_id: uuid.UUID, 
        active: bool
    ) -> Optional[APIKey]:
        """Activate or deactivate an API key."""
        stmt = select(APIKey).where(
            APIKey.id == key_id, 
            APIKey.user_id == user_id,
            APIKey.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            return None
            
        api_key.is_active = active
        await db.commit()
        await db.refresh(api_key)
        
        # Attach usage summary before return
        return await APIKeyService.get_key(db, user_id, key_id)

    @staticmethod
    async def rename_key(
        db: AsyncSession,
        user_id: uuid.UUID,
        key_id: uuid.UUID,
        new_name: str
    ) -> Optional[APIKey]:
        """Rename an API key."""
        stmt = select(APIKey).where(
            APIKey.id == key_id, 
            APIKey.user_id == user_id,
            APIKey.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            return None
            
        api_key.name = new_name
        await db.commit()
        await db.refresh(api_key)
        
        # Attach usage summary before return
        return await APIKeyService.get_key(db, user_id, key_id)

    @staticmethod
    async def delete_key(db: AsyncSession, user_id: uuid.UUID, key_id: uuid.UUID) -> bool:
        """Soft-delete an API key."""
        stmt = select(APIKey).where(
            APIKey.id == key_id, 
            APIKey.user_id == user_id,
            APIKey.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            return False
            
        api_key.deleted_at = datetime.now(timezone.utc)
        api_key.is_active = False
        await db.commit()
        return True

    @staticmethod
    async def rotate_key(
        db: AsyncSession,
        user_id: uuid.UUID,
        key_id: uuid.UUID
    ) -> Optional[APIKeyCreateResponse]:
        """Rotate an API key. Soft-delete the old key, and create a new one with same name and expiration."""
        stmt = select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == user_id,
            APIKey.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        old_key = result.scalar_one_or_none()
        
        if not old_key:
            return None
            
        # Get expiration and name, and overrides
        expires_at = old_key.expires_at
        name = old_key.name
        rate_limit_rpm = old_key.rate_limit_rpm
        monthly_token_quota = old_key.monthly_token_quota
        
        # Soft delete the old key
        old_key.is_active = False
        old_key.deleted_at = datetime.now(timezone.utc)
        
        # Generate new API Key
        entropy = secrets.token_hex(24)
        raw_key = f"gw_live_{entropy}"
        key_prefix = raw_key[:12]
        hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
        
        new_key = APIKey(
            user_id=user_id,
            name=name,
            key_prefix=key_prefix,
            hashed_key=hashed_key,
            expires_at=expires_at,
            rate_limit_rpm=rate_limit_rpm,
            monthly_token_quota=monthly_token_quota
        )
        
        db.add(new_key)
        await db.commit()
        await db.refresh(new_key)
        
        usage = APIKeyUsageSummary()
        
        # Return response including the raw API key
        return APIKeyCreateResponse(
            id=new_key.id,
            user_id=new_key.user_id,
            name=new_key.name,
            key_prefix=new_key.key_prefix,
            is_active=new_key.is_active,
            expires_at=new_key.expires_at,
            created_at=new_key.created_at,
            updated_at=new_key.updated_at,
            last_used_at=new_key.last_used_at,
            api_key=raw_key,
            usage=usage,
            rate_limit_rpm=new_key.rate_limit_rpm,
            monthly_token_quota=new_key.monthly_token_quota
        )
