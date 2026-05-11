from __future__ import annotations

import streamlit as st

from app.components.export_panel import render_export_controls, render_previous_exports
from app.components.sidebar import render_sidebar
from app.services.api_client import APIClientError, DownloadedFile
from app.services.export_client import (
    download_export,
    export_email_drafts_csv,
    export_email_drafts_excel,
    list_exports,
)
from app.utils.session import initialize_session_state, require_authentication


def _render_download(downloaded_file: DownloadedFile) -> None:
    st.download_button(
        "Save Export File",
        data=downloaded_file.content,
        file_name=downloaded_file.filename,
        mime=downloaded_file.content_type,
        use_container_width=False,
    )


st.set_page_config(
    page_title="Export Center | LeadFlow AI",
    layout="wide",
)

initialize_session_state()
require_authentication()
render_sidebar("Export Center")

st.title("Export Center")
st.caption("Create ready-to-send email draft files for human review. LeadFlow AI does not send emails.")

export_action = render_export_controls()

if export_action and export_action["action"] in {"csv", "excel"}:
    include_draft_status = bool(export_action["include_draft_status"])
    try:
        with st.spinner("Creating export file..."):
            if export_action["action"] == "csv":
                export_result = export_email_drafts_csv(include_draft_status=include_draft_status)
            else:
                export_result = export_email_drafts_excel(include_draft_status=include_draft_status)
    except APIClientError as exc:
        st.error(exc.message)
    else:
        st.success(f"Export created with {export_result.get('lead_count', 0)} email draft(s).")

st.divider()

try:
    exports_response = list_exports(limit=50, offset=0)
except APIClientError as exc:
    st.error(exc.message)
else:
    exports = exports_response.get("items", [])
    download_action = render_previous_exports(exports)

    if download_action and download_action["action"] == "download" and download_action["export_id"] is not None:
        try:
            with st.spinner("Preparing download..."):
                downloaded_file = download_export(int(download_action["export_id"]))
        except APIClientError as exc:
            st.error(exc.message)
        else:
            st.success("Export file is ready to download.")
            _render_download(downloaded_file)
