from __future__ import annotations

from typing import Any

import httpx

from app.core.errors import AIProviderError
from app.services.ai.base import AIProvider, build_email_prompt, parse_email_response_text


class GeminiProvider(AIProvider):
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str = "gemini-2.5-flash",
        timeout_seconds: int = 30,
    ) -> None:
        if not api_key:
            raise AIProviderError(
                "Gemini API key is missing. Set GEMINI_API_KEY in the environment.",
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
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "You write practical B2B follow-up email drafts. "
                                "Return only valid JSON with subject and body.\n\n"
                                f"{prompt}"
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
            },
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        try:
            response = httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AIProviderError(f"Gemini provider request failed with status {exc.response.status_code}.") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError("Gemini provider request failed.") from exc

        response_payload = response.json()
        response_text = self._extract_text(response_payload)
        return parse_email_response_text(response_text)

    @staticmethod
    def _extract_text(response_payload: dict[str, Any]) -> str:
        candidates = response_payload.get("candidates", [])
        for candidate in candidates:
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    return text

        raise AIProviderError("Gemini provider returned no email draft text.")
