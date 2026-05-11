from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st


def render_dashboard_charts(charts_payload: dict[str, Any]) -> None:
    charts = charts_payload.get("charts", [])
    if not charts:
        st.info("No chart data is available yet.")
        return

    for index, chart in enumerate(charts):
        with st.container(border=True):
            st.subheader(str(chart.get("title", "Chart")))
            figure = build_chart_figure(chart)
            st.plotly_chart(figure, use_container_width=True, key=f"dashboard_chart_{index}")


def build_chart_figure(chart: dict[str, Any]) -> go.Figure:
    chart_type = str(chart.get("type", "")).lower()

    if chart_type == "bar":
        figure = go.Figure(
            data=[
                go.Bar(
                    x=chart.get("x", []),
                    y=chart.get("y", []),
                    marker_color="#2563EB",
                )
            ]
        )
    elif chart_type == "pie":
        figure = go.Figure(
            data=[
                go.Pie(
                    labels=chart.get("labels", []),
                    values=chart.get("values", []),
                    hole=0.35,
                )
            ]
        )
    else:
        figure = go.Figure()
        figure.add_annotation(
            text=f"Unsupported chart type: {chart_type or 'unknown'}",
            showarrow=False,
        )

    figure.update_layout(
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        height=320,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": "#111827"},
    )
    return figure
