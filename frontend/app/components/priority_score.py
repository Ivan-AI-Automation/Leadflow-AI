from __future__ import annotations

from typing import Any

import streamlit as st


def render_priority_score(score: int | float | None, category: str | None = None) -> None:
    numeric_score = int(score or 0)
    st.metric("Priority Score", numeric_score)
    st.progress(min(max(numeric_score, 0), 100) / 100)
    if category:
        st.caption(f"Category: {category}")


def render_score_breakdown(score_payload: dict[str, Any] | None) -> None:
    if not score_payload:
        st.info("No score breakdown is available yet. Score this lead to see the explanation.")
        return

    render_priority_score(score_payload.get("score"), str(score_payload.get("category", "")))

    recommendation = score_payload.get("recommendation")
    if recommendation:
        st.write(str(recommendation))

    breakdown = score_payload.get("score_breakdown_json") or {}
    if breakdown:
        st.subheader("Score Breakdown")
        for label, value in breakdown.items():
            readable_label = str(label).replace("_", " ").title()
            st.write(f"**{readable_label}:** {value}")
