from __future__ import annotations

from typing import Any, Literal, TypedDict

import streamlit as st

ExportActionName = Literal["csv", "excel", "download"]


class ExportAction(TypedDict):
    action: ExportActionName
    export_id: int | None
    include_draft_status: bool


def render_export_controls() -> ExportAction | None:
    with st.container(border=True):
        st.subheader("Create Ready-to-Send Export")
        st.write("Export approved email drafts to files your team can review and send from their email tools.")
        include_draft_status = st.checkbox(
            "Also include drafts that are not approved yet",
            value=False,
            help="Approved drafts are always included. Draft-status emails should still be reviewed before use.",
        )
        action_columns = st.columns([1, 1, 3])
        csv_clicked = action_columns[0].button("Export CSV", type="primary", use_container_width=True)
        excel_clicked = action_columns[1].button("Export Excel", use_container_width=True)

    if csv_clicked:
        return {"action": "csv", "export_id": None, "include_draft_status": include_draft_status}
    if excel_clicked:
        return {"action": "excel", "export_id": None, "include_draft_status": include_draft_status}
    return None


def render_previous_exports(exports: list[dict[str, Any]]) -> ExportAction | None:
    st.subheader("Previous Exports")
    if not exports:
        st.info(
            "No exports have been created yet. Approve at least one email draft, then create a CSV or Excel export."
        )
        return None

    for export in exports:
        export_id = int(export["id"])
        with st.container(border=True):
            columns = st.columns([1, 1, 2, 2, 1])
            columns[0].metric("ID", export_id)
            columns[1].metric("Format", str(export.get("format", "")).upper())
            columns[2].metric("Lead Count", export.get("lead_count", 0))
            columns[3].write(f"Created: {str(export.get('created_at', ''))[:19]}")
            clicked = columns[4].button(
                "Download",
                key=f"download_export_{export_id}",
                use_container_width=True,
            )
            if clicked:
                return {"action": "download", "export_id": export_id, "include_draft_status": False}

    return None
