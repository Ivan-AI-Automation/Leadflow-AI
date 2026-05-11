from __future__ import annotations

import streamlit as st

from app.components.charts import render_dashboard_charts
from app.components.kpi_cards import render_dashboard_kpis
from app.components.sidebar import render_sidebar
from app.services.api_client import APIClientError
from app.services.dashboard_client import get_dashboard_charts, get_dashboard_summary
from app.utils.session import initialize_session_state, require_authentication


st.set_page_config(
    page_title="Dashboard | LeadFlow AI",
    layout="wide",
)

initialize_session_state()
require_authentication()
render_sidebar("Dashboard")

st.title("Dashboard")
st.caption("Lead pipeline health, follow-up readiness, and data quality.")

try:
    summary = get_dashboard_summary()
    charts = get_dashboard_charts()
except APIClientError as exc:
    st.error(exc.message)
else:
    render_dashboard_kpis(summary)
    if summary.get("total_leads", 0) == 0:
        st.info(
            "No leads have been processed yet. Upload a sample file, process the import, and score the leads to populate this dashboard."
        )
    st.divider()
    render_dashboard_charts(charts)

    if st.toggle("Show debug payload", value=False):
        st.subheader("Debug Payload")
        st.json({"summary": summary, "charts": charts})
