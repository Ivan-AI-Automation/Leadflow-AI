from __future__ import annotations

import re

import pandas as pd


class LeadCleaningService:
    @staticmethod
    def normalize_text_fields(dataframe: pd.DataFrame) -> pd.DataFrame:
        cleaned = dataframe.copy()

        for column in cleaned.columns:
            if pd.api.types.is_object_dtype(cleaned[column]) or pd.api.types.is_string_dtype(cleaned[column]):
                cleaned[column] = cleaned[column].map(LeadCleaningService._normalize_text_value)

        return cleaned

    @staticmethod
    def normalize_email(dataframe: pd.DataFrame, column: str = "email") -> pd.DataFrame:
        cleaned = dataframe.copy()
        if column not in cleaned.columns:
            return cleaned

        cleaned[column] = cleaned[column].map(LeadCleaningService._normalize_email_value)
        return cleaned

    @staticmethod
    def normalize_phone(dataframe: pd.DataFrame, column: str = "phone") -> pd.DataFrame:
        cleaned = dataframe.copy()
        if column not in cleaned.columns:
            return cleaned

        cleaned[column] = cleaned[column].map(LeadCleaningService._normalize_phone_value)
        return cleaned

    @staticmethod
    def normalize_budget_range(dataframe: pd.DataFrame, column: str = "budget_range") -> pd.DataFrame:
        cleaned = dataframe.copy()
        if column not in cleaned.columns:
            return cleaned

        cleaned[column] = cleaned[column].map(LeadCleaningService._normalize_budget_value)
        return cleaned

    @staticmethod
    def normalize_timeline(dataframe: pd.DataFrame, column: str = "timeline") -> pd.DataFrame:
        cleaned = dataframe.copy()
        if column not in cleaned.columns:
            return cleaned

        timeline_map = {
            "immediate": "Immediate",
            "asap": "Immediate",
            "this month": "This month",
            "this quarter": "This quarter",
            "30-60 days": "30-60 days",
            "30 to 60 days": "30-60 days",
            "60-90 days": "60-90 days",
            "60 to 90 days": "60-90 days",
            "next quarter": "Next quarter",
            "no fixed date": "No fixed date",
        }

        def normalize_timeline_value(value: object) -> object:
            text = LeadCleaningService._normalize_text_value(value)
            if pd.isna(text):
                return pd.NA
            compact_text = re.sub(r"\s+", " ", str(text).lower()).strip()
            return timeline_map.get(compact_text, str(text))

        cleaned[column] = cleaned[column].map(normalize_timeline_value)
        return cleaned

    @staticmethod
    def remove_empty_rows(dataframe: pd.DataFrame) -> pd.DataFrame:
        cleaned = dataframe.copy()
        if cleaned.empty:
            return cleaned

        missing_mask = cleaned.map(LeadCleaningService._is_missing_value)
        non_empty_rows = ~missing_mask.all(axis=1)
        return cleaned.loc[non_empty_rows].reset_index(drop=True)

    @staticmethod
    def detect_duplicate_leads(dataframe: pd.DataFrame) -> pd.DataFrame:
        if dataframe.empty:
            return dataframe.copy()

        working = dataframe.copy()
        duplicate_keys = working.apply(LeadCleaningService._build_duplicate_key, axis=1)
        duplicate_mask = duplicate_keys.duplicated(keep=False) & duplicate_keys.notna()
        duplicates = working.loc[duplicate_mask].copy()
        duplicates["duplicate_key"] = duplicate_keys.loc[duplicate_mask]
        return duplicates.reset_index(drop=True)

    @staticmethod
    def _normalize_text_value(value: object) -> object:
        if LeadCleaningService._is_missing_value(value):
            return pd.NA
        return re.sub(r"\s+", " ", str(value)).strip()

    @staticmethod
    def _normalize_email_value(value: object) -> object:
        text = LeadCleaningService._normalize_text_value(value)
        if pd.isna(text):
            return pd.NA
        return str(text).lower()

    @staticmethod
    def _normalize_phone_value(value: object) -> object:
        text = LeadCleaningService._normalize_text_value(value)
        if pd.isna(text):
            return pd.NA

        phone_text = str(text)
        has_plus_prefix = phone_text.startswith("+")
        digits = re.sub(r"\D", "", phone_text)
        if not digits:
            return pd.NA

        return f"+{digits}" if has_plus_prefix else digits

    @staticmethod
    def _normalize_budget_value(value: object) -> object:
        text = LeadCleaningService._normalize_text_value(value)
        if pd.isna(text):
            return pd.NA

        budget_text = str(text)
        budget_text = re.sub(r"\s*-\s*", "-", budget_text)
        budget_text = re.sub(r"\s+", " ", budget_text).strip()
        return budget_text

    @staticmethod
    def _is_missing_value(value: object) -> bool:
        if pd.isna(value):
            return True
        return str(value).strip() == ""

    @staticmethod
    def _build_duplicate_key(row: pd.Series) -> str | None:
        email = LeadCleaningService._row_value(row, "email")
        if email:
            return f"email:{email.lower()}"

        phone = LeadCleaningService._row_value(row, "phone")
        if phone:
            normalized_phone = LeadCleaningService._normalize_phone_value(phone)
            if not pd.isna(normalized_phone):
                return f"phone:{normalized_phone}"

        first_name = LeadCleaningService._row_value(row, "first_name")
        last_name = LeadCleaningService._row_value(row, "last_name")
        company_name = LeadCleaningService._row_value(row, "company_name")
        location = LeadCleaningService._row_value(row, "location")

        if first_name and last_name and company_name:
            return f"name_company:{first_name.lower()}:{last_name.lower()}:{company_name.lower()}"

        if first_name and last_name and location:
            return f"name_location:{first_name.lower()}:{last_name.lower()}:{location.lower()}"

        return None

    @staticmethod
    def _row_value(row: pd.Series, column: str) -> str | None:
        if column not in row:
            return None
        value = row[column]
        if LeadCleaningService._is_missing_value(value):
            return None
        return str(value).strip()
