# -*- coding: utf-8 -*-
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import os

import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from pages_lt.ui_utils import BBVA_BLUE, BBVA_GREY, card, download_button, page_title, safe_records
from pages_lt.iif_flows_utils import (
    FLOW_TYPES,
    REGIONS,
    annual_cumulative_profile,
    country_list,
    country_monthly,
    fig_cumulative_profile,
    fig_regional_monthly,
    fig_total_decomposition,
    fig_total_tracker,
    load_iif_workbook,
    regional_series,
)


dash.register_page(
    __name__,
    path="/iif-flows",
    name="IIF Flows",
    order=9999,
)

# =============================================================================
# IIF DATABASE
# =============================================================================

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DATA_DIR = Path(os.getenv("IIF_DATA_DIR", os.getenv("DASHBOARD_DATA_DIR", str(_PROJECT_ROOT / "data_files")))).expanduser()
_IIF_PATH = Path(os.getenv("IIF_WORKBOOK_PATH", str(_DATA_DIR / "monthly_em_portfolio_flows_database.xlsx"))).expanduser()

_IIF_LOAD_ERROR = None

try:
    if not _IIF_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo IIF en:\n{_IIF_PATH}"
        )

    _IIF = load_iif_workbook(_IIF_PATH)

except Exception as exc:
    _IIF_LOAD_ERROR = str(exc)

    _IIF = {
        "total": pd.DataFrame(),
        "regional": pd.DataFrame(),
        "country": pd.DataFrame(),
    }

_TOTAL = _IIF["total"]
_REGIONAL = _IIF["regional"]
_COUNTRY = _IIF["country"]
_COUNTRIES = country_list(_COUNTRY) if not _COUNTRY.empty else ["EM Aggregate", "Mexico"]
_DEFAULT_COUNTRY = "Mexico" if "Mexico" in _COUNTRIES else _COUNTRIES[0]


def _note(text: str):
    return html.Div(
        [html.Span("Methodology: ", style={"fontWeight": "bold", "color": BBVA_BLUE}), html.Span(text)],
        style={
            "fontSize": "11px", "color": BBVA_GREY, "borderTop": "1px solid #E2E6EA",
            "paddingTop": "8px", "marginTop": "4px", "lineHeight": "1.45",
        },
    )


def _graph_card(btn_id, dl_id, graph_id, note):
    return card(
        [
            download_button(btn_id, dl_id, label="Download Excel"),
            dcc.Loading(type="circle", color=BBVA_BLUE, children=dcc.Graph(id=graph_id)),
            _note(note),
        ],
        style={"height": "auto"},
    )


def _empty(title: str):
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.update_layout(
        title=title, template="simple_white", paper_bgcolor="white", plot_bgcolor="white",
        annotations=[dict(text="No data available", x=.5, y=.5, xref="paper", yref="paper", showarrow=False)],
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


layout = html.Div(
    [
        page_title(
            "IIF Flows",
            "Emerging-market portfolio-flow tracker, country cumulative profiles and regional flows from the IIF monthly database.",
        ),
        dbc.Alert(_IIF_LOAD_ERROR, color="danger") if _IIF_LOAD_ERROR else None,

        html.H4("Headline EM tracker", style={"color": BBVA_BLUE, "fontWeight": "bold", "marginTop": "8px"}),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Tracker history"),
                        dcc.Dropdown(
                            id="iif-tracker-months", value=30, clearable=False,
                            options=[{"label": f"{x} months", "value": x} for x in [24, 30, 36, 60]],
                        ),
                    ],
                    lg=2, md=4,
                ),
            ],
            class_name="g-3", style={"marginBottom": "12px"},
        ),
        dbc.Row(
            [
                dbc.Col(_graph_card(
                    "iif-dl-tracker1-btn", "iif-dl-tracker1", "iif-tracker1",
                    "IIF headline tracker. Equity and debt are shown as monthly contributions; the black line is total portfolio flows. Units: USD bn.",
                ), lg=6, md=12),
                dbc.Col(_graph_card(
                    "iif-dl-tracker2-btn", "iif-dl-tracker2", "iif-tracker2",
                    "Decomposition of total EM flows into China and EM ex-China equity/debt components. Units: USD bn.",
                ), lg=6, md=12),
            ],
            class_name="g-3", style={"marginBottom": "18px"},
        ),

        html.H4("Country flows", style={"color": BBVA_BLUE, "fontWeight": "bold"}),
        dbc.Row(
            [
                dbc.Col(
                    [html.Label("Country / aggregate"), dcc.Dropdown(
                        id="iif-country", value=_DEFAULT_COUNTRY, clearable=False,
                        options=[{"label": x, "value": x} for x in _COUNTRIES],
                    )], lg=4, md=6),
                dbc.Col(
                    [html.Label("Years shown"), dcc.Dropdown(
                        id="iif-display-years", value=4, clearable=False,
                        options=[{"label": str(x), "value": x} for x in [3, 4, 5, 6]],
                    )], lg=2, md=3),
                dbc.Col(
                    [html.Label("Average"), dcc.Dropdown(
                        id="iif-average-years", value=5, clearable=False,
                        options=[{"label": f"{x}Y", "value": x} for x in [3, 5, 7, 10]],
                    )], lg=2, md=3),
            ], class_name="g-3", style={"marginBottom": "12px"},
        ),
        dbc.Row(
            [
                dbc.Col(_graph_card(
                    "iif-dl-country-total-btn", "iif-dl-country-total", "iif-country-total",
                    "Country-level IIF data are reported in USD mn and converted here to USD bn. Total = Equity + Debt when both series exist; Portfolio-only countries use the Portfolio series.",
                ), lg=4, md=12),
                dbc.Col(_graph_card(
                    "iif-dl-country-equity-btn", "iif-dl-country-equity", "iif-country-equity",
                    "Jan-Dec cumulative equity-flow profile. Missing future/current observations are not replaced with zero.",
                ), lg=4, md=12),
                dbc.Col(_graph_card(
                    "iif-dl-country-debt-btn", "iif-dl-country-debt", "iif-country-debt",
                    "Jan-Dec cumulative debt-flow profile. Missing future/current observations are not replaced with zero.",
                ), lg=4, md=12),
            ], class_name="g-3", style={"marginBottom": "18px"},
        ),
        html.Div(
            [
                html.Strong("Important: ", style={"color": BBVA_BLUE}),
                html.Span(
                    "EM Aggregate on this page is the sum of country-level series from Country Flows. "
                    "It is not the same construct as the model-driven IIF headline Total Portfolio Flows Tracker, "
                    "so the two series should not be expected to reconcile exactly."
                ),
            ],
            style={"fontSize": "11px", "color": BBVA_GREY, "marginBottom": "18px"},
        ),

        html.H4("Regional flows", style={"color": BBVA_BLUE, "fontWeight": "bold"}),
        dbc.Row(
            [
                dbc.Col([html.Label("Flow type"), dcc.Dropdown(
                    id="iif-region-flow-type", value="Total", clearable=False,
                    options=[{"label": x, "value": x} for x in FLOW_TYPES],
                )], lg=2, md=4),
                dbc.Col([html.Label("Region"), dcc.Dropdown(
                    id="iif-region", value="Latin America", clearable=False,
                    options=[{"label": x, "value": x} for x in REGIONS + ["Total"]],
                )], lg=3, md=5),
                dbc.Col([html.Label("Monthly history"), dcc.Dropdown(
                    id="iif-region-months", value=36, clearable=False,
                    options=[{"label": f"{x} months", "value": x} for x in [24, 36, 60, 120]],
                )], lg=2, md=3),
            ], class_name="g-3", style={"marginBottom": "12px"},
        ),
        dbc.Row(
            [
                dbc.Col(_graph_card(
                    "iif-dl-region-monthly-btn", "iif-dl-region-monthly", "iif-region-monthly",
                    "Regional monthly IIF flows. Bars show the four EM regions and the black line is the reported regional total for the selected flow type.",
                ), lg=7, md=12),
                dbc.Col(_graph_card(
                    "iif-dl-region-profile-btn", "iif-dl-region-profile", "iif-region-profile",
                    "Jan-Dec cumulative profile for the selected region and flow type, using the same year/average convention as the country section.",
                ), lg=5, md=12),
            ], class_name="g-3",
        ),

        dcc.Store(id="iif-store-tracker"),
        dcc.Store(id="iif-store-country"),
        dcc.Store(id="iif-store-regional"),
    ],
    style={"paddingBottom": "30px"},
)


@callback(
    Output("iif-tracker1", "figure"),
    Output("iif-tracker2", "figure"),
    Output("iif-store-tracker", "data"),
    Input("iif-tracker-months", "value"),
)
def _update_trackers(months):
    if _TOTAL.empty:
        return _empty("IIF tracker"), _empty("IIF decomposition"), []
    months = int(months or 30)
    q = _TOTAL.sort_values("Date").tail(months).copy()
    return fig_total_tracker(_TOTAL, months), fig_total_decomposition(_TOTAL, months), safe_records(q)


@callback(
    Output("iif-country-total", "figure"),
    Output("iif-country-equity", "figure"),
    Output("iif-country-debt", "figure"),
    Output("iif-store-country", "data"),
    Input("iif-country", "value"),
    Input("iif-display-years", "value"),
    Input("iif-average-years", "value"),
)
def _update_country(country, display_years, average_years):
    if _COUNTRY.empty:
        e = _empty("Country flows")
        return e, e, e, []
    country = country or _DEFAULT_COUNTRY
    display_years = int(display_years or 4)
    average_years = int(average_years or 5)
    monthly = country_monthly(_COUNTRY, country)
    figs = []
    for metric in ["Total", "Equity", "Debt"]:
        profile = annual_cumulative_profile(monthly, metric, display_years, average_years)
        figs.append(fig_cumulative_profile(
            profile,
            f"{country} | {metric} portfolio flows | Cumulative Jan-Dec [USD bn]",
            average_years,
        ))
    return figs[0], figs[1], figs[2], safe_records(monthly)


@callback(
    Output("iif-region-monthly", "figure"),
    Output("iif-region-profile", "figure"),
    Output("iif-store-regional", "data"),
    Input("iif-region-flow-type", "value"),
    Input("iif-region", "value"),
    Input("iif-region-months", "value"),
    Input("iif-display-years", "value"),
    Input("iif-average-years", "value"),
)
def _update_regional(flow_type, region, months, display_years, average_years):
    if _REGIONAL.empty:
        e = _empty("Regional flows")
        return e, e, []
    flow_type = flow_type or "Total"
    region = region or "Latin America"
    months = int(months or 36)
    display_years = int(display_years or 4)
    average_years = int(average_years or 5)
    monthly_fig = fig_regional_monthly(_REGIONAL, flow_type, months)
    series = regional_series(_REGIONAL, flow_type, region)
    profile = annual_cumulative_profile(series, flow_type, display_years, average_years)
    profile_fig = fig_cumulative_profile(
        profile, f"{region} | {flow_type} portfolio flows | Cumulative Jan-Dec [USD bn]", average_years
    )
    q = _REGIONAL[_REGIONAL["Flow Type"] == flow_type].copy()
    return monthly_fig, profile_fig, safe_records(q)


def _records_to_df(records):
    q = pd.DataFrame(records or [])
    for c in q.columns:
        if "Date" in c:
            q[c] = pd.to_datetime(q[c], errors="coerce")
    return q


def _send_xlsx(sheets: dict[str, pd.DataFrame], filename: str):
    def writer(buf):
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            for name, df in sheets.items():
                df.to_excel(xw, sheet_name=name[:31], index=False)
    return dcc.send_bytes(writer, filename)


@callback(
    Output("iif-dl-tracker1", "data"),
    Input("iif-dl-tracker1-btn", "n_clicks"), State("iif-store-tracker", "data"), prevent_initial_call=True,
)
def _dl_tracker1(n, records):
    q = _records_to_df(records)
    return _send_xlsx({"Tracker": q[[c for c in ["Date", "Total", "Equity", "Debt"] if c in q]]}, "IIF_Total_Flows_Tracker.xlsx")


@callback(
    Output("iif-dl-tracker2", "data"),
    Input("iif-dl-tracker2-btn", "n_clicks"), State("iif-store-tracker", "data"), prevent_initial_call=True,
)
def _dl_tracker2(n, records):
    q = _records_to_df(records)
    cols = ["Date", "Total", "China Equity", "EM ex-China Equity", "China Debt", "EM ex-China Debt"]
    return _send_xlsx({"Decomposition": q[[c for c in cols if c in q]]}, "IIF_Total_Flows_Decomposition.xlsx")


for _metric, _btn, _dl in [
    ("Total", "iif-dl-country-total-btn", "iif-dl-country-total"),
    ("Equity", "iif-dl-country-equity-btn", "iif-dl-country-equity"),
    ("Debt", "iif-dl-country-debt-btn", "iif-dl-country-debt"),
]:
    @callback(Output(_dl, "data"), Input(_btn, "n_clicks"), State("iif-store-country", "data"), prevent_initial_call=True)
    def _dl_country(n, records, metric=_metric):
        q = _records_to_df(records)
        return _send_xlsx({metric: q[[c for c in ["Date", metric] if c in q]]}, f"IIF_Country_{metric}_Flows.xlsx")


@callback(
    Output("iif-dl-region-monthly", "data"), Input("iif-dl-region-monthly-btn", "n_clicks"),
    State("iif-store-regional", "data"), prevent_initial_call=True,
)
def _dl_region_monthly(n, records):
    return _send_xlsx({"Regional Flows": _records_to_df(records)}, "IIF_Regional_Flows.xlsx")


@callback(
    Output("iif-dl-region-profile", "data"), Input("iif-dl-region-profile-btn", "n_clicks"),
    State("iif-store-regional", "data"), State("iif-region-flow-type", "value"), State("iif-region", "value"),
    prevent_initial_call=True,
)
def _dl_region_profile(n, records, flow_type, region):
    q = _records_to_df(records)
    q = q[(q.get("Flow Type") == flow_type) & (q.get("Region") == region)] if not q.empty else q
    return _send_xlsx({"Regional Profile": q}, "IIF_Regional_Profile.xlsx")
