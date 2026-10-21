from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.schemas.api_key import APIKeyCreate, APIKeyResponse, APIKeyCreateResponse, APIKeyUpdate
from app.services.api_key_service import APIKeyService

router = APIRouter()

@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a new API key for the authenticated user. Displays raw key ONLY once."""
    return await APIKeyService.create_key(db, current_user.id, key_data)

@router.get("", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve metadata of all API keys owned by the authenticated user."""
    return await APIKeyService.list_keys(db, current_user.id)

@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve metadata of a specific API key."""
    key = await APIKeyService.get_key(db, current_user.id, key_id)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found or does not belong to you."
        )
    return key

@router.patch("/{key_id}", response_model=APIKeyResponse)
async def rename_api_key(
    key_id: uuid.UUID,
    update_data: APIKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rename a specific API key."""
    key = await APIKeyService.rename_key(db, current_user.id, key_id, update_data.name)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found or does not belong to you."
        )
    return key

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft-delete a specific API key."""
    deleted = await APIKeyService.delete_key(db, current_user.id, key_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found or does not belong to you."
        )
    return None

@router.patch("/{key_id}/activate", response_model=APIKeyResponse)
async def activate_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Activate a specific API key."""
    key = await APIKeyService.toggle_key_status(db, current_user.id, key_id, active=True)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found or does not belong to you."
        )
    return key

@router.patch("/{key_id}/deactivate", response_model=APIKeyResponse)
async def deactivate_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a specific API key."""
    key = await APIKeyService.toggle_key_status(db, current_user.id, key_id, active=False)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found or does not belong to you."
        )
    return key

@router.post("/{key_id}/rotate", response_model=APIKeyCreateResponse)
async def rotate_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rotate an API key (soft-deactivates the old key, issues a new one with same expiration and name)."""
    response = await APIKeyService.rotate_key(db, current_user.id, key_id)
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found or does not belong to you."
        )
    return response
