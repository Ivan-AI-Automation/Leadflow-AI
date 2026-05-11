from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.sidebar import render_sidebar
from app.services.api_client import APIClientError
from app.services.import_client import process_import, upload_import
from app.utils.session import initialize_session_state, require_authentication

LAST_UPLOADED_IMPORT_KEY = "last_uploaded_import"


def _render_upload_result(lead_import: dict[str, Any]) -> None:
    metric_columns = st.columns(4)
    metric_columns[0].metric("Import ID", lead_import.get("id", "-"))
    metric_columns[1].metric("Rows", lead_import.get("rows_count", 0))
    metric_columns[2].metric("Columns", lead_import.get("columns_count", 0))
    metric_columns[3].metric("Status", str(lead_import.get("status", "unknown")).title())

    st.write(f"**File:** {lead_import.get('original_filename', 'Uploaded file')}")
    columns = lead_import.get("columns_json") or []
    if columns:
        st.caption("Detected columns")
        st.write(", ".join(str(column) for column in columns))


def _render_process_result(result: dict[str, Any]) -> None:
    metric_columns = st.columns(4)
    metric_columns[0].metric("Created Leads", result.get("created_leads_count", 0))
    metric_columns[1].metric("Skipped Rows", result.get("skipped_rows_count", 0))
    metric_columns[2].metric("Quality Score", result.get("quality_score", 0))
    metric_columns[3].metric("Dataset Type", result.get("dataset_type", "generic"))

    summary = result.get("readable_summary")
    if summary:
        st.write(summary)


st.set_page_config(
    page_title="Upload Leads | LeadFlow AI",
    layout="wide",
)

initialize_session_state()
require_authentication()
render_sidebar("Upload Leads")

st.title("Upload Leads")
st.caption("Upload a CSV or Excel file. Lead validation and processing happen in the backend.")

uploaded_file = st.file_uploader(
    "Choose a lead file",
    type=["csv", "xlsx", "xls"],
    help="Accepted formats: CSV, XLSX, XLS.",
)

upload_columns = st.columns([1, 3])
upload_clicked = upload_columns[0].button(
    "Upload File",
    type="primary",
    use_container_width=True,
    disabled=uploaded_file is None,
)

if upload_clicked and uploaded_file is not None:
    try:
        uploaded_file.seek(0)
        with st.spinner("Uploading lead file..."):
            result = upload_import(uploaded_file)
    except APIClientError as exc:
        st.error(exc.message)
    else:
        st.session_state[LAST_UPLOADED_IMPORT_KEY] = result
        st.success("Lead file uploaded successfully.")

last_uploaded_import = st.session_state.get(LAST_UPLOADED_IMPORT_KEY)

if isinstance(last_uploaded_import, dict):
    st.divider()
    st.subheader("Upload Result")
    _render_upload_result(last_uploaded_import)

    process_clicked = st.button(
        "Process Import",
        type="primary",
        use_container_width=False,
        key=f"process_uploaded_import_{last_uploaded_import['id']}",
    )
    if process_clicked:
        try:
            with st.spinner("Processing import and creating lead records..."):
                process_result = process_import(int(last_uploaded_import["id"]))
        except APIClientError as exc:
            st.error(exc.message)
        else:
            st.success("Import processed successfully.")
            _render_process_result(process_result)
else:
    st.info("Upload a lead file to see its row and column summary.")
