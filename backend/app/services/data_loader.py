from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from app.core.errors import ValidationError


class DataLoader:
    @staticmethod
    def load_csv(file_path: str | Path) -> pd.DataFrame:
        return pd.read_csv(file_path)

    @staticmethod
    def load_excel(file_path: str | Path) -> pd.DataFrame:
        return pd.read_excel(file_path)

    @staticmethod
    def load_by_file_path(file_path: str | Path) -> pd.DataFrame:
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension == ".csv":
            return DataLoader.load_csv(path)

        if extension in {".xlsx", ".xls"}:
            return DataLoader.load_excel(path)

        raise ValidationError(
            "Unsupported file format. Please upload a CSV or Excel file.",
            details={"file_extension": extension or "missing"},
        )

    @staticmethod
    def validate_dataframe_not_empty(dataframe: pd.DataFrame) -> None:
        if dataframe.empty or len(dataframe.columns) == 0:
            raise ValidationError("The uploaded file does not contain any lead data.")

    @staticmethod
    def normalize_column_names(dataframe: pd.DataFrame) -> pd.DataFrame:
        normalized_dataframe = dataframe.copy()
        seen_names: dict[str, int] = {}
        normalized_columns: list[str] = []

        for column in normalized_dataframe.columns:
            normalized_name = DataLoader._normalize_column_name(str(column))
            count = seen_names.get(normalized_name, 0)
            seen_names[normalized_name] = count + 1

            if count:
                normalized_name = f"{normalized_name}_{count + 1}"

            normalized_columns.append(normalized_name)

        normalized_dataframe.columns = normalized_columns
        return normalized_dataframe

    @staticmethod
    def _normalize_column_name(column_name: str) -> str:
        normalized = column_name.strip().lower()
        normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
        normalized = normalized.strip("_")
        return normalized or "unnamed_column"
