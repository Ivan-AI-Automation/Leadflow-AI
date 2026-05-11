from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
import re
from typing import Any


ScoreInput = Mapping[str, Any] | object

BREAKDOWN_KEYS = [
    "contact_completeness",
    "business_value",
    "urgency",
    "source_quality",
    "context_quality",
    "status_need",
]

CLOSED_STATUSES = {"closed", "lost"}
PRIORITY_STATUSES = {"new", "follow-up", "follow up", "follow_up"}


class LeadScoringService:
    @staticmethod
    def score_lead(lead: ScoreInput) -> dict[str, Any]:
        breakdown = {
            "contact_completeness": LeadScoringService._score_contact_completeness(lead),
            "business_value": LeadScoringService._score_business_value(lead),
            "urgency": LeadScoringService._score_urgency(lead),
            "source_quality": LeadScoringService._score_source_quality(lead),
            "context_quality": LeadScoringService._score_context_quality(lead),
            "status_need": LeadScoringService._score_status_need(lead),
        }

        score = sum(breakdown.values())
        status = LeadScoringService._normalized_value(lead, "status")

        # Closed and lost leads stay visible in the pipeline, but they should
        # never compete with active follow-up work.
        if status in CLOSED_STATUSES:
            score = 0
            breakdown = {key: 0 for key in BREAKDOWN_KEYS}

        score = max(0, min(100, int(score)))
        category = LeadScoringService.category_for_score(score)

        return {
            "score": score,
            "category": category,
            "breakdown": breakdown,
            "recommendation": LeadScoringService.recommendation_for_score(score, category, status),
        }

    @staticmethod
    def category_for_score(score: int) -> str:
        if score >= 80:
            return "Hot"
        if score >= 60:
            return "Warm"
        if score >= 40:
            return "Nurture"
        return "Low Priority"

    @staticmethod
    def recommendation_for_score(score: int, category: str, status: str | None = None) -> str:
        if status in CLOSED_STATUSES:
            return "Do not prioritize this lead because it is already closed or lost."
        if category == "Hot":
            return "Prioritize this lead within 24 hours."
        if category == "Warm":
            return "Follow up within the next few business days."
        if category == "Nurture":
            return "Add this lead to a nurture sequence and follow up when timing improves."
        return "Keep this lead as low priority until more contact or buying intent is available."

    @staticmethod
    def _score_contact_completeness(lead: ScoreInput) -> int:
        score = 0
        if LeadScoringService._has_value(lead, "email"):
            score += 10
        if LeadScoringService._has_value(lead, "phone"):
            score += 8
        if LeadScoringService._has_value(lead, "company_name") or LeadScoringService._has_value(lead, "website"):
            score += 7
        return min(score, 25)

    @staticmethod
    def _score_business_value(lead: ScoreInput) -> int:
        score = 0
        deal_value = LeadScoringService._numeric_value(LeadScoringService._value(lead, "deal_value"))

        if deal_value is not None:
            if deal_value >= Decimal("25000"):
                score += 10
            elif deal_value >= Decimal("10000"):
                score += 8
            elif deal_value > 0:
                score += 5

        if LeadScoringService._has_value(lead, "budget_range"):
            score += 5

        if LeadScoringService._has_value(lead, "company_name"):
            score += 3
        if LeadScoringService._has_value(lead, "industry"):
            score += 2

        return min(score, 20)

    @staticmethod
    def _score_urgency(lead: ScoreInput) -> int:
        score = 0
        timeline = LeadScoringService._normalized_value(lead, "timeline") or ""
        interest_level = LeadScoringService._normalized_value(lead, "interest_level") or ""
        urgency = LeadScoringService._normalized_value(lead, "urgency") or ""
        notes = LeadScoringService._normalized_value(lead, "notes") or ""
        combined_timing_text = " ".join([timeline, urgency, notes])

        if LeadScoringService._contains_any(
            combined_timing_text,
            ["urgent", "this week", "asap", "immediate", "immediately"],
        ):
            score += 10
        elif "this month" in combined_timing_text:
            score += 8
        elif "30-60 days" in combined_timing_text or "30 to 60 days" in combined_timing_text:
            score += 6
        elif "this quarter" in combined_timing_text:
            score += 5
        elif "60-90 days" in combined_timing_text or "60 to 90 days" in combined_timing_text:
            score += 3

        if interest_level == "high":
            score += 6
        elif interest_level == "medium":
            score += 3

        if urgency == "high":
            score += 4
        elif urgency == "medium":
            score += 2

        return min(score, 20)

    @staticmethod
    def _score_source_quality(lead: ScoreInput) -> int:
        source = LeadScoringService._normalized_value(lead, "source") or ""

        if LeadScoringService._contains_any(source, ["demo request", "requested demo", "booked demo"]):
            return 15
        if "referral" in source:
            return 14
        if LeadScoringService._contains_any(source, ["inbound", "website", "web form", "form", "valuation form"]):
            return 12
        if LeadScoringService._contains_any(source, ["webinar", "open house", "conference", "trade show"]):
            return 9
        if LeadScoringService._contains_any(source, ["linkedin", "google ads", "facebook"]):
            return 7
        if LeadScoringService._contains_any(source, ["newsletter", "instagram"]):
            return 5
        if LeadScoringService._contains_any(source, ["cold list", "cold outreach", "cold"]):
            return 2
        return 0

    @staticmethod
    def _score_context_quality(lead: ScoreInput) -> int:
        score = 0
        notes = LeadScoringService._text_value(lead, "notes")

        if notes and len(notes) >= 20:
            score += 4
        elif notes:
            score += 2

        if LeadScoringService._has_value(lead, "job_title"):
            score += 2
        if LeadScoringService._has_value(lead, "industry"):
            score += 2
        if LeadScoringService._has_value(lead, "location"):
            score += 2

        return min(score, 10)

    @staticmethod
    def _score_status_need(lead: ScoreInput) -> int:
        status = LeadScoringService._normalized_value(lead, "status") or "new"

        if status in PRIORITY_STATUSES:
            return 10
        if status == "contacted":
            return 5
        if status in CLOSED_STATUSES:
            return 0
        return 3

    @staticmethod
    def _value(lead: ScoreInput, field_name: str) -> Any | None:
        if isinstance(lead, Mapping):
            return lead.get(field_name)
        return getattr(lead, field_name, None)

    @staticmethod
    def _has_value(lead: ScoreInput, field_name: str) -> bool:
        value = LeadScoringService._value(lead, field_name)
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True

    @staticmethod
    def _text_value(lead: ScoreInput, field_name: str) -> str | None:
        value = LeadScoringService._value(lead, field_name)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _normalized_value(lead: ScoreInput, field_name: str) -> str | None:
        text = LeadScoringService._text_value(lead, field_name)
        if text is None:
            return None
        return re.sub(r"\s+", " ", text).strip().lower()

    @staticmethod
    def _numeric_value(value: Any | None) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))

        try:
            normalized_value = str(value).replace(",", "").replace("$", "").replace(chr(163), "").strip()
            if not normalized_value:
                return None
            return Decimal(normalized_value)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _contains_any(text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)
