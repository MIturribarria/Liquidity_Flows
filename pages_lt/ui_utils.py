# -*- coding: utf-8 -*-
from __future__ import annotations

import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import dcc, html


BBVA_BLUE = "#001391"
BBVA_NAVY = "#072146"
BBVA_GREY = "#46536D"
BBVA_LIGHT_GREY = "#E2E6EA"
BBVA_RED = "#B00028"
BBVA_GREEN = "#024700"

BBVA_COLORS = [
    "#001391",
    "#85C8FF",
    "#46536D",
    "#88E783",
    "#070E46",
    "#8BE1E9",
    "#2B7BF4",
    "#108C97",
    "#9694FF",
    "#024700",
    "#E2E6EA",
    "#2DCCCD",
    "#1973B8",
    "#F7893B",
]


def page_title(title: str, subtitle: str | None = None):
    children = [
        html.H2(
            title,
            style={
                "color": BBVA_BLUE,
                "fontWeight": "bold",
                "marginBottom": "4px",
            },
        )
    ]
    if subtitle:
        children.append(
            html.Div(
                subtitle,
                style={
                    "fontSize": "13px",
                    "color": BBVA_GREY,
                    "marginBottom": "16px",
                },
            )
        )
    return html.Div(children)


def card(children, style: dict | None = None):
    base = {
        "backgroundColor": "white",
        "border": f"1px solid {BBVA_LIGHT_GREY}",
        "borderRadius": "10px",
        "boxShadow": "0 1px 4px rgba(7, 14, 70, 0.08)",
        "padding": "10px 12px",
        "height": "100%",
    }
    if style:
        base.update(style)
    return html.Div(children, style=base)


def download_button(button_id: str, download_id: str, label: str = "Descargar Excel"):
    return html.Div(
        [
            dbc.Button(
                label,
                id=button_id,
                n_clicks=0,
                size="sm",
                outline=True,
                color="primary",
            ),
            dcc.Download(id=download_id),
        ],
        style={
            "display": "flex",
            "justifyContent": "flex-end",
            "marginBottom": "6px",
        },
    )


def safe_records(df: pd.DataFrame | None):
    """Records JSON-safe para dcc.Store/DataTable."""
    if df is None or df.empty:
        return []

    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d")
        elif isinstance(out[c].dtype, pd.CategoricalDtype):
            out[c] = out[c].astype(str)

    out = out.replace([np.inf, -np.inf], np.nan)
    out = out.astype(object).where(pd.notna(out), None)
    return out.to_dict("records")


def empty_fig(title: str = "Sin datos"):
    fig = go.Figure()
    fig.update_layout(
        title=title,
        template="simple_white",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=12, color=BBVA_GREY),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text="No hay datos para la selección actual",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=13, color=BBVA_GREY),
            )
        ],
        margin=dict(l=40, r=30, t=60, b=40),
    )
    return fig


def apply_layout(fig: go.Figure, title: str, y_title: str = "", x_title: str = ""):
    fig.update_layout(
        title=title,
        template="simple_white",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=12, color=BBVA_GREY),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        margin=dict(l=55, r=30, t=85, b=55),
        hovermode="closest",
    )
    fig.update_xaxes(
        title=x_title,
        showgrid=True,
        gridwidth=1,
        gridcolor="#E9ECEF",
        zeroline=False,
    )
    fig.update_yaxes(
        title=y_title,
        showgrid=True,
        gridwidth=1,
        gridcolor="#E9ECEF",
        zeroline=False,
    )
    fig.add_annotation(
        x=0,
        y=-0.16,
        xref="paper",
        yref="paper",
        text="Source: BBVA Global Markets Strategy",
        showarrow=False,
        xanchor="left",
        font=dict(size=10, color="#A2A0A0"),
    )
    return fig
