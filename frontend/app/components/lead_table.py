from __future__ import annotations

from typing import Any, Literal

import streamlit as st

LeadAction = Literal["open", "status", "score", "draft"]

STATUS_OPTIONS = ["New", "Contacted", "Follow-up", "Closed", "Lost"]


def render_lead_table(leads: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, LeadAction | None, str | None]:
    if not leads:
        st.info("No leads match the current filters.")
        return None, None, None

    table_rows = [_lead_to_table_row(lead) for lead in leads]
    st.dataframe(
        table_rows,
        use_container_width=True,
        hide_index=True,
        column_order=[
            "id",
            "name",
            "company",
            "email",
            "status",
            "category",
            "priority_score",
            "source",
        ],
    )

    lead_options = {f"#{lead['id']} - {_display_name(lead)}": lead for lead in leads}
    selected_label = st.selectbox("Select a lead for actions", options=list(lead_options.keys()))
    selected_lead = lead_options[selected_label]

    action_columns = st.columns([1, 1, 1, 1, 2])
    open_clicked = action_columns[0].button("Open Lead", use_container_width=True)

    new_status = action_columns[1].selectbox(
        "New Status",
        options=STATUS_OPTIONS,
        index=_status_index(str(selected_lead.get("status", "New"))),
        label_visibility="collapsed",
    )
    status_clicked = action_columns[2].button("Update Status", use_container_width=True)
    score_clicked = action_columns[3].button("Score Lead", use_container_width=True)
    draft_clicked = action_columns[4].button("Generate Email Draft", use_container_width=True)

    if open_clicked:
        return selected_lead, "open", None
    if status_clicked:
        return selected_lead, "status", new_status
    if score_clicked:
        return selected_lead, "score", None
    if draft_clicked:
        return selected_lead, "draft", None
    return selected_lead, None, None


def _lead_to_table_row(lead: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": lead.get("id"),
        "name": _display_name(lead),
        "company": lead.get("company_name") or "",
        "email": lead.get("email") or "",
        "status": lead.get("status") or "",
        "category": lead.get("category") or "",
        "priority_score": lead.get("priority_score") or 0,
        "source": lead.get("source") or "",
    }


def _display_name(lead: dict[str, Any]) -> str:
    name_parts = [lead.get("first_name"), lead.get("last_name")]
    name = " ".join(str(part) for part in name_parts if part)
    return name or str(lead.get("company_name") or "Unnamed Lead")


def _status_index(status: str) -> int:
    if status in STATUS_OPTIONS:
        return STATUS_OPTIONS.index(status)
    return 0
