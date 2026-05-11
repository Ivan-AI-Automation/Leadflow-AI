from __future__ import annotations

from typing import Any

import httpx

from app.core.errors import AIProviderError
from app.services.ai.base import AIProvider, build_email_prompt, parse_email_response_text


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str = "gpt-5-mini",
        timeout_seconds: int = 30,
    ) -> None:
        if not api_key:
            raise AIProviderError(
                "OpenAI API key is missing. Set OPENAI_API_KEY in the environment.",
                code="ai_provider_not_configured",
            )

        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_follow_up_email(self, context: dict[str, Any]) -> dict[str, str]:
        prompt = build_email_prompt(context)
        return self._request_email_json(prompt)

    def rewrite_email(self, context: dict[str, Any]) -> dict[str, str]:
        prompt = build_email_prompt(context, rewrite=True)
        return self._request_email_json(prompt)

    def _request_email_json(self, prompt: str) -> dict[str, str]:
        payload = {
            "model": self.model,
            "instructions": (
                "You write practical B2B follow-up email drafts. Return only valid JSON with subject and body."
            ),
            "input": prompt,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                "https://api.openai.com/v1/responses",
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AIProviderError(f"OpenAI provider request failed with status {exc.response.status_code}.") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError("OpenAI provider request failed.") from exc

        response_payload = response.json()
        response_text = self._extract_text(response_payload)
        return parse_email_response_text(response_text)

    @staticmethod
    def _extract_text(response_payload: dict[str, Any]) -> str:
        output_text = response_payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        for item in response_payload.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text

        raise AIProviderError("OpenAI provider returned no email draft text.")
