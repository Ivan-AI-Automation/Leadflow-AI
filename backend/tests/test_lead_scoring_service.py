from decimal import Decimal
from types import SimpleNamespace

from app.services.lead_scoring_service import LeadScoringService


def test_hot_lead_scores_high_with_complete_contact_value_and_urgency() -> None:
    lead = {
        "email": "maya@example.com",
        "phone": "+14155550134",
        "company_name": "Northstar Homes",
        "website": "https://northstar.example",
        "deal_value": Decimal("32000"),
        "budget_range": "25k-50k",
        "industry": "Property Management",
        "timeline": "Immediate",
        "interest_level": "High",
        "source": "Referral",
        "job_title": "Operations Director",
        "location": "San Francisco, CA",
        "notes": "Asked for a proposal and wants an onboarding plan by next week.",
        "status": "New",
    }

    result = LeadScoringService.score_lead(lead)

    assert result == {
        "score": 95,
        "category": "Hot",
        "breakdown": {
            "contact_completeness": 25,
            "business_value": 20,
            "urgency": 16,
            "source_quality": 14,
            "context_quality": 10,
            "status_need": 10,
        },
        "recommendation": "Prioritize this lead within 24 hours.",
    }


def test_warm_lead_scores_medium_with_inbound_source_and_partial_timing() -> None:
    lead = {
        "email": "jordan@example.com",
        "phone": "",
        "company_name": "BrightPath Marketing",
        "deal_value": "9200",
        "budget_range": "5k-10k",
        "industry": "Marketing Agency",
        "timeline": "30-60 days",
        "interest_level": "Medium",
        "source": "Inbound form",
        "job_title": "Founder",
        "location": "Austin, TX",
        "notes": "Needs help cleaning CRM data before a new outbound campaign.",
        "status": "Contacted",
    }

    result = LeadScoringService.score_lead(lead)

    assert result["score"] == 68
    assert result["category"] == "Warm"
    assert result["breakdown"]["contact_completeness"] == 17
    assert result["breakdown"]["source_quality"] == 12
    assert result["recommendation"] == "Follow up within the next few business days."


def test_nurture_lead_scores_lower_when_contact_and_context_are_incomplete() -> None:
    lead = {
        "email": "",
        "phone": "+15125550199",
        "company_name": "Small Consultancy",
        "deal_value": None,
        "budget_range": "Under 5k",
        "timeline": "Next quarter",
        "interest_level": "Medium",
        "source": "Newsletter",
        "location": "Denver, CO",
        "notes": "Asked for examples.",
        "status": "New",
    }

    result = LeadScoringService.score_lead(lead)

    assert result["score"] == 45
    assert result["category"] == "Nurture"
    assert result["breakdown"] == {
        "contact_completeness": 15,
        "business_value": 8,
        "urgency": 3,
        "source_quality": 5,
        "context_quality": 4,
        "status_need": 10,
    }


def test_closed_or_lost_leads_are_not_prioritized() -> None:
    lead = {
        "email": "closed@example.com",
        "phone": "+14155550134",
        "company_name": "Closed Company",
        "deal_value": 50000,
        "budget_range": "50k+",
        "timeline": "Immediate",
        "interest_level": "High",
        "source": "Demo request",
        "job_title": "CEO",
        "industry": "SaaS",
        "location": "New York, NY",
        "notes": "Strong context but the opportunity has already been closed.",
        "status": "Closed",
    }

    result = LeadScoringService.score_lead(lead)

    assert result["score"] == 0
    assert result["category"] == "Low Priority"
    assert all(value == 0 for value in result["breakdown"].values())
    assert result["recommendation"] == "Do not prioritize this lead because it is already closed or lost."


def test_scoring_accepts_orm_like_objects() -> None:
    lead = SimpleNamespace(
        email="amelia@example.com",
        phone="+442055550141",
        company_name="Vertex Payments",
        website=None,
        deal_value=None,
        budget_range=None,
        industry=None,
        timeline=None,
        interest_level="High",
        urgency="High",
        source="Inbound form",
        job_title="People Director",
        location="London, UK",
        notes="Hiring need: Senior backend engineer. Urgency: High.",
        status="Follow-up",
    )

    result = LeadScoringService.score_lead(lead)

    assert result["score"] == 68
    assert result["category"] == "Warm"
    assert result["breakdown"]["urgency"] == 10
    assert result["breakdown"]["status_need"] == 10
