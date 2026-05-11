from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.email_draft_card import TONE_OPTIONS, render_email_draft_card
from app.components.sidebar import render_sidebar
from app.services.api_client import APIClientError
from app.services.email_draft_client import (
    approve_email_draft,
    archive_email_draft,
    generate_bulk_email_drafts,
    list_email_drafts,
    rewrite_email_draft,
    update_email_draft,
)
from app.services.lead_client import get_lead, list_leads
from app.utils.session import initialize_session_state, require_authentication

STATUS_OPTIONS = ["All", "Draft", "Approved", "Exported", "Archived"]
CATEGORY_OPTIONS = ["All", "Hot", "Warm", "Nurture", "Low Priority", "Unscored"]
LEAD_STATUS_OPTIONS = ["All", "New", "Contacted", "Follow-up", "Closed", "Lost"]


def _none_if_all(value: str) -> str | None:
    return None if value == "All" else value


def _lead_label(lead: dict[str, Any]) -> str:
    name_parts = [lead.get("first_name"), lead.get("last_name")]
    name = " ".join(str(part) for part in name_parts if part)
    display_name = name or str(lead.get("company_name") or "Unnamed Lead")
    company = lead.get("company_name") or "No company"
    return f"#{lead['id']} - {display_name} ({company})"


def _load_leads_for_drafts(drafts: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    leads_by_id: dict[int, dict[str, Any]] = {}
    for draft in drafts:
        lead_id = int(draft["lead_id"])
        if lead_id in leads_by_id:
            continue
        try:
            leads_by_id[lead_id] = get_lead(lead_id)
        except APIClientError:
            leads_by_id[lead_id] = {}
    return leads_by_id


def _render_skipped_leads(skipped: list[dict[str, Any]]) -> None:
    if not skipped:
        return
    st.warning("Some leads were skipped.")
    st.dataframe(skipped, use_container_width=True, hide_index=True)


st.set_page_config(
    page_title="Email Drafts | LeadFlow AI",
    layout="wide",
)

initialize_session_state()
require_authentication()
render_sidebar("Email Drafts")

st.title("Email Drafts")
st.caption("Review, edit, approve, rewrite, and archive AI-generated follow-up drafts. The system never sends emails.")

bulk_tab, review_tab = st.tabs(["Bulk Generation", "Draft Review"])

with bulk_tab:
    st.subheader("Generate Drafts for Selected Leads")
    with st.container(border=True):
        filter_columns = st.columns([1, 1, 1])
        lead_status = filter_columns[0].selectbox("Lead Status", LEAD_STATUS_OPTIONS)
        lead_category = filter_columns[1].selectbox("Lead Category", CATEGORY_OPTIONS)
        draft_tone = filter_columns[2].selectbox("Draft Tone", TONE_OPTIONS)

        business_columns = st.columns([1, 1])
        business_type = business_columns[0].text_input("Business Type", placeholder="B2B service business")
        sender_company_name = business_columns[1].text_input("Sender Company Name", placeholder="Your company")
        overwrite_existing = st.checkbox("Replace existing drafts for selected leads", value=False)

        try:
            lead_response = list_leads(
                status=_none_if_all(lead_status),
                category=_none_if_all(lead_category),
                missing_email=False,
                limit=200,
                offset=0,
                sort_by="priority_score",
                sort_order="desc",
            )
        except APIClientError as exc:
            st.error(exc.message)
            lead_response = {"items": []}

        leads = lead_response.get("items", [])
        lead_options = {_lead_label(lead): int(lead["id"]) for lead in leads}
        if not lead_options:
            st.info(
                "No leads with email addresses match these filters. Process an import or adjust the lead filters before generating drafts."
            )
        selected_labels = st.multiselect(
            "Select leads",
            options=list(lead_options.keys()),
            help="Only leads with email addresses are shown here.",
        )
        selected_lead_ids = [lead_options[label] for label in selected_labels]

        generate_clicked = st.button(
            "Generate Drafts",
            type="primary",
            disabled=not selected_lead_ids,
            use_container_width=False,
        )

    if generate_clicked:
        try:
            with st.spinner("Generating email drafts for selected leads..."):
                result = generate_bulk_email_drafts(
                    selected_lead_ids,
                    tone=draft_tone,
                    business_type=business_type.strip() or None,
                    sender_company_name=sender_company_name.strip() or None,
                    overwrite_existing=overwrite_existing,
                )
        except APIClientError as exc:
            st.error(exc.message)
        else:
            st.success(f"Created {result.get('created_count', 0)} draft(s).")
            _render_skipped_leads(result.get("skipped", []))

with review_tab:
    st.subheader("Review Drafts")
    filter_columns = st.columns([1, 1, 1, 2])
    draft_status = filter_columns[0].selectbox("Draft Status", STATUS_OPTIONS, key="draft_status_filter")
    draft_tone_filter = filter_columns[1].selectbox("Tone", ["All", *TONE_OPTIONS], key="draft_tone_filter")
    lead_category_filter = filter_columns[2].selectbox("Lead Category", CATEGORY_OPTIONS, key="draft_category_filter")
    search = filter_columns[3].text_input("Search", placeholder="Subject, body, lead, or company")

    try:
        draft_response = list_email_drafts(
            status=_none_if_all(draft_status),
            tone=_none_if_all(draft_tone_filter),
            lead_category=_none_if_all(lead_category_filter),
            search=search.strip() or None,
            limit=50,
            offset=0,
        )
    except APIClientError as exc:
        st.error(exc.message)
    else:
        drafts = draft_response.get("items", [])
        leads_by_id = _load_leads_for_drafts(drafts)
        st.caption(f"Showing {len(drafts)} draft(s).")

        if not drafts:
            if (
                draft_status == "All"
                and draft_tone_filter == "All"
                and lead_category_filter == "All"
                and not search.strip()
            ):
                st.info("No email drafts yet. Generate drafts from selected leads, then review and approve them here.")
            else:
                st.info("No email drafts match the current filters.")

        for draft in drafts:
            lead = leads_by_id.get(int(draft["lead_id"]))
            action = render_email_draft_card(draft, lead)
            if not action:
                continue

            draft_id = action["draft_id"]
            try:
                if action["action"] == "save":
                    with st.spinner("Saving draft edits..."):
                        update_email_draft(
                            draft_id,
                            {
                                "subject": action["subject"],
                                "body": action["body"],
                                "tone": action["tone"],
                            },
                        )
                    st.success("Draft saved.")
                    st.rerun()
                if action["action"] == "approve":
                    with st.spinner("Approving draft..."):
                        approve_email_draft(draft_id)
                    st.success("Draft approved.")
                    st.rerun()
                if action["action"] == "rewrite":
                    with st.spinner("Rewriting draft..."):
                        rewrite_email_draft(draft_id, tone=action["tone"] or "Professional")
                    st.success("Draft rewritten. Please review it before approval.")
                    st.rerun()
                if action["action"] == "archive":
                    with st.spinner("Archiving draft..."):
                        archive_email_draft(draft_id)
                    st.success("Draft archived.")
                    st.rerun()
            except APIClientError as exc:
                st.error(exc.message)
