from __future__ import annotations

import streamlit as st

from app.components.sidebar import render_sidebar
from app.services.api_client import APIClientError, api_client
from app.services.dashboard_client import get_dashboard_summary
from app.utils.session import initialize_session_state, require_authentication


st.set_page_config(
    page_title="LeadFlow AI Dashboard",
    layout="wide",
)

initialize_session_state()
require_authentication()
render_sidebar("Dashboard")

st.title("Dashboard")
st.caption("Lead pipeline overview and follow-up readiness.")

try:
    health = api_client.get("/api/v1/health", authenticated=False)
except APIClientError as exc:
    health = None
    st.warning(exc.message)

if health:
    st.success("Backend connection is healthy.")

try:
    summary = get_dashboard_summary()
except APIClientError as exc:
    st.info("Dashboard metrics will appear after the backend is available and leads have been added.")
    st.caption(exc.message)
else:
    metric_columns = st.columns(4)
    metric_columns[0].metric("Total Leads", summary.get("total_leads", 0))
    metric_columns[1].metric("Hot Leads", summary.get("hot_leads", 0))
    metric_columns[2].metric("Follow-up Leads", summary.get("follow_up_leads", 0))
    metric_columns[3].metric("Approved Drafts", summary.get("drafts_approved", 0))

    st.divider()
    st.subheader("Pipeline Snapshot")
    status_columns = st.columns(5)
    status_columns[0].metric("New", summary.get("new_leads", 0))
    status_columns[1].metric("Contacted", summary.get("contacted_leads", 0))
    status_columns[2].metric("Follow-up", summary.get("follow_up_leads", 0))
    status_columns[3].metric("Closed", summary.get("closed_leads", 0))
    status_columns[4].metric("Lost", summary.get("lost_leads", 0))

    st.subheader("Data Quality")
    quality_columns = st.columns(3)
    quality_columns[0].metric("Missing Email", summary.get("missing_email_count", 0))
    quality_columns[1].metric("Missing Phone", summary.get("missing_phone_count", 0))
    quality_columns[2].metric("Average Priority Score", summary.get("average_priority_score", 0.0))

st.divider()
st.subheader("Next Steps")
st.write("Use the upcoming lead import, scoring, draft review, and export pages to run the full LeadFlow AI workflow.")
