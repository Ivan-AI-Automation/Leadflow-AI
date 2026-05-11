from __future__ import annotations

from typing import Any, Literal, TypedDict

import streamlit as st

DraftActionName = Literal["save", "approve", "rewrite", "archive"]
TONE_OPTIONS = ["Professional", "Friendly", "Direct", "Warm", "Short"]


class DraftAction(TypedDict):
    action: DraftActionName
    draft_id: int
    subject: str | None
    body: str | None
    tone: str | None


def render_email_draft_card(draft: dict[str, Any], lead: dict[str, Any] | None = None) -> DraftAction | None:
    draft_id = int(draft["id"])
    draft_status = str(draft.get("status", "Draft"))
    is_locked = draft_status in {"Exported", "Archived"}
    lead_name = _lead_name(lead)
    company_name = _company_name(lead)

    with st.container(border=True):
        header_columns = st.columns([3, 1, 1])
        header_columns[0].subheader(lead_name)
        header_columns[0].caption(company_name)
        header_columns[1].markdown(f"**Status:** {draft_status}")
        header_columns[2].markdown(f"**Tone:** {draft.get('tone', 'Professional')}")

        st.caption("AI-generated draft. Review and edit before using it with a lead.")
        if is_locked:
            st.info("This draft is locked because it has already been exported or archived.")

        with st.form(f"edit_draft_form_{draft_id}", clear_on_submit=False):
            subject = st.text_input(
                "Subject",
                value=str(draft.get("subject") or ""),
                key=f"draft_subject_{draft_id}",
            )
            body = st.text_area(
                "Body",
                value=str(draft.get("body") or ""),
                height=220,
                key=f"draft_body_{draft_id}",
            )
            tone = st.selectbox(
                "Tone",
                options=TONE_OPTIONS,
                index=_tone_index(str(draft.get("tone", "Professional"))),
                key=f"draft_tone_{draft_id}",
            )
            save_clicked = st.form_submit_button(
                "Save Edits",
                use_container_width=True,
                disabled=is_locked,
            )

        if save_clicked:
            return {
                "action": "save",
                "draft_id": draft_id,
                "subject": subject,
                "body": body,
                "tone": tone,
            }

        action_columns = st.columns([1, 1, 1, 2])
        approve_clicked = action_columns[0].button(
            "Approve",
            key=f"approve_draft_{draft_id}",
            use_container_width=True,
            disabled=draft_status != "Draft",
        )
        rewrite_tone = action_columns[1].selectbox(
            "Rewrite Tone",
            options=TONE_OPTIONS,
            index=_tone_index(str(draft.get("tone", "Professional"))),
            key=f"rewrite_tone_{draft_id}",
            label_visibility="collapsed",
        )
        rewrite_clicked = action_columns[2].button(
            "Rewrite",
            key=f"rewrite_draft_{draft_id}",
            use_container_width=True,
            disabled=is_locked,
        )
        archive_clicked = action_columns[3].button(
            "Archive",
            key=f"archive_draft_{draft_id}",
            use_container_width=True,
            disabled=draft_status == "Archived",
        )

    if approve_clicked:
        return {"action": "approve", "draft_id": draft_id, "subject": None, "body": None, "tone": None}
    if rewrite_clicked:
        return {"action": "rewrite", "draft_id": draft_id, "subject": None, "body": None, "tone": rewrite_tone}
    if archive_clicked:
        return {"action": "archive", "draft_id": draft_id, "subject": None, "body": None, "tone": None}
    return None


def _tone_index(tone: str) -> int:
    if tone in TONE_OPTIONS:
        return TONE_OPTIONS.index(tone)
    return 0


def _lead_name(lead: dict[str, Any] | None) -> str:
    if not lead:
        return "Lead unavailable"
    name_parts = [lead.get("first_name"), lead.get("last_name")]
    name = " ".join(str(part) for part in name_parts if part)
    return name or str(lead.get("company_name") or "Unnamed Lead")


def _company_name(lead: dict[str, Any] | None) -> str:
    if not lead:
        return "Company unavailable"
    return str(lead.get("company_name") or "No company provided")
