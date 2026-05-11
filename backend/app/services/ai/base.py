from __future__ import annotations

from abc import ABC, abstractmethod
import json
from typing import Any

from app.core.errors import AIProviderError

ALLOWED_AI_CONTEXT_KEYS = {
    "first_name",
    "company_name",
    "job_title",
    "industry",
    "source",
    "interest_level",
    "timeline",
    "notes",
    "lead_category",
    "priority_score",
    "email_tone",
    "business_type",
    "sender_company_name",
    "existing_subject",
    "existing_body",
}

EMAIL_OUTPUT_SCHEMA = {
    "subject": "Short email subject line.",
    "body": "Concise follow-up email body.",
}

# Keep provider context deliberately small. Uploaded files and unrelated leads
# should never leave the backend when drafting one follow-up email.


class AIProvider(ABC):
    @abstractmethod
    def generate_follow_up_email(self, context: dict[str, Any]) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def rewrite_email(self, context: dict[str, Any]) -> dict[str, str]:
        raise NotImplementedError


def sanitize_ai_context(context: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}

    for key in ALLOWED_AI_CONTEXT_KEYS:
        value = context.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            cleaned_value = value.strip()
            if cleaned_value:
                sanitized[key] = cleaned_value
        elif isinstance(value, (int, float, bool)):
            sanitized[key] = value
        else:
            sanitized[key] = str(value)

    return sanitized


def build_email_prompt(context: dict[str, Any], *, rewrite: bool = False) -> str:
    sanitized_context = sanitize_ai_context(context)
    task = "Rewrite the existing follow-up email draft" if rewrite else "Generate a follow-up email draft"

    return (
        f"{task} for a business lead using only the provided context.\n"
        "Write like a practical account manager, not a marketing newsletter.\n"
        "Use the requested tone, lead source, timeline, notes, and priority when they are present.\n"
        "Keep the email concise enough for a first follow-up.\n"
        "Do not invent facts, pricing, meetings, or promises.\n"
        "Do not send the email. Only return a draft.\n"
        "Return only valid JSON with exactly these keys: subject, body.\n"
        f"Expected output shape: {json.dumps(EMAIL_OUTPUT_SCHEMA)}\n"
        f"Lead context: {json.dumps(sanitized_context, ensure_ascii=True)}"
    )


def parse_email_response_text(response_text: str) -> dict[str, str]:
    cleaned_text = response_text.strip()

    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`")
        cleaned_text = cleaned_text.removeprefix("json").strip()

    try:
        payload = json.loads(cleaned_text)
    except json.JSONDecodeError as exc:
        raise AIProviderError("The AI provider returned an invalid email draft format.") from exc

    subject = str(payload.get("subject", "")).strip()
    body = str(payload.get("body", "")).strip()

    if not subject or not body:
        raise AIProviderError("The AI provider returned an incomplete email draft.")

    return {
        "subject": subject,
        "body": body,
    }
