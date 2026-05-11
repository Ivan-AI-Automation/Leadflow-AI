import pandas as pd
import pytest

from app.core.errors import ValidationError
from app.services.data_loader import DataLoader
from app.services.lead_cleaning_service import LeadCleaningService
from app.services.lead_validation_service import LeadValidationService


def test_normalize_column_names_returns_clean_unique_columns() -> None:
    dataframe = pd.DataFrame(
        {
            "First Name": ["Maya"],
            "Email Address": ["maya@example.com"],
            "Email-Address": ["maya.secondary@example.com"],
            " Deal Value ": [10000],
        }
    )

    normalized = DataLoader.normalize_column_names(dataframe)

    assert list(normalized.columns) == [
        "first_name",
        "email_address",
        "email_address_2",
        "deal_value",
    ]
    assert list(dataframe.columns) == ["First Name", "Email Address", "Email-Address", " Deal Value "]


def test_validate_dataframe_not_empty_rejects_empty_dataframe() -> None:
    with pytest.raises(ValidationError):
        DataLoader.validate_dataframe_not_empty(pd.DataFrame())


def test_normalization_cleans_text_email_phone_budget_and_timeline() -> None:
    dataframe = pd.DataFrame(
        {
            "first_name": ["  Maya  "],
            "email": ["  MAYA.PATEL@EXAMPLE.COM  "],
            "phone": [" +1 (415) 555-0134 "],
            "budget_range": ["  15k - 25k  "],
            "timeline": [" 30 to 60 days "],
        }
    )

    cleaned = LeadCleaningService.normalize_text_fields(dataframe)
    cleaned = LeadCleaningService.normalize_email(cleaned)
    cleaned = LeadCleaningService.normalize_phone(cleaned)
    cleaned = LeadCleaningService.normalize_budget_range(cleaned)
    cleaned = LeadCleaningService.normalize_timeline(cleaned)

    assert cleaned.loc[0, "first_name"] == "Maya"
    assert cleaned.loc[0, "email"] == "maya.patel@example.com"
    assert cleaned.loc[0, "phone"] == "+14155550134"
    assert cleaned.loc[0, "budget_range"] == "15k-25k"
    assert cleaned.loc[0, "timeline"] == "30-60 days"


def test_remove_empty_rows_does_not_mutate_original_dataframe() -> None:
    dataframe = pd.DataFrame(
        [
            {"first_name": "Maya", "email": "maya@example.com"},
            {"first_name": "   ", "email": ""},
        ]
    )

    cleaned = LeadCleaningService.remove_empty_rows(dataframe)

    assert len(cleaned) == 1
    assert len(dataframe) == 2


def test_detect_missing_contact_data_returns_business_readable_counts() -> None:
    dataframe = pd.DataFrame(
        [
            {"first_name": "Maya", "email": "maya@example.com", "phone": "+14155550134"},
            {"first_name": "Jordan", "email": "", "phone": "+15125550199"},
            {"first_name": "Elena", "email": "elena@example.com", "phone": ""},
            {"first_name": "Noah", "email": "", "phone": ""},
        ]
    )

    result = LeadValidationService.detect_missing_contact_data(dataframe)

    assert result["missing_email_count"] == 2
    assert result["missing_phone_count"] == 2
    assert result["missing_all_contact_count"] == 1
    assert result["rows_missing_all_contact"] == [3]
    assert "missing an email address" in str(result["readable_summary"])


def test_detect_duplicate_leads_uses_email_phone_and_name_company_keys() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "first_name": "Maya",
                "last_name": "Patel",
                "company_name": "Northstar Homes",
                "email": "maya@example.com",
                "phone": "",
            },
            {
                "first_name": "Maya",
                "last_name": "Patel",
                "company_name": "Northstar Homes",
                "email": "maya@example.com",
                "phone": "+14155550134",
            },
            {
                "first_name": "Jordan",
                "last_name": "Lee",
                "company_name": "BrightPath Marketing",
                "email": "",
                "phone": "+15125550199",
            },
            {
                "first_name": "Jordan",
                "last_name": "Lee",
                "company_name": "BrightPath Marketing",
                "email": "",
                "phone": "+1 (512) 555-0199",
            },
        ]
    )

    duplicates = LeadCleaningService.detect_duplicate_leads(dataframe)

    assert len(duplicates) == 4
    assert set(duplicates["duplicate_key"]) == {
        "email:maya@example.com",
        "phone:+15125550199",
    }


def test_infer_lead_dataset_type() -> None:
    recruitment_dataframe = pd.DataFrame(
        columns=["first_name", "last_name", "company_name", "hiring_need", "role_type", "urgency"]
    )
    real_estate_dataframe = pd.DataFrame(
        columns=["first_name", "last_name", "property_type", "budget_range", "timeline"]
    )
    b2b_dataframe = pd.DataFrame(
        columns=["first_name", "last_name", "company_name", "job_title", "deal_value", "industry"]
    )

    assert LeadValidationService.infer_lead_dataset_type(recruitment_dataframe) == "recruitment"
    assert LeadValidationService.infer_lead_dataset_type(real_estate_dataframe) == "real_estate"
    assert LeadValidationService.infer_lead_dataset_type(b2b_dataframe) == "b2b_service"


def test_build_import_quality_report_calculates_score_and_summary() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "first_name": "Maya",
                "last_name": "Patel",
                "company_name": "Northstar Homes",
                "email": "maya@example.com",
                "phone": "+14155550134",
            },
            {
                "first_name": "Jordan",
                "last_name": "Lee",
                "company_name": "",
                "email": "",
                "phone": "+15125550199",
            },
            {
                "first_name": "Jordan",
                "last_name": "Lee",
                "company_name": "",
                "email": "",
                "phone": "+1 (512) 555-0199",
            },
            {
                "first_name": "",
                "last_name": "",
                "company_name": "",
                "email": "",
                "phone": "",
            },
        ]
    )

    report = LeadValidationService.build_import_quality_report(dataframe)

    assert report["row_count"] == 3
    assert report["column_count"] == 5
    assert report["missing_email_count"] == 2
    assert report["missing_phone_count"] == 0
    assert report["missing_company_count"] == 2
    assert report["duplicate_lead_count"] == 2
    assert report["empty_row_count"] == 1
    assert report["quality_score"] == 55
    assert "quality score is 55/100" in str(report["readable_summary"])
