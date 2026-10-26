# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html

from data import df_base
from pages_lt.ui_utils import BBVA_BLUE, BBVA_GREY, card, download_button, page_title, safe_records
from pages_lt.flow_comparison_utils import (
    COMPARISON_INSTRUMENTS,
    COMPARISON_PARTICIPANTS,
    comparison_date_bounds,
    comparison_frame,
    comparison_stats,
    monthly_comparison_fig,
    cumulative_comparison_fig,
)


dash.register_page(
    __name__,
    path="/flow-comparison",
    name="Net purchases vs. Flows comparative",
    order=999,
)

_MIN_DATE, _MAX_DATE = comparison_date_bounds(df_base)
_DEFAULT_START = max(_MIN_DATE, _MAX_DATE - pd.DateOffset(years=5))


def _footnote(text, equation=None):
    ch = [
        html.Span("Nota: ", style={"fontWeight": "bold", "color": BBVA_BLUE}),
        html.Span(text),
    ]
    if equation:
        ch += [
            html.Br(),
            html.Span("Ecuación: ", style={"fontWeight": "bold", "color": BBVA_BLUE}),
            html.Code(
                equation,
                style={"fontSize": "11px", "backgroundColor": "#F4F6F8", "padding": "2px 5px"},
            ),
        ]
    return html.Div(
        ch,
        style={
            "fontSize": "11px", "color": BBVA_GREY,
            "borderTop": "1px solid #E2E6EA", "paddingTop": "8px", "marginTop": "4px",
        },
    )


def _graph_card(btn_id, dl_id, graph_id, note, equation):
    return card([
        download_button(btn_id, dl_id),
        dcc.Loading(type="circle", color=BBVA_BLUE, children=dcc.Graph(id=graph_id)),
        _footnote(note, equation),
    ], style={"height": "auto"})


def _kpi(title, value_id, suffix="USD bn"):
    return html.Div([
        html.Div(title, style={"fontSize": "12px", "color": BBVA_GREY}),
        html.Div(
            id=value_id, children="-",
            style={"fontSize": "23px", "fontWeight": "bold", "color": BBVA_BLUE, "marginTop": "3px"},
        ),
        html.Div(suffix, style={"fontSize": "10px", "color": BBVA_GREY}),
    ], style={
        "backgroundColor": "white", "border": "1px solid #E2E6EA", "borderRadius": "10px",
        "padding": "12px 14px", "boxShadow": "0 1px 4px rgba(7,14,70,0.08)", "height": "100%",
    })


layout = html.Div([
    page_title(
        "Comparación: cambio de tenencias vs Net Purchases",
        "Contrasta los flujos inferidos por cambios mensuales en tenencias con los Net Purchases de Base_M por tipo de inversionista.",
    ),

    dbc.Row([
        dbc.Col([
            html.Label("Periodo"),
            dcc.DatePickerRange(
                id="cmp-dates", min_date_allowed=_MIN_DATE, max_date_allowed=_MAX_DATE,
                start_date=_DEFAULT_START, end_date=_MAX_DATE, display_format="YYYY-MM-DD",
            ),
        ], width=4),
        dbc.Col([
            html.Label("Instrumento"),
            dcc.Dropdown(
                id="cmp-instrument", value="MBonos", clearable=False,
                options=[{"label": x, "value": x} for x in COMPARISON_INSTRUMENTS],
            ),
        ], width=4),
        dbc.Col([
            html.Label("Inversionista"),
            dcc.Dropdown(
                id="cmp-participant", value="Inversionistas extranjeros", clearable=False,
                options=[{"label": x, "value": x} for x in COMPARISON_PARTICIPANTS],
            ),
        ], width=4),
    ], style={"marginBottom": "14px"}),

    dbc.Row([
        dbc.Col(_kpi("Cambio de tenencia acumulado", "cmp-kpi-holdings"), width=3),
        dbc.Col(_kpi("Net Purchases acumulado", "cmp-kpi-netp"), width=3),
        dbc.Col(_kpi("Brecha acumulada", "cmp-kpi-gap"), width=3),
        dbc.Col(_kpi("Correlación mensual", "cmp-kpi-corr", suffix="coeficiente"), width=3),
    ], style={"marginBottom": "16px"}),

    dbc.Row([
        dbc.Col(_graph_card(
            "cmp-dl-monthly-btn", "cmp-dl-monthly", "cmp-monthly",
            "Compara mes a mes el flujo inferido por cambio de tenencias con los Net Purchases del mismo grupo. Interbancaria/Bancos quedan excluidos de esta comparación.",
            "Cambio tenencia_m = Delta Tenencias_m / FX promedio_m; Net Purchases_m = suma compras netas diarias / 1000",
        ), width=12),
    ], style={"marginBottom": "14px"}),

    dbc.Row([
        dbc.Col(_graph_card(
            "cmp-dl-cum-btn", "cmp-dl-cum", "cmp-cumulative",
            "Acumulado de ambas medidas desde el inicio del periodo seleccionado. Permite evaluar si ambas fuentes muestran una dirección y magnitud semejantes a lo largo del tiempo.",
            "Acumulado_t = suma Flujo_m, m <= t",
        ), width=12),
    ], style={"marginBottom": "14px"}),

    html.H4("Detalle mensual", style={"color": BBVA_BLUE, "fontWeight": "bold"}),
    card([
        download_button("cmp-dl-table-btn", "cmp-dl-table"),
        dash_table.DataTable(
            id="cmp-table", page_action="none", sort_action="native", filter_action="native",
            style_table={"overflowX": "auto", "maxHeight": "520px", "overflowY": "auto"},
            style_header={"backgroundColor": BBVA_BLUE, "color": "white", "fontWeight": "bold"},
            style_cell={
                "fontFamily": "Arial", "fontSize": "12px", "padding": "6px",
                "textAlign": "center", "minWidth": "135px",
            },
        ),
        _footnote(
            "Mapeo de categorías: Siefores ↔ Siefores; Fondos de inversión ↔ Soc Inversion; Otros inversionistas locales ↔ Otros Nac.; Inversionistas extranjeros ↔ Res. Exterior. 'Total' suma estas cuatro categorías y excluye Interbancaria/Bancos. 'Total comparable' incluye únicamente MBonos + Udibonos porque son los mercados presentes en Base_M.",
            "Total comparable = MBonos + Udibonos; Total inversionistas = Siefores + Fondos + Otros locales + Extranjeros",
        ),
    ], style={"height": "auto"}),

    dcc.Store(id="cmp-store-data"),
])


@callback(
    Output("cmp-monthly", "figure"),
    Output("cmp-cumulative", "figure"),
    Output("cmp-kpi-holdings", "children"),
    Output("cmp-kpi-netp", "children"),
    Output("cmp-kpi-gap", "children"),
    Output("cmp-kpi-corr", "children"),
    Output("cmp-table", "data"),
    Output("cmp-table", "columns"),
    Output("cmp-store-data", "data"),
    Input("cmp-dates", "start_date"),
    Input("cmp-dates", "end_date"),
    Input("cmp-instrument", "value"),
    Input("cmp-participant", "value"),
)
def update_comparison(start_date, end_date, instrument, participant):
    data = comparison_frame(df_base, instrument, participant, start_date, end_date).round(4)
    stats = comparison_stats(data)

    def fmt(v, digits=2):
        return f"{v:,.{digits}f}" if pd.notna(v) and np.isfinite(v) else "-"

    cols = []
    for c in data.columns:
        if c == "Fecha":
            cols.append({"name": c, "id": c, "type": "datetime"})
        else:
            cols.append({"name": c, "id": c, "type": "numeric", "format": {"specifier": ",.2f"}})

    return (
        monthly_comparison_fig(data, instrument, participant),
        cumulative_comparison_fig(data, instrument, participant),
        fmt(stats["holdings"]),
        fmt(stats["netp"]),
        fmt(stats["gap"]),
        fmt(stats["corr"], 2),
        safe_records(data),
        cols,
        safe_records(data),
    )


def _send(records, filename):
    return dcc.send_data_frame(pd.DataFrame(records or []).to_excel, filename, index=False, sheet_name="Datos")


@callback(Output("cmp-dl-monthly", "data"), Input("cmp-dl-monthly-btn", "n_clicks"), State("cmp-store-data", "data"), prevent_initial_call=True)
def dl_monthly(n, data):
    return _send(data, "comparacion_flujos_mensual.xlsx")


@callback(Output("cmp-dl-cum", "data"), Input("cmp-dl-cum-btn", "n_clicks"), State("cmp-store-data", "data"), prevent_initial_call=True)
def dl_cumulative(n, data):
    return _send(data, "comparacion_flujos_acumulado.xlsx")


@callback(Output("cmp-dl-table", "data"), Input("cmp-dl-table-btn", "n_clicks"), State("cmp-store-data", "data"), prevent_initial_call=True)
def dl_table(n, data):
    return _send(data, "comparacion_flujos_detalle.xlsx")
