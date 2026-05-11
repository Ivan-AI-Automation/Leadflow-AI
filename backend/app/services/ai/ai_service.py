from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.errors import AIProviderError
from app.services.ai.base import AIProvider, sanitize_ai_context
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.mock_provider import MockAIProvider
from app.services.ai.openai_provider import OpenAIProvider


class AIService:
    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider or self._provider_from_settings()

    def generate_follow_up_email(self, context: dict[str, Any]) -> dict[str, str]:
        sanitized_context = sanitize_ai_context(context)
        return self.provider.generate_follow_up_email(sanitized_context)

    def rewrite_email(self, context: dict[str, Any]) -> dict[str, str]:
        sanitized_context = sanitize_ai_context(context)
        return self.provider.rewrite_email(sanitized_context)

    @staticmethod
    def _provider_from_settings() -> AIProvider:
        settings = get_settings()
        provider_name = settings.ai_provider.strip().lower()

        if provider_name in {"mock", "fake", "local", "dev"}:
            return MockAIProvider()

        if provider_name == "openai":
            return OpenAIProvider(api_key=settings.openai_api_key)

        if provider_name == "gemini":
            return GeminiProvider(api_key=settings.gemini_api_key)

        raise AIProviderError(
            f"Unsupported AI provider '{settings.ai_provider}'. Use mock, openai, or gemini.",
            code="unsupported_ai_provider",
        )
