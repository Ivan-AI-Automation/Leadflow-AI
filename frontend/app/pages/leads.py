from __future__ import annotations

import streamlit as st

from app.components.lead_table import render_lead_table
from app.components.sidebar import render_sidebar
from app.services.api_client import APIClientError
from app.services.email_draft_client import generate_email_draft
from app.services.lead_client import list_leads, update_lead_status
from app.services.scoring_client import score_lead
from app.utils.session import initialize_session_state, require_authentication

STATUS_OPTIONS = ["All", "New", "Contacted", "Follow-up", "Closed", "Lost"]
CATEGORY_OPTIONS = ["All", "Hot", "Warm", "Nurture", "Low Priority", "Unscored"]


def _none_if_all(value: str) -> str | None:
    return None if value == "All" else value


def _open_lead_detail(lead_id: int) -> None:
    st.query_params["lead_id"] = str(lead_id)
    st.switch_page("pages/lead_detail.py")


def _has_active_filters() -> bool:
    return any(
        [
            search.strip(),
            status != "All",
            category != "All",
            source.strip(),
            missing_email,
            missing_phone,
        ]
    )


st.set_page_config(
    page_title="Leads | LeadFlow AI",
    layout="wide",
)

initialize_session_state()
require_authentication()
render_sidebar("Leads")

st.title("Leads")
st.caption("Search, filter, score, and move leads through the follow-up workflow.")

with st.container(border=True):
    filter_columns = st.columns([2, 1, 1, 1, 1, 1])
    search = filter_columns[0].text_input("Search", placeholder="Name, company, email, or notes")
    status = filter_columns[1].selectbox("Status", STATUS_OPTIONS)
    category = filter_columns[2].selectbox("Category", CATEGORY_OPTIONS)
    source = filter_columns[3].text_input("Source")
    missing_email = filter_columns[4].checkbox("Missing Email")
    missing_phone = filter_columns[5].checkbox("Missing Phone")

    sort_order = st.radio(
        "Priority Sort",
        options=["High to Low", "Low to High"],
        index=0,
        horizontal=True,
    )

try:
    response = list_leads(
        status=_none_if_all(status),
        category=_none_if_all(category),
        source=source.strip() or None,
        search=search.strip() or None,
        missing_email=True if missing_email else None,
        missing_phone=True if missing_phone else None,
        limit=100,
        offset=0,
        sort_by="priority_score",
        sort_order="desc" if sort_order == "High to Low" else "asc",
    )
except APIClientError as exc:
    st.error(exc.message)
else:
    leads = response.get("items", [])
    meta = response.get("meta", {})
    st.caption(f"Showing {len(leads)} of {meta.get('total', len(leads))} matching leads.")
    if not leads:
        if _has_active_filters():
            st.info("No leads match the current filters. Clear one or two filters and try again.")
        else:
            st.info("No leads yet. Upload and process a lead file, then return here to score and follow up.")
        selected_lead, action, new_status = None, None, None
    else:
        selected_lead, action, new_status = render_lead_table(leads)

    if selected_lead and action == "open":
        _open_lead_detail(int(selected_lead["id"]))

    if selected_lead and action == "status" and new_status:
        try:
            update_lead_status(int(selected_lead["id"]), new_status)
        except APIClientError as exc:
            st.error(exc.message)
        else:
            st.success("Lead status updated.")
            st.rerun()

    if selected_lead and action == "score":
        try:
            result = score_lead(int(selected_lead["id"]))
        except APIClientError as exc:
            st.error(exc.message)
        else:
            st.success(f"Lead scored as {result.get('category')} with score {result.get('score')}.")
            st.rerun()

    if selected_lead and action == "draft":
        try:
            generate_email_draft(int(selected_lead["id"]), tone="Professional")
        except APIClientError as exc:
            st.error(exc.message)
        else:
            st.success("Email draft generated.")
