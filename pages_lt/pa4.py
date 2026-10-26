# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from data import df_base
from pages_lt.ui_utils import (
    BBVA_BLUE,
    download_button,
    page_title,
    card,
    safe_records,
)
from pages_lt.net_purchases_utils import (
    FLOW_MAP,
    prepare_base,
    participants,
    bonds,
    by_instrument,
    monthly_flow,
    annual_flow,
    cumulative_flow,
    flow_bar_fig,
    cumulative_fig,
)

MARKET = "UDIBONOS"
MARKET_LABEL = "Udibono"
PREFIX = "npudi"
PAGE_NAME = "Udibono | Net purchases"

dash.register_page(__name__, path="/udibono-net-purchases", name=PAGE_NAME, order=4)

_df = prepare_base(df_base)
_min_date = _df["Día"].min()
_max_date = _df["Día"].max()
_years = sorted(_df["Día"].dropna().dt.year.unique().tolist())
_min_year = min(_years) if _years else 2010
_max_year = max(_years) if _years else pd.Timestamp.today().year
_participants = participants(_df, MARKET)
_bonds = bonds(_df, MARKET)
_default_participant = "Res. Exterior" if "Res. Exterior" in _participants else (_participants[0] if _participants else None)


def _footnote(text, equation=None):
    items = [
        html.Span("Nota: ", style={"fontWeight": "bold", "color": BBVA_BLUE}),
        html.Span(text),
    ]
    if equation:
        items += [
            html.Br(),
            html.Span("Ecuación: ", style={"fontWeight": "bold", "color": BBVA_BLUE}),
            html.Code(
                equation,
                style={
                    "fontSize": "11px",
                    "backgroundColor": "#F4F6F8",
                    "padding": "2px 5px",
                    "borderRadius": "4px",
                },
            ),
        ]
    return html.Div(
        items,
        style={
            "fontSize": "11px",
            "color": "#46536D",
            "lineHeight": "1.45",
            "borderTop": "1px solid #E2E6EA",
            "paddingTop": "8px",
            "marginTop": "4px",
        },
    )


def _graph_card(btn_id, dl_id, graph_id, note, eq):
    return card(
        [
            download_button(btn_id, dl_id),
            dcc.Loading(type="circle", color=BBVA_BLUE, children=dcc.Graph(id=graph_id)),
            _footnote(note, eq),
        ]
    )


layout = html.Div(
    [
        page_title(
            f"Net Purchases | {MARKET_LABEL}",
            "Compras netas por emisión y evolución temporal en USD y DV01, con análisis diario, mensual, anual y acumulado.",
        ),

        html.H4("Net purchases by instrument", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Periodo"),
                        dcc.DatePickerRange(
                            id=f"{PREFIX}-daily-dates",
                            min_date_allowed=_min_date,
                            max_date_allowed=_max_date,
                            start_date=_max_date - pd.Timedelta(days=30),
                            end_date=_max_date,
                            display_format="YYYY-MM-DD",
                        ),
                    ],
                    width=5,
                ),
                dbc.Col(
                    [
                        html.Label("Participante"),
                        dcc.Dropdown(
                            id=f"{PREFIX}-daily-participant",
                            options=[{"label": x, "value": x} for x in _participants],
                            value=_default_participant,
                            clearable=False,
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        html.Label(" "),
                        dbc.Button(
                            "Cargar / actualizar análisis",
                            id=f"{PREFIX}-run",
                            color="primary",
                            n_clicks=0,
                            style={"width": "100%"},
                        ),
                    ],
                    width=3,
                ),
            ],
            style={"marginBottom": "12px"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-inst-usd-btn",
                        f"{PREFIX}-dl-inst-usd",
                        f"{PREFIX}-inst-usd",
                        "Suma de compras netas del participante seleccionado por emisión durante el periodo. Positivo/negativo conserva la convención de signo de Base_M.",
                        "Net Purchases(bond) = Σ Daily Net Purchases(bond)",
                    ),
                    width=6,
                ),
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-inst-dv01-btn",
                        f"{PREFIX}-dl-inst-dv01",
                        f"{PREFIX}-inst-dv01",
                        "Mismo flujo neto expresado en DV01 para comparar riesgo de tasa entre emisiones con distinta duración.",
                        "Net Purchases DV01(bond) = Σ Net Purchases DV01(daily)",
                    ),
                    width=6,
                ),
            ],
            style={"marginBottom": "18px"},
        ),

        html.H4("Monthly Net Purchases", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Periodo"),
                        dcc.DatePickerRange(
                            id=f"{PREFIX}-monthly-dates",
                            min_date_allowed=_min_date,
                            max_date_allowed=_max_date,
                            start_date=_max_date - pd.DateOffset(months=12),
                            end_date=_max_date,
                            display_format="YYYY-MM-DD",
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        html.Label("Participante"),
                        dcc.Dropdown(
                            id=f"{PREFIX}-monthly-participant",
                            options=[{"label": x, "value": x} for x in _participants],
                            value=_default_participant,
                            clearable=False,
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        html.Label("Bono"),
                        dcc.Dropdown(
                            id=f"{PREFIX}-monthly-bond",
                            options=[{"label": x, "value": x} for x in _bonds],
                            value="Total",
                            clearable=False,
                        ),
                    ],
                    width=4,
                ),
            ],
            style={"marginBottom": "10px"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-mon-usd-btn",
                        f"{PREFIX}-dl-mon-usd",
                        f"{PREFIX}-mon-usd",
                        "Agregación mensual de compras netas para el bono seleccionado. 'Total' suma todas las emisiones del mercado elegido.",
                        "Monthly Flow(m) = Σ Net Purchases(d), d ∈ month m",
                    ),
                    width=6,
                ),
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-mon-dv01-btn",
                        f"{PREFIX}-dl-mon-dv01",
                        f"{PREFIX}-mon-dv01",
                        "Agregación mensual del flujo expresado en DV01 para normalizar la exposición de duración.",
                        "Monthly DV01(m) = Σ Net Purchases DV01(d), d ∈ month m",
                    ),
                    width=6,
                ),
            ],
            style={"marginBottom": "18px"},
        ),

        html.H4("Annual Net Purchases", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Rango de años"),
                        dcc.RangeSlider(
                            id=f"{PREFIX}-years",
                            min=_min_year,
                            max=_max_year,
                            step=1,
                            value=[max(_min_year, _max_year - 5), _max_year],
                            marks={str(y): str(y) for y in _years},
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ],
                    width=5,
                ),
                dbc.Col(
                    [
                        html.Label("Participante"),
                        dcc.Dropdown(
                            id=f"{PREFIX}-annual-participant",
                            options=[{"label": x, "value": x} for x in _participants],
                            value=_default_participant,
                            clearable=False,
                        ),
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        html.Label("Bono"),
                        dcc.Dropdown(
                            id=f"{PREFIX}-annual-bond",
                            options=[{"label": x, "value": x} for x in _bonds],
                            value="Total",
                            clearable=False,
                        ),
                    ],
                    width=4,
                ),
            ],
            style={"marginBottom": "10px"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-ann-usd-btn",
                        f"{PREFIX}-dl-ann-usd",
                        f"{PREFIX}-ann-usd",
                        "Suma anual de compras netas. Permite identificar cambios persistentes de posicionamiento por participante.",
                        "Annual Flow(y) = Σ Net Purchases(d), year(d)=y",
                    ),
                    width=6,
                ),
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-ann-dv01-btn",
                        f"{PREFIX}-dl-ann-dv01",
                        f"{PREFIX}-ann-dv01",
                        "Suma anual expresada en DV01 para comparar años y emisiones en unidades de riesgo de tasa.",
                        "Annual DV01(y) = Σ Net Purchases DV01(d), year(d)=y",
                    ),
                    width=6,
                ),
            ],
            style={"marginBottom": "18px"},
        ),

        html.H4("Cumulative Net Purchases", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-cum-usd-btn",
                        f"{PREFIX}-dl-cum-usd",
                        f"{PREFIX}-cum-usd",
                        "Acumulado de compras netas desde el inicio del periodo mensual seleccionado. Ayuda a distinguir una tendencia persistente de movimientos aislados.",
                        "Cumulative Flow(t) = Σ Net Purchases(i), i≤t",
                    ),
                    width=6,
                ),
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-cum-dv01-btn",
                        f"{PREFIX}-dl-cum-dv01",
                        f"{PREFIX}-cum-dv01",
                        "Acumulado del flujo en DV01 para observar la trayectoria de exposición de riesgo de tasa del participante.",
                        "Cumulative DV01(t) = Σ Net Purchases DV01(i), i≤t",
                    ),
                    width=6,
                ),
            ]
        ),

        dcc.Store(id=f"{PREFIX}-store-inst-usd"),
        dcc.Store(id=f"{PREFIX}-store-inst-dv01"),
        dcc.Store(id=f"{PREFIX}-store-mon-usd"),
        dcc.Store(id=f"{PREFIX}-store-mon-dv01"),
        dcc.Store(id=f"{PREFIX}-store-ann-usd"),
        dcc.Store(id=f"{PREFIX}-store-ann-dv01"),
        dcc.Store(id=f"{PREFIX}-store-cum-usd"),
        dcc.Store(id=f"{PREFIX}-store-cum-dv01"),
    ],
    style={"fontFamily": "Arial", "backgroundColor": "white"},
)


@callback(
    Output(f"{PREFIX}-inst-usd", "figure"),
    Output(f"{PREFIX}-inst-dv01", "figure"),
    Output(f"{PREFIX}-mon-usd", "figure"),
    Output(f"{PREFIX}-mon-dv01", "figure"),
    Output(f"{PREFIX}-ann-usd", "figure"),
    Output(f"{PREFIX}-ann-dv01", "figure"),
    Output(f"{PREFIX}-cum-usd", "figure"),
    Output(f"{PREFIX}-cum-dv01", "figure"),
    Output(f"{PREFIX}-store-inst-usd", "data"),
    Output(f"{PREFIX}-store-inst-dv01", "data"),
    Output(f"{PREFIX}-store-mon-usd", "data"),
    Output(f"{PREFIX}-store-mon-dv01", "data"),
    Output(f"{PREFIX}-store-ann-usd", "data"),
    Output(f"{PREFIX}-store-ann-dv01", "data"),
    Output(f"{PREFIX}-store-cum-usd", "data"),
    Output(f"{PREFIX}-store-cum-dv01", "data"),
    Input(f"{PREFIX}-run", "n_clicks"),
    State(f"{PREFIX}-daily-participant", "value"),
    State(f"{PREFIX}-daily-dates", "start_date"),
    State(f"{PREFIX}-daily-dates", "end_date"),
    State(f"{PREFIX}-monthly-participant", "value"),
    State(f"{PREFIX}-monthly-bond", "value"),
    State(f"{PREFIX}-monthly-dates", "start_date"),
    State(f"{PREFIX}-monthly-dates", "end_date"),
    State(f"{PREFIX}-annual-participant", "value"),
    State(f"{PREFIX}-annual-bond", "value"),
    State(f"{PREFIX}-years", "value"),
    prevent_initial_call=True,
)
def update_page(
    n_clicks,
    daily_participant,
    daily_start,
    daily_end,
    monthly_participant,
    monthly_bond,
    monthly_start,
    monthly_end,
    annual_participant,
    annual_bond,
    years,
):
    if not n_clicks:
        raise PreventUpdate

    inst_usd = by_instrument(_df, MARKET, daily_participant, daily_start, daily_end, "USD")
    inst_dv01 = by_instrument(_df, MARKET, daily_participant, daily_start, daily_end, "DV01")

    mon_usd = monthly_flow(_df, MARKET, monthly_participant, monthly_bond, monthly_start, monthly_end, "USD")
    mon_dv01 = monthly_flow(_df, MARKET, monthly_participant, monthly_bond, monthly_start, monthly_end, "DV01")

    start_year, end_year = years or [_max_year - 5, _max_year]
    ann_usd = annual_flow(_df, MARKET, annual_participant, annual_bond, start_year, end_year, "USD")
    ann_dv01 = annual_flow(_df, MARKET, annual_participant, annual_bond, start_year, end_year, "DV01")

    cum_usd = cumulative_flow(_df, MARKET, monthly_participant, monthly_bond, monthly_start, monthly_end, "USD")
    cum_dv01 = cumulative_flow(_df, MARKET, monthly_participant, monthly_bond, monthly_start, monthly_end, "DV01")

    return (
        flow_bar_fig(inst_usd, f"{MARKET_LABEL} | Net purchases by instrument | {daily_participant}", FLOW_MAP["USD"][1]),
        flow_bar_fig(inst_dv01, f"{MARKET_LABEL} | Net purchases DV01 by instrument | {daily_participant}", FLOW_MAP["DV01"][1]),
        flow_bar_fig(mon_usd, f"{MARKET_LABEL} | Monthly Net Purchases | {monthly_participant} | {monthly_bond}", FLOW_MAP["USD"][1]),
        flow_bar_fig(mon_dv01, f"{MARKET_LABEL} | Monthly Net Purchases DV01 | {monthly_participant} | {monthly_bond}", FLOW_MAP["DV01"][1]),
        flow_bar_fig(ann_usd, f"{MARKET_LABEL} | Annual Net Purchases | {annual_participant} | {annual_bond}", FLOW_MAP["USD"][1]),
        flow_bar_fig(ann_dv01, f"{MARKET_LABEL} | Annual Net Purchases DV01 | {annual_participant} | {annual_bond}", FLOW_MAP["DV01"][1]),
        cumulative_fig(cum_usd, f"{MARKET_LABEL} | Cumulative Net Purchases | {monthly_participant} | {monthly_bond}", FLOW_MAP["USD"][1]),
        cumulative_fig(cum_dv01, f"{MARKET_LABEL} | Cumulative Net Purchases DV01 | {monthly_participant} | {monthly_bond}", FLOW_MAP["DV01"][1]),
        safe_records(inst_usd),
        safe_records(inst_dv01),
        safe_records(mon_usd),
        safe_records(mon_dv01),
        safe_records(ann_usd),
        safe_records(ann_dv01),
        safe_records(cum_usd),
        safe_records(cum_dv01),
    )


def _send(records, filename):
    df = pd.DataFrame(records or [])
    return dcc.send_data_frame(df.to_excel, filename, index=False, sheet_name="Datos")


def _register_download(output_id, button_id, store_id, filename):
    @callback(
        Output(output_id, "data"),
        Input(button_id, "n_clicks"),
        State(store_id, "data"),
        prevent_initial_call=True,
    )
    def _download(n, data):
        return _send(data, filename)


_register_download(f"{PREFIX}-dl-inst-usd", f"{PREFIX}-dl-inst-usd-btn", f"{PREFIX}-store-inst-usd", f"{PREFIX}_net_purchases_by_instrument_usd.xlsx")
_register_download(f"{PREFIX}-dl-inst-dv01", f"{PREFIX}-dl-inst-dv01-btn", f"{PREFIX}-store-inst-dv01", f"{PREFIX}_net_purchases_by_instrument_dv01.xlsx")
_register_download(f"{PREFIX}-dl-mon-usd", f"{PREFIX}-dl-mon-usd-btn", f"{PREFIX}-store-mon-usd", f"{PREFIX}_monthly_net_purchases_usd.xlsx")
_register_download(f"{PREFIX}-dl-mon-dv01", f"{PREFIX}-dl-mon-dv01-btn", f"{PREFIX}-store-mon-dv01", f"{PREFIX}_monthly_net_purchases_dv01.xlsx")
_register_download(f"{PREFIX}-dl-ann-usd", f"{PREFIX}-dl-ann-usd-btn", f"{PREFIX}-store-ann-usd", f"{PREFIX}_annual_net_purchases_usd.xlsx")
_register_download(f"{PREFIX}-dl-ann-dv01", f"{PREFIX}-dl-ann-dv01-btn", f"{PREFIX}-store-ann-dv01", f"{PREFIX}_annual_net_purchases_dv01.xlsx")
_register_download(f"{PREFIX}-dl-cum-usd", f"{PREFIX}-dl-cum-usd-btn", f"{PREFIX}-store-cum-usd", f"{PREFIX}_cumulative_net_purchases_usd.xlsx")
_register_download(f"{PREFIX}-dl-cum-dv01", f"{PREFIX}-dl-cum-dv01-btn", f"{PREFIX}-store-cum-dv01", f"{PREFIX}_cumulative_net_purchases_dv01.xlsx")
