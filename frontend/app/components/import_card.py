from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

import streamlit as st

ImportAction = Literal["process", "score", "delete"]


def render_import_card(lead_import: dict[str, Any]) -> ImportAction | None:
    import_id = int(lead_import["id"])
    status = str(lead_import.get("status", "unknown"))

    with st.container(border=True):
        title_columns = st.columns([3, 1])
        title_columns[0].subheader(str(lead_import.get("original_filename", "Lead import")))
        title_columns[1].markdown(f"**Status:** {status.title()}")

        detail_columns = st.columns(4)
        detail_columns[0].metric("Rows", lead_import.get("rows_count", 0))
        detail_columns[1].metric("Columns", lead_import.get("columns_count", 0))
        detail_columns[2].metric("File Type", str(lead_import.get("file_type", "")).upper())
        detail_columns[3].metric("Uploaded", _format_datetime(lead_import.get("created_at")))

        columns = lead_import.get("columns_json") or []
        if columns:
            st.caption("Detected columns")
            st.write(", ".join(str(column) for column in columns))

        button_columns = st.columns([1, 1, 1, 4])
        process_clicked = button_columns[0].button(
            "Process",
            key=f"process_import_{import_id}",
            use_container_width=True,
        )
        score_clicked = button_columns[1].button(
            "Score Leads",
            key=f"score_import_{import_id}",
            use_container_width=True,
        )
        delete_clicked = button_columns[2].button(
            "Delete",
            key=f"delete_import_{import_id}",
            use_container_width=True,
        )

    if process_clicked:
        return "process"
    if score_clicked:
        return "score"
    if delete_clicked:
        return "delete"
    return None


def _format_datetime(value: Any) -> str:
    if not value:
        return "Unknown"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value[:10]
        return parsed.strftime("%Y-%m-%d")
    return str(value)
