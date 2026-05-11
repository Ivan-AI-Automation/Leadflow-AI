from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.import_card import render_import_card
from app.components.sidebar import render_sidebar
from app.services.api_client import APIClientError
from app.services.import_client import delete_import, list_imports, process_import
from app.services.scoring_client import score_import
from app.utils.session import initialize_session_state, require_authentication

IMPORT_ACTION_MESSAGE_KEY = "import_action_message"
IMPORT_ACTION_ERROR_KEY = "import_action_error"


def _set_action_message(message: str) -> None:
    st.session_state[IMPORT_ACTION_MESSAGE_KEY] = message
    st.session_state[IMPORT_ACTION_ERROR_KEY] = None


def _set_action_error(message: str) -> None:
    st.session_state[IMPORT_ACTION_ERROR_KEY] = message
    st.session_state[IMPORT_ACTION_MESSAGE_KEY] = None


def _render_stored_messages() -> None:
    message = st.session_state.get(IMPORT_ACTION_MESSAGE_KEY)
    error = st.session_state.get(IMPORT_ACTION_ERROR_KEY)
    if message:
        st.success(str(message))
        st.session_state[IMPORT_ACTION_MESSAGE_KEY] = None
    if error:
        st.error(str(error))
        st.session_state[IMPORT_ACTION_ERROR_KEY] = None


def _render_process_result(result: dict[str, Any]) -> None:
    st.write(result.get("readable_summary", "Import processed successfully."))
    metric_columns = st.columns(4)
    metric_columns[0].metric("Created Leads", result.get("created_leads_count", 0))
    metric_columns[1].metric("Quality Score", result.get("quality_score", 0))
    metric_columns[2].metric("Missing Email", result.get("missing_email_count", 0))
    metric_columns[3].metric("Duplicates", result.get("duplicate_lead_count", 0))


def _render_score_result(result: dict[str, Any]) -> None:
    metric_columns = st.columns(5)
    metric_columns[0].metric("Total Scored", result.get("total_scored", 0))
    metric_columns[1].metric("Hot", result.get("hot_count", 0))
    metric_columns[2].metric("Warm", result.get("warm_count", 0))
    metric_columns[3].metric("Nurture", result.get("nurture_count", 0))
    metric_columns[4].metric("Low Priority", result.get("low_priority_count", 0))


st.set_page_config(
    page_title="Imports | LeadFlow AI",
    layout="wide",
)

initialize_session_state()
require_authentication()
render_sidebar("Imports")

st.title("Imports")
st.caption("Review uploaded lead files, process them into leads, and score imported leads.")

_render_stored_messages()

refresh_clicked = st.button("Refresh Imports", use_container_width=False)
if refresh_clicked:
    st.rerun()

try:
    imports = list_imports()
except APIClientError as exc:
    st.error(exc.message)
else:
    if not imports:
        st.info(
            "No imports found yet. Start with the Upload Leads page and use one of the fictional sample files if you want a quick demo."
        )
    else:
        for lead_import in imports:
            action = render_import_card(lead_import)
            import_id = int(lead_import["id"])

            if action == "process":
                try:
                    with st.spinner("Processing import..."):
                        process_result = process_import(import_id)
                except APIClientError as exc:
                    _set_action_error(exc.message)
                    st.rerun()
                else:
                    st.success("Import processed successfully.")
                    _render_process_result(process_result)

            if action == "score":
                try:
                    with st.spinner("Scoring imported leads..."):
                        score_result = score_import(import_id)
                except APIClientError as exc:
                    _set_action_error(exc.message)
                    st.rerun()
                else:
                    st.success("Imported leads scored successfully.")
                    _render_score_result(score_result)

            if action == "delete":
                try:
                    delete_import(import_id)
                except APIClientError as exc:
                    _set_action_error(exc.message)
                else:
                    _set_action_message("Import deleted successfully.")
                st.rerun()
