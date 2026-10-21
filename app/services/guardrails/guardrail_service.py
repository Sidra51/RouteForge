import re
import uuid
import logging
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.guardrail_event import GuardrailEvent

logger = logging.getLogger(__name__)

# PII Pattern definitions
PII_PATTERNS = [
    {
        "type": "email",
        "detail": "Email Address",
        "pattern": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "replacement": "[EMAIL_REDACTED]",
        "severity": "medium",
    },
    {
        "type": "phone",
        "detail": "Phone Number",
        "pattern": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "replacement": "[PHONE_REDACTED]",
        "severity": "medium",
    },
    {
        "type": "ssn",
        "detail": "Social Security Number",
        "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
        "replacement": "[SSN_REDACTED]",
        "severity": "high",
    },
    {
        "type": "api_key",
        "detail": "API Key / Token",
        "pattern": r"\b(sk-[a-zA-Z0-9]{20,}|gw_live_[a-zA-Z0-9_]{16,}|AIzaSy[a-zA-Z0-9_-]{33})\b",
        "replacement": "[KEY_REDACTED]",
        "severity": "critical",
    },
    {
        "type": "credit_card",
        "detail": "Credit Card Number",
        "pattern": r"\b(?:\d[ -]*?){13,16}\b",
        "replacement": "[CARD_REDACTED]",
        "severity": "high",
    },
]

# Jailbreak / Prompt Injection patterns
JAILBREAK_PATTERNS = [
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)bypass\s+safety\s+filters",
    r"(?i)dan\s+mode",
    r"(?i)do\s+anything\s+now",
]


class GuardrailService:
    @classmethod
    async def evaluate_request(
        cls,
        db: Optional[AsyncSession] = None,
        user_id: Optional[uuid.UUID] = None,
        api_key_id: Optional[uuid.UUID] = None,
        prompt: str = "",
        policy: Optional[Dict[str, Any]] = None,
        policies: Optional[Dict[str, Any]] = None,
        request_id: Optional[uuid.UUID] = None,
        trace_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Evaluate a prompt against active security policies & PII filters.
        Accepts both `policy` and `policies` keyword arguments as well as `dry_run`.
        """
        if not prompt:
            return prompt, []

        active_policy = policy or policies or {}
        violations: List[Dict[str, Any]] = []
        masked_prompt = prompt
        req_id = request_id or uuid.uuid4()

        # 1. Prompt Size Limit check
        max_chars = active_policy.get("max_characters")
        if max_chars and len(prompt) > max_chars:
            violations.append({
                "event_type": "size_limit",
                "matched_detail": f"Prompt length ({len(prompt)} chars) exceeds limit ({max_chars} chars)",
                "matched_text": prompt[:50] + "...",
                "confidence": 1.0,
                "severity": "high",
                "action_taken": "block",
                "detector": "size_validator",
            })

        # 2. PII Masking & Detection
        pii_action = active_policy.get("pii", "mask")
        for pii in PII_PATTERNS:
            matches = list(re.finditer(pii["pattern"], masked_prompt))
            for match in matches:
                matched_text = match.group(0)
                violations.append({
                    "event_type": "pii_leak",
                    "matched_detail": pii["detail"],
                    "matched_text": matched_text,
                    "confidence": 0.98,
                    "severity": pii["severity"],
                    "action_taken": pii_action,
                    "detector": "pii_detector",
                })
            if matches and pii_action in ["mask", "redact"]:
                masked_prompt = re.sub(pii["pattern"], pii["replacement"], masked_prompt)

        # 3. Jailbreak / Prompt Injection Detection
        injection_action = active_policy.get("prompt_injection", "block")
        for jb_pattern in JAILBREAK_PATTERNS:
            match = re.search(jb_pattern, prompt)
            if match:
                violations.append({
                    "event_type": "prompt_injection",
                    "matched_detail": f"Pattern matched: {match.group(0)}",
                    "matched_text": match.group(0),
                    "confidence": 0.95,
                    "severity": "high",
                    "action_taken": injection_action,
                    "detector": "injection_detector",
                })

        # 4. Save Guardrail Events to PostgreSQL DB if DB session is active and not dry_run
        if db and not dry_run and violations and user_id:
            try:
                for v in violations:
                    event = GuardrailEvent(
                        user_id=user_id,
                        api_key_id=api_key_id,
                        request_id=req_id,
                        trace_id=trace_id,
                        detector=v["detector"],
                        event_type=v["event_type"],
                        action_taken=v["action_taken"],
                        severity=v["severity"],
                        confidence=v["confidence"],
                        matched_detail=v["matched_detail"],
                        prompt_preview=prompt[:200],
                    )
                    db.add(event)
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to log guardrail events: {e}")
                await db.rollback()

        return masked_prompt, violations
