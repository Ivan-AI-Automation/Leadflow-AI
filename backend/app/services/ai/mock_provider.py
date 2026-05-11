from __future__ import annotations

from typing import Any

from app.services.ai.base import AIProvider, sanitize_ai_context


class MockAIProvider(AIProvider):
    def generate_follow_up_email(self, context: dict[str, Any]) -> dict[str, str]:
        sanitized_context = sanitize_ai_context(context)
        first_name = str(sanitized_context.get("first_name", "there"))
        company_name = str(sanitized_context.get("company_name", "your team"))
        sender_company_name = str(sanitized_context.get("sender_company_name", "our team"))
        lead_category = str(sanitized_context.get("lead_category", "lead"))
        business_type = str(sanitized_context.get("business_type", "business"))
        source = str(sanitized_context.get("source", "")).strip()
        timeline = str(sanitized_context.get("timeline", "")).strip()
        notes = str(sanitized_context.get("notes", "")).strip()
        email_tone = str(sanitized_context.get("email_tone", "Professional")).strip().lower()
        priority_score = sanitized_context.get("priority_score")

        subject = f"Following up with {company_name}"
        body_lines = [
            f"Hi {first_name},",
            "",
            f"I wanted to follow up because {company_name} looks like a relevant fit for our {business_type} work at {sender_company_name}.",
        ]

        if source:
            body_lines.append(f"I noticed this came through via {source}, so I wanted to keep the next step practical.")
        if timeline:
            body_lines.append(f"Your timeline was noted as {timeline}.")
        if notes:
            body_lines.append(f"The note I have is: {notes[:160]}")
        if priority_score is not None:
            body_lines.append(
                f"This is marked as a {lead_category} lead with a priority score of {priority_score}, so I wanted to keep the follow-up focused."
            )

        body_lines.extend(
            [
                "",
                "Would it be useful to compare notes and see whether there is a practical next step?",
                "",
                "Best,",
                sender_company_name,
            ]
        )

        if email_tone in {"short", "concise"}:
            body_lines = [
                f"Hi {first_name},",
                "",
                f"Quick follow-up to see whether {company_name} would like to explore a practical next step with {sender_company_name}.",
                "",
                "Best,",
                sender_company_name,
            ]

        return {
            "subject": subject,
            "body": "\n".join(body_lines),
        }

    def rewrite_email(self, context: dict[str, Any]) -> dict[str, str]:
        sanitized_context = sanitize_ai_context(context)
        first_name = str(sanitized_context.get("first_name", "there"))
        existing_subject = str(sanitized_context.get("existing_subject", "Following up"))
        existing_body = str(sanitized_context.get("existing_body", "")).strip()
        email_tone = str(sanitized_context.get("email_tone", "Professional")).strip().lower()

        tone_note = "short" if email_tone in {"short", "concise"} else "polished"
        body = (
            existing_body
            or f"Hi {first_name},\n\nI wanted to follow up and see whether a short conversation would be useful.\n\nBest,"
        )

        return {
            "subject": existing_subject,
            "body": f"{body}\n\n[Rewritten in a {tone_note}, business-friendly tone.]",
        }
