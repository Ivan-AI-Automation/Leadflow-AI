from __future__ import annotations

import streamlit as st

STATUS_COLORS = {
    "New": "#2563EB",
    "Contacted": "#0F766E",
    "Follow-up": "#B45309",
    "Closed": "#15803D",
    "Lost": "#6B7280",
}

CATEGORY_COLORS = {
    "Hot": "#DC2626",
    "Warm": "#D97706",
    "Nurture": "#2563EB",
    "Low Priority": "#6B7280",
    "Unscored": "#9CA3AF",
}


def render_status_badge(status: str) -> None:
    _render_badge(status, STATUS_COLORS.get(status, "#6B7280"))


def render_category_badge(category: str) -> None:
    _render_badge(category, CATEGORY_COLORS.get(category, "#6B7280"))


def _render_badge(label: str, color: str) -> None:
    st.markdown(
        (
            "<span style='display:inline-block;padding:0.2rem 0.55rem;"
            f"border-radius:0.35rem;background:{color};color:white;"
            "font-size:0.8rem;font-weight:600;'>"
            f"{label}</span>"
        ),
        unsafe_allow_html=True,
    )
