from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.core.errors import AIProviderError
from app.services.ai.ai_service import AIService
from app.services.ai.base import build_email_prompt, parse_email_response_text, sanitize_ai_context
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.mock_provider import MockAIProvider
from app.services.ai.openai_provider import OpenAIProvider


def test_sanitize_ai_context_keeps_only_business_safe_fields() -> None:
    context = {
        "first_name": " Maya ",
        "company_name": "Northstar Homes",
        "job_title": "Operations Director",
        "industry": "Property Management",
        "source": "Referral",
        "interest_level": "High",
        "timeline": "Immediate",
        "notes": "Asked for a concise proposal.",
        "lead_category": "Hot",
        "priority_score": 92,
        "email_tone": "professional",
        "business_type": "B2B service business",
        "sender_company_name": "LeadFlow AI",
        "email": "maya@example.com",
        "phone": "+14155550134",
        "raw_dataframe": [{"email": "other@example.com"}],
        "unrelated_leads": [{"first_name": "Other"}],
        "private_internal_note": "Do not send this to a provider.",
    }

    sanitized = sanitize_ai_context(context)

    assert sanitized == {
        "first_name": "Maya",
        "company_name": "Northstar Homes",
        "job_title": "Operations Director",
        "industry": "Property Management",
        "source": "Referral",
        "interest_level": "High",
        "timeline": "Immediate",
        "notes": "Asked for a concise proposal.",
        "lead_category": "Hot",
        "priority_score": 92,
        "email_tone": "professional",
        "business_type": "B2B service business",
        "sender_company_name": "LeadFlow AI",
    }


def test_build_email_prompt_does_not_include_unallowed_private_data() -> None:
    prompt = build_email_prompt(
        {
            "first_name": "Maya",
            "company_name": "Northstar Homes",
            "email": "maya@example.com",
            "phone": "+14155550134",
            "raw_dataframe": "full import data",
        }
    )

    assert "Maya" in prompt
    assert "Northstar Homes" in prompt
    assert "maya@example.com" not in prompt
    assert "+14155550134" not in prompt
    assert "full import data" not in prompt
    assert "Do not send the email" in prompt


def test_mock_provider_generates_human_follow_up_email() -> None:
    provider = MockAIProvider()

    result = provider.generate_follow_up_email(
        {
            "first_name": "Maya",
            "company_name": "Northstar Homes",
            "sender_company_name": "LeadFlow AI",
            "lead_category": "Hot",
            "priority_score": 92,
            "email_tone": "professional",
        }
    )

    assert result["subject"] == "Following up with Northstar Homes"
    assert "Hi Maya" in result["body"]
    assert "LeadFlow AI" in result["body"]
    assert "priority score of 92" in result["body"]
    assert "send" not in result["subject"].lower()


def test_mock_provider_can_rewrite_existing_email() -> None:
    provider = MockAIProvider()

    result = provider.rewrite_email(
        {
            "first_name": "Jordan",
            "existing_subject": "Checking in",
            "existing_body": "Hi Jordan,\n\nWould a quick call be useful?\n\nBest,",
            "email_tone": "concise",
        }
    )

    assert result["subject"] == "Checking in"
    assert "Would a quick call be useful?" in result["body"]
    assert "short, business-friendly tone" in result["body"]


def test_ai_service_uses_mock_provider_for_local_development() -> None:
    settings = get_settings()
    original_provider = settings.ai_provider
    settings.ai_provider = "mock"

    try:
        service = AIService()
        result = service.generate_follow_up_email(
            {
                "first_name": "Avery",
                "company_name": "BrightPath Marketing",
                "sender_company_name": "LeadFlow AI",
            }
        )
    finally:
        settings.ai_provider = original_provider

    assert result["subject"] == "Following up with BrightPath Marketing"
    assert "Hi Avery" in result["body"]


def test_openai_provider_requires_api_key() -> None:
    with pytest.raises(AIProviderError) as exc:
        OpenAIProvider(api_key=None)

    assert exc.value.code == "ai_provider_not_configured"
    assert "OPENAI_API_KEY" in exc.value.message


def test_gemini_provider_requires_api_key() -> None:
    with pytest.raises(AIProviderError) as exc:
        GeminiProvider(api_key=None)

    assert exc.value.code == "ai_provider_not_configured"
    assert "GEMINI_API_KEY" in exc.value.message


def test_parse_email_response_text_accepts_json_only_output() -> None:
    result = parse_email_response_text(
        '{"subject": "Quick follow-up", "body": "Hi Maya, would a short call be useful?"}'
    )

    assert result == {
        "subject": "Quick follow-up",
        "body": "Hi Maya, would a short call be useful?",
    }


def test_parse_email_response_text_rejects_incomplete_output() -> None:
    with pytest.raises(AIProviderError) as exc:
        parse_email_response_text('{"subject": "", "body": ""}')

    assert "incomplete email draft" in exc.value.message
