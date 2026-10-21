import re
import random
import uuid
import logging
from typing import Dict, Any, Tuple, Set, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_template import PromptTemplate
from app.models.prompt_version import PromptVersion
from app.models.prompt_experiment import PromptExperiment

logger = logging.getLogger(__name__)

class PromptService:
    @staticmethod
    def get_placeholders(text: Optional[str]) -> Set[str]:
        """Extract all unique placeholders formatted as {{variable_name}} from prompt text."""
        if not text:
            return set()
        return set(re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", text))

    @classmethod
    def validate_variables(
        cls, 
        system_prompt: Optional[str], 
        user_prompt: str, 
        variables: Optional[Dict[str, Any]]
    ) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Validate provided variables against required placeholders in the template:
        - missing: required but not provided
        - unknown: provided but not required
        - empty: provided but value is empty/None
        """
        req_system = cls.get_placeholders(system_prompt)
        req_user = cls.get_placeholders(user_prompt)
        required = req_system.union(req_user)
        
        variables = variables or {}
        provided = set(variables.keys())
        
        missing = list(required - provided)
        unknown = list(provided - required)
        empty = []
        
        for k in provided:
            if k in required:
                val = variables[k]
                if val is None or (isinstance(val, str) and val.strip() == ""):
                    empty.append(k)
        
        errors = {}
        if missing:
            errors["missing"] = missing
        if unknown:
            errors["unknown"] = unknown
        if empty:
            errors["empty"] = empty
            
        return len(errors) == 0, errors

    @staticmethod
    def render_prompt(template_text: Optional[str], variables: Optional[Dict[str, Any]]) -> str:
        """Replace all double curly brace placeholders with variables dict values."""
        if not template_text:
            return ""
        variables = variables or {}
        rendered = template_text
        for key, value in variables.items():
            pattern = re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}")
            rendered = pattern.sub(str(value), rendered)
        return rendered

    @classmethod
    async def route_template_request(
        cls,
        db: AsyncSession,
        template_name: str,
        version_str: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Tuple[PromptVersion, Optional[PromptExperiment], str, Optional[str]]:
        """
        Select the target prompt version based on:
        1. Explicit version string if provided.
        2. A/B testing experiment weights if active.
        3. Active default version.
        
        Validates variables and renders the system and user prompts.
        
        Returns:
            Tuple[PromptVersion, Optional[PromptExperiment], rendered_user_prompt, Optional[rendered_system_prompt]]
        """
        # 1. Fetch template
        stmt = select(PromptTemplate).where(PromptTemplate.name == template_name)
        res = await db.execute(stmt)
        template = res.scalar_one_or_none()
        if not template:
            raise ValueError(f"Prompt template '{template_name}' not found.")

        target_version = None
        target_experiment = None

        # 2. Pick target version
        if version_str:
            # Explicit version requested
            v_stmt = select(PromptVersion).where(
                PromptVersion.template_id == template.id,
                PromptVersion.version == version_str
            )
            v_res = await db.execute(v_stmt)
            target_version = v_res.scalar_one_or_none()
            if not target_version:
                raise ValueError(f"Prompt template version '{version_str}' not found for template '{template_name}'.")
        else:
            # Check for active experiment
            exp_stmt = select(PromptExperiment).where(
                PromptExperiment.template_id == template.id,
                PromptExperiment.is_active == True
            )
            exp_res = await db.execute(exp_stmt)
            target_experiment = exp_res.scalar_one_or_none()
            
            if target_experiment and target_experiment.variants:
                # Random split based on weights
                variants = target_experiment.variants
                v_ids = [v["version_id"] for v in variants]
                weights = [v["weight"] for v in variants]
                selected_v_id_str = random.choices(v_ids, weights=weights, k=1)[0]
                selected_v_id = uuid.UUID(selected_v_id_str)
                
                v_stmt = select(PromptVersion).where(PromptVersion.id == selected_v_id)
                v_res = await db.execute(v_stmt)
                target_version = v_res.scalar_one_or_none()
            
            if not target_version:
                # Fall back to default active version
                v_stmt = select(PromptVersion).where(
                    PromptVersion.template_id == template.id,
                    PromptVersion.is_active == True
                )
                v_res = await db.execute(v_stmt)
                target_version = v_res.scalar_one_or_none()

            if not target_version:
                # Fall back to latest created version if no active version is set
                v_stmt = select(PromptVersion).where(
                    PromptVersion.template_id == template.id
                ).order_by(PromptVersion.created_at.desc())
                v_res = await db.execute(v_stmt)
                target_version = v_res.scalars().first()

        if not target_version:
            raise ValueError(f"No prompt versions found/configured for template '{template_name}'.")

        # 3. Validate variables
        is_valid, validation_errors = cls.validate_variables(
            target_version.system_prompt,
            target_version.user_prompt,
            variables
        )
        if not is_valid:
            error_details = []
            if "missing" in validation_errors:
                error_details.append(f"Missing variables: {', '.join(validation_errors['missing'])}")
            if "unknown" in validation_errors:
                error_details.append(f"Unused/unknown variables provided: {', '.join(validation_errors['unknown'])}")
            if "empty" in validation_errors:
                error_details.append(f"Empty variable values provided: {', '.join(validation_errors['empty'])}")
            raise ValueError(f"Variable validation failed: {'; '.join(error_details)}")

        # 4. Render prompts
        rendered_user = cls.render_prompt(target_version.user_prompt, variables)
        rendered_system = cls.render_prompt(target_version.system_prompt, variables) if target_version.system_prompt else None

        return target_version, target_experiment, rendered_user, rendered_system
