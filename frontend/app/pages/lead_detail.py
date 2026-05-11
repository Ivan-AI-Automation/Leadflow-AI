from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.lead_status_badge import render_category_badge, render_status_badge
from app.components.priority_score import render_score_breakdown
from app.components.sidebar import render_sidebar
from app.services.api_client import APIClientError
from app.services.email_draft_client import generate_email_draft
from app.services.lead_client import get_lead, list_lead_activities, update_lead_status
from app.services.scoring_client import get_lead_score, score_lead
from app.utils.session import initialize_session_state, require_authentication

STATUS_OPTIONS = ["New", "Contacted", "Follow-up", "Closed", "Lost"]


def _query_lead_id() -> int | None:
    value = st.query_params.get("lead_id")
    if isinstance(value, list):
        value = value[0] if value else None
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _display_name(lead: dict[str, Any]) -> str:
    name_parts = [lead.get("first_name"), lead.get("last_name")]
    name = " ".join(str(part) for part in name_parts if part)
    return name or str(lead.get("company_name") or "Unnamed Lead")


def _render_profile(lead: dict[str, Any]) -> None:
    st.subheader("Lead Profile")
    badge_columns = st.columns([1, 1, 4])
    with badge_columns[0]:
        render_status_badge(str(lead.get("status", "")))
    with badge_columns[1]:
        render_category_badge(str(lead.get("category", "")))

    detail_columns = st.columns(2)
    with detail_columns[0]:
        st.write(f"**Company:** {lead.get('company_name') or 'Not provided'}")
        st.write(f"**Job Title:** {lead.get('job_title') or 'Not provided'}")
        st.write(f"**Industry:** {lead.get('industry') or 'Not provided'}")
        st.write(f"**Location:** {lead.get('location') or 'Not provided'}")
    with detail_columns[1]:
        st.write(f"**Email:** {lead.get('email') or 'Missing'}")
        st.write(f"**Phone:** {lead.get('phone') or 'Missing'}")
        st.write(f"**Source:** {lead.get('source') or 'Not provided'}")
        st.write(f"**Timeline:** {lead.get('timeline') or 'Not provided'}")

    notes = lead.get("notes")
    if notes:
        st.write("**Notes**")
        st.write(str(notes))


def _render_missing_fields(lead: dict[str, Any]) -> None:
    missing_fields = lead.get("missing_fields_json") or []
    st.subheader("Missing Fields")
    if missing_fields:
        st.warning(", ".join(str(field).replace("_", " ").title() for field in missing_fields))
    else:
        st.success("No critical missing fields recorded.")


def _render_activity_history(activities: list[dict[str, Any]]) -> None:
    st.subheader("Activity History")
    if not activities:
        st.info("No activity has been recorded for this lead yet.")
        return

    for activity in activities:
        with st.container(border=True):
            st.write(str(activity.get("description", "Activity recorded.")))
            st.caption(f"{activity.get('activity_type', 'activity')} | {str(activity.get('created_at', ''))[:19]}")


st.set_page_config(
    page_title="Lead Detail | LeadFlow AI",
    layout="wide",
)

initialize_session_state()
require_authentication()
render_sidebar("Lead Detail")

lead_id = _query_lead_id()
if lead_id is None:
    st.title("Lead Detail")
    st.info("Select a lead from the Leads page to view details.")
    if st.button("Open Leads"):
        st.switch_page("pages/leads.py")
    st.stop()

try:
    lead = get_lead(lead_id)
except APIClientError as exc:
    st.error(exc.message)
    st.stop()

st.title(_display_name(lead))
st.caption(f"Lead ID: {lead_id}")

top_actions = st.columns([1, 1, 1, 3])
if top_actions[0].button("Back to Leads", use_container_width=True):
    st.switch_page("pages/leads.py")

selected_status = top_actions[1].selectbox(
    "Status",
    STATUS_OPTIONS,
    index=STATUS_OPTIONS.index(str(lead.get("status", "New"))) if lead.get("status") in STATUS_OPTIONS else 0,
    label_visibility="collapsed",
)
if top_actions[2].button("Update Status", use_container_width=True):
    try:
        lead = update_lead_status(lead_id, selected_status)
    except APIClientError as exc:
        st.error(exc.message)
    else:
        st.success("Lead status updated.")

left_column, right_column = st.columns([2, 1])

with left_column:
    _render_profile(lead)
    st.divider()
    _render_missing_fields(lead)

with right_column:
    try:
        score_payload = get_lead_score(lead_id)
    except APIClientError:
        score_payload = None
    render_score_breakdown(score_payload)

    if st.button("Score Lead", type="primary", use_container_width=True):
        try:
            score_payload = score_lead(lead_id)
        except APIClientError as exc:
            st.error(exc.message)
        else:
            st.success(f"Lead scored as {score_payload.get('category')} with score {score_payload.get('score')}.")
            st.rerun()

    if st.button("Generate Email Draft", use_container_width=True):
        try:
            generate_email_draft(lead_id, tone="Professional")
        except APIClientError as exc:
            st.error(exc.message)
        else:
            st.success("Email draft generated.")

st.divider()

try:
    activities = list_lead_activities(lead_id)
except APIClientError as exc:
    st.warning(exc.message)
    activities = []

_render_activity_history(activities)

if st.toggle("Show debug payload", value=False):
    st.subheader("Debug Payload")
    st.json({"lead": lead, "score": score_payload, "activities": activities})
