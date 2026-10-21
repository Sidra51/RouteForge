from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.prompt_template import PromptTemplate
from app.models.prompt_version import PromptVersion
from app.models.prompt_experiment import PromptExperiment
from app.models.request_trace import RequestTrace
from app.services.prompt_service import PromptService
from app.schemas.prompts import (
    PromptTemplateCreate, PromptTemplateResponse,
    PromptVersionCreate, PromptVersionResponse,
    PromptPreviewRequest, PromptPreviewResponse,
    PromptExperimentCreate, PromptExperimentResponse,
    TemplateEvalResponse, VersionEvalMetric
)

router = APIRouter()

@router.get("", response_model=List[PromptTemplateResponse])
async def list_templates(
    tag: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all prompt templates owned by the current user, optionally filtered by tag."""
    stmt = select(PromptTemplate).where(PromptTemplate.user_id == current_user.id)
    res = await db.execute(stmt)
    templates = res.scalars().all()
    
    if tag:
        # Client side filter for simplicity since tags is JSON array
        templates = [t for t in templates if tag.lower() in [tg.lower() for tg in t.tags]]
        
    return templates

@router.post("", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: PromptTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new prompt template in the registry."""
    # Check if duplicate name
    stmt = select(PromptTemplate).where(PromptTemplate.name == payload.name)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt template with name '{payload.name}' already exists."
        )
        
    template = PromptTemplate(
        name=payload.name,
        description=payload.description,
        tags=payload.tags or [],
        user_id=current_user.id
    )
    
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template

@router.get("/{template_id}/versions", response_model=List[PromptVersionResponse])
async def list_versions(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all versions of a prompt template."""
    # Verify ownership
    stmt = select(PromptTemplate).where(PromptTemplate.id == template_id, PromptTemplate.user_id == current_user.id)
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt template not found.")

    v_stmt = select(PromptVersion).where(PromptVersion.template_id == template_id).order_by(PromptVersion.created_at.desc())
    v_res = await db.execute(v_stmt)
    return v_res.scalars().all()

@router.post("/{template_id}/versions", response_model=PromptVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    template_id: uuid.UUID,
    payload: PromptVersionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new version of a prompt template. Toggles is_active override if requested."""
    # Verify ownership
    stmt = select(PromptTemplate).where(PromptTemplate.id == template_id, PromptTemplate.user_id == current_user.id)
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt template not found.")

    # Check if duplicate version string
    dup_stmt = select(PromptVersion).where(
        PromptVersion.template_id == template_id, 
        PromptVersion.version == payload.version
    )
    dup_res = await db.execute(dup_stmt)
    if dup_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Version '{payload.version}' already exists for this template."
        )

    if payload.is_active:
        # Deactivate other versions first
        await db.execute(
            update(PromptVersion)
            .where(PromptVersion.template_id == template_id)
            .values(is_active=False)
        )

    version = PromptVersion(
        template_id=template_id,
        version=payload.version,
        description=payload.description,
        system_prompt=payload.system_prompt,
        user_prompt=payload.user_prompt,
        is_active=payload.is_active,
        user_id=current_user.id
    )

    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version

@router.patch("/{template_id}/versions/{version_id}/activate", response_model=PromptVersionResponse)
async def activate_version(
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a prompt version as default active (deactivating all other versions)."""
    # Verify template ownership
    stmt = select(PromptTemplate).where(PromptTemplate.id == template_id, PromptTemplate.user_id == current_user.id)
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt template not found.")

    # Verify version ownership
    v_stmt = select(PromptVersion).where(PromptVersion.id == version_id, PromptVersion.template_id == template_id)
    v_res = await db.execute(v_stmt)
    version = v_res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt version not found.")

    # Deactivate others
    await db.execute(
        update(PromptVersion)
        .where(PromptVersion.template_id == template_id)
        .values(is_active=False)
    )

    version.is_active = True
    await db.commit()
    await db.refresh(version)
    return version

@router.post("/{template_id}/preview", response_model=PromptPreviewResponse)
async def preview_prompt_variables(
    template_id: uuid.UUID,
    payload: PromptPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Dry-run validation and rendering preview helper for developer playground."""
    # Verify ownership
    stmt = select(PromptTemplate).where(PromptTemplate.id == template_id, PromptTemplate.user_id == current_user.id)
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt template not found.")

    is_valid, validation_errors = PromptService.validate_variables(
        payload.system_prompt,
        payload.user_prompt,
        payload.variables
    )

    rendered_user = PromptService.render_prompt(payload.user_prompt, payload.variables)
    rendered_system = PromptService.render_prompt(payload.system_prompt, payload.variables) if payload.system_prompt else None

    return {
        "valid": is_valid,
        "rendered_user": rendered_user,
        "rendered_system": rendered_system,
        "errors": validation_errors
    }

@router.post("/{template_id}/experiment", response_model=PromptExperimentResponse)
async def configure_experiment(
    template_id: uuid.UUID,
    payload: PromptExperimentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Configure variant weights for A/B testing splits. Deactivates existing active experiments on template."""
    # Verify ownership
    stmt = select(PromptTemplate).where(PromptTemplate.id == template_id, PromptTemplate.user_id == current_user.id)
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt template not found.")

    # Validate weights sum to 1.0 (allow small precision tolerance)
    total_weight = sum(v.weight for v in payload.variants)
    if abs(total_weight - 1.0) > 0.001:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sum of variant weights must equal 1.0. Found: {total_weight}"
        )

    # Deactivate existing experiments
    await db.execute(
        update(PromptExperiment)
        .where(PromptExperiment.template_id == template_id)
        .values(is_active=False)
    )

    variants_list = [{"version_id": str(v.version_id), "weight": v.weight} for v in payload.variants]

    experiment = PromptExperiment(
        template_id=template_id,
        name=payload.name,
        is_active=payload.is_active,
        variants=variants_list
    )

    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    return experiment

@router.get("/{template_id}/experiment", response_model=Optional[PromptExperimentResponse])
async def get_active_experiment(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve the currently active A/B testing experiment config for a template."""
    stmt = select(PromptExperiment).where(
        PromptExperiment.template_id == template_id,
        PromptExperiment.is_active == True
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

@router.get("/{template_id}/eval", response_model=TemplateEvalResponse)
async def get_template_evaluation(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Query comparison performance metrics and judge scores across all versions of the template."""
    # Verify ownership
    stmt = select(PromptTemplate).where(PromptTemplate.id == template_id, PromptTemplate.user_id == current_user.id)
    res = await db.execute(stmt)
    template = res.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt template not found.")

    v_stmt = select(PromptVersion).where(PromptVersion.template_id == template_id)
    v_res = await db.execute(v_stmt)
    versions = v_res.scalars().all()
    
    version_metrics = []
    for v in versions:
        # Get traces
        t_stmt = select(RequestTrace).where(RequestTrace.prompt_version_id == v.id)
        t_res = await db.execute(t_stmt)
        traces = t_res.scalars().all()
        
        total_calls = len(traces)
        if total_calls == 0:
            version_metrics.append(
                VersionEvalMetric(
                    version_id=v.id,
                    version_str=v.version,
                    total_calls=0,
                    success_rate=100.0,
                    failure_rate=0.0,
                    guardrail_block_rate=0.0,
                    cache_hit_rate=0.0,
                    avg_latency_ms=0.0,
                    avg_cost=0.0,
                    avg_helpfulness=0.0,
                    avg_accuracy=0.0,
                    avg_safety=0.0,
                    avg_tone=0.0,
                    avg_completeness=0.0,
                    avg_overall_score=0.0
                )
            )
            continue
            
        success_count = sum(1 for t in traces if t.is_success)
        failure_count = sum(1 for t in traces if not t.is_success)
        blocked_count = sum(1 for t in traces if t.is_guardrail_blocked)
        
        # Check cache hits
        cache_hit_count = 0
        for t in traces:
            is_hit = False
            for stage in t.timeline:
                if "cache_hit" in stage.get("stage", ""):
                    is_hit = True
                    break
            if is_hit:
                cache_hit_count += 1
                
        avg_latency = sum(t.total_latency_ms for t in traces) / total_calls
        
        # Total cost of all attempts
        total_cost = 0.0
        for t in traces:
            if t.attempts:
                total_cost += sum(float(att.get("cost", 0.0)) for att in t.attempts)
        avg_cost = total_cost / total_calls
        
        # Averages for Judge Evaluation scores
        eval_traces = [t for t in traces if t.evaluation_scores]
        eval_count = len(eval_traces)
        
        avg_helpfulness = 0.0
        avg_accuracy = 0.0
        avg_safety = 0.0
        avg_tone = 0.0
        avg_completeness = 0.0
        avg_overall = 0.0
        
        if eval_count > 0:
            avg_helpfulness = sum(float(t.evaluation_scores.get("helpfulness", 0.0)) for t in eval_traces) / eval_count
            avg_accuracy = sum(float(t.evaluation_scores.get("accuracy", 0.0)) for t in eval_traces) / eval_count
            avg_safety = sum(float(t.evaluation_scores.get("safety", 0.0)) for t in eval_traces) / eval_count
            avg_tone = sum(float(t.evaluation_scores.get("tone", 0.0)) for t in eval_traces) / eval_count
            avg_completeness = sum(float(t.evaluation_scores.get("completeness", 0.0)) for t in eval_traces) / eval_count
            avg_overall = sum(float(t.evaluation_scores.get("overall", 0.0)) for t in eval_traces) / eval_count
            
        version_metrics.append(
            VersionEvalMetric(
                version_id=v.id,
                version_str=v.version,
                total_calls=total_calls,
                success_rate=round((success_count / total_calls) * 100.0, 2),
                failure_rate=round((failure_count / total_calls) * 100.0, 2),
                guardrail_block_rate=round((blocked_count / total_calls) * 100.0, 2),
                cache_hit_rate=round((cache_hit_count / total_calls) * 100.0, 2),
                avg_latency_ms=round(avg_latency, 2),
                avg_cost=round(avg_cost, 6),
                avg_helpfulness=round(avg_helpfulness, 2),
                avg_accuracy=round(avg_accuracy, 2),
                avg_safety=round(avg_safety, 2),
                avg_tone=round(avg_tone, 2),
                avg_completeness=round(avg_completeness, 2),
                avg_overall_score=round(avg_overall, 2)
            )
        )
        
    return {
        "template_name": template.name,
        "versions": version_metrics
    }
