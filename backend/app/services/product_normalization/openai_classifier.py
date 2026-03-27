from __future__ import annotations

import json
import logging

import httpx

from app.core.config import get_settings

from .ai_classifier import get_category_catalog
from .models import NormalizationDecision, ProductCandidate

logger = logging.getLogger(__name__)


def _build_messages(candidate: ProductCandidate) -> list[dict]:
    catalog = get_category_catalog()
    category_descriptions = "\n".join(
        f"- {entry['category']}: {entry['display_name']}"
        for entry in catalog
    )
    return [
        {
            "role": "system",
            "content": (
                "You classify Swedish retail purchase labels into a single stable category. "
                "Return strict JSON with keys normalized_name, category, confidence. "
                "Use one of the allowed categories below, or 'other' if none fit.\n"
                f"Allowed categories:\n{category_descriptions}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"raw_label: {candidate.raw_label}\n"
                f"cleaned_label: {candidate.cleaned_label}\n"
                f"base_label: {candidate.base_label}\n"
                f"tokens: {candidate.tokens}\n"
                f"ascii_tokens: {candidate.ascii_tokens}\n"
                "Respond only with JSON."
            ),
        },
    ]


def _normalize_response(payload: dict, candidate: ProductCandidate, model: str) -> NormalizationDecision | None:
    catalog = {entry["category"] for entry in get_category_catalog()}
    catalog.add("other")

    normalized_name = str(payload.get("normalized_name") or candidate.cleaned_label.title()).strip()
    category = str(payload.get("category") or "other").strip().lower()
    if category not in catalog:
        category = "other"

    raw_confidence = payload.get("confidence", 0.78)
    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError):
        confidence = 0.78

    confidence = max(0.5, min(0.95, confidence))

    return NormalizationDecision(
        normalized_name=normalized_name,
        category=category,
        confidence=confidence,
        source="ai",
        rule_id=f"openai.{model}",
    )


def classify(candidate: ProductCandidate) -> NormalizationDecision | None:
    settings = get_settings()
    if not settings.openai_categorization_enabled or not settings.openai_api_key:
        return None

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.openai_model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": _build_messages(candidate),
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=settings.openai_timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return _normalize_response(parsed, candidate, settings.openai_model)
    except Exception as exc:
        logger.warning(
            "openai_product_classification_failed model=%s label=%s error=%s",
            settings.openai_model,
            candidate.raw_label,
            exc,
        )
        return None