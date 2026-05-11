from __future__ import annotations

from pathlib import Path

import pandas as pd


class CSVExportService:
    @staticmethod
    def write_email_drafts(rows: list[dict[str, object]], file_path: Path) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        dataframe = pd.DataFrame(rows)
        dataframe.to_csv(file_path, index=False)
