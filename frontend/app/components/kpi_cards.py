from __future__ import annotations

from typing import Any

import streamlit as st


def render_dashboard_kpis(summary: dict[str, Any]) -> None:
    first_row = st.columns(3)
    first_row[0].metric("Total Leads", summary.get("total_leads", 0))
    first_row[1].metric("New Leads", summary.get("new_leads", 0))
    first_row[2].metric("Follow-up Leads", summary.get("follow_up_leads", 0))

    second_row = st.columns(3)
    second_row[0].metric("Hot Leads", summary.get("hot_leads", 0))
    second_row[1].metric("Missing Email", summary.get("missing_email_count", 0))
    second_row[2].metric("Average Priority Score", summary.get("average_priority_score", 0.0))
