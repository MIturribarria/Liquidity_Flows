# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from pages_lt.ui_utils import BBVA_BLUE, card, download_button, page_title, safe_records
from pages_lt.holdings_utils import (
    HOLDINGS_LOAD_ERROR,
    INSTRUMENTS,
    date_bounds,
    horizon_flows,
    horizon_flow_fig,
    flow_history,
    monthly_flow_history_fig,
    period_flow_summary,
    period_flow_summary_fig,
)


dash.register_page(
    __name__,
    path="/government-holdings-flows",
    name="Government Flows by Investor",
    order=6,
)

_MIN_DATE, _MAX_DATE = date_bounds()


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
                style={
                    "fontSize": "11px",
                    "backgroundColor": "#F4F6F8",
                    "padding": "2px 5px",
                },
            ),
        ]
    return html.Div(
        ch,
        style={
            "fontSize": "11px",
            "color": "#46536D",
            "borderTop": "1px solid #E2E6EA",
            "paddingTop": "8px",
        },
    )




def _kpi(title, value_id, subtitle):
    return html.Div(
        [
            html.Div(title, style={"fontSize": "12px", "color": "#46536D"}),
            html.Div(
                id=value_id,
                children="-",
                style={
                    "fontSize": "22px",
                    "fontWeight": "bold",
                    "color": BBVA_BLUE,
                    "marginTop": "3px",
                },
            ),
            html.Div(subtitle, style={"fontSize": "10px", "color": "#46536D"}),
        ],
        style={
            "backgroundColor": "white",
            "border": "1px solid #E2E6EA",
            "borderRadius": "10px",
            "padding": "10px 12px",
            "boxShadow": "0 1px 4px rgba(7,14,70,0.08)",
            "height": "100%",
        },
    )

def _graph_card(horizon):
    return card(
        [
            download_button(f"hflow-dl-{horizon}-btn", f"hflow-dl-{horizon}"),
            dcc.Loading(
                type="circle",
                color=BBVA_BLUE,
                children=dcc.Graph(id=f"hflow-{horizon}"),
            ),
            _footnote(
                f"Cambio acumulado durante los últimos {horizon} mes(es) hasta la fecha de corte. "
                "Los cambios mensuales se convierten a USD con el USDMXN promedio de cada mes.",
                "Flujo_m = (Tenencias_m - Tenencias_m-1) / Promedio(USDMXN_m) / 1000; "
                "Flujo_N = suma Flujo_m",
            ),
        ],
        style={"height": "auto"},
    )


layout = html.Div(
    [
        page_title(
            "Flujos de Valores Gubernamentales",
            "Flujos por participante a 1, 3, 6 y 12 meses, más evolución mensual y suma acumulada para un periodo elegido.",
        ),
        dbc.Alert(HOLDINGS_LOAD_ERROR, color="danger") if HOLDINGS_LOAD_ERROR else None,
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Fecha de corte"),
                        dcc.DatePickerSingle(
                            id="hflow-asof",
                            min_date_allowed=_MIN_DATE,
                            max_date_allowed=_MAX_DATE,
                            date=_MAX_DATE,
                            display_format="YYYY-MM-DD",
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        html.Label("Instrumento"),
                        dcc.Dropdown(
                            id="hflow-instrument",
                            value="Total",
                            clearable=False,
                            options=[{"label": x, "value": x} for x in INSTRUMENTS],
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        html.Label("Nivel de desglose"),
                        dcc.Dropdown(
                            id="hflow-breakdown",
                            value="detail",
                            clearable=False,
                            options=[
                                {"label": "Detalle completo", "value": "detail"},
                                {"label": "5 grupos del reporte", "value": "summary"},
                            ],
                        ),
                    ],
                    width=4,
                ),
            ],
            style={"marginBottom": "14px"},
        ),
        dbc.Row(
            [dbc.Col(_graph_card(1), width=6), dbc.Col(_graph_card(3), width=6)],
            style={"marginBottom": "14px"},
        ),
        dbc.Row(
            [dbc.Col(_graph_card(6), width=6), dbc.Col(_graph_card(12), width=6)],
            style={"marginBottom": "18px"},
        ),

        html.H4("Evolución histórica de flujos", style={"color": BBVA_BLUE, "fontWeight": "bold"}),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Periodo histórico"),
                        dcc.DatePickerRange(
                            id="hflow-history-dates",
                            min_date_allowed=_MIN_DATE,
                            max_date_allowed=_MAX_DATE,
                            start_date=max(_MIN_DATE, _MAX_DATE - pd.DateOffset(years=3)),
                            end_date=_MAX_DATE,
                            display_format="YYYY-MM-DD",
                        ),
                    ],
                    width=12,
                ),
            ],
            style={"marginBottom": "10px"},
        ),

        dbc.Row(
            [
                dbc.Col(_kpi("Flujo neto del periodo", "hflow-kpi-net", "suma de participantes | USD bn"), width=4),
                dbc.Col(_kpi("Mayor comprador", "hflow-kpi-buyer", "participante y flujo acumulado"), width=4),
                dbc.Col(_kpi("Mayor vendedor", "hflow-kpi-seller", "participante y flujo acumulado"), width=4),
            ],
            class_name="g-3",
            style={"marginBottom": "12px"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    card(
                        [
                            download_button("hflow-dl-history-btn", "hflow-dl-history"),
                            dcc.Loading(type="circle", color=BBVA_BLUE, children=dcc.Graph(id="hflow-history")),
                            _footnote(
                                "Barras mensuales que muestran la contribución de cada tipo de inversionista al flujo del instrumento seleccionado entre las fechas elegidas. Los flujos positivos y negativos se apilan por separado alrededor de cero.",
                                "Flujo_m = (Tenencias_m - Tenencias_m-1) / Promedio(USDMXN_m) / 1000",
                            ),
                        ],
                        style={"height": "auto"},
                    ),
                    lg=8, md=12,
                ),
                dbc.Col(
                    card(
                        [
                            download_button("hflow-dl-period-sum-btn", "hflow-dl-period-sum"),
                            dcc.Loading(type="circle", color=BBVA_BLUE, children=dcc.Graph(id="hflow-period-sum")),
                            _footnote(
                                "Suma de todos los flujos mensuales del periodo seleccionado para cada participante. Es el resumen cross-section de la gráfica mensual que aparece a la izquierda.",
                                "Flujo del periodo_i = suma_m Flujo_i,m",
                            ),
                        ],
                        style={"height": "auto"},
                    ),
                    lg=4, md=12,
                ),
            ],
            class_name="g-3",
            align="start",
            style={"marginBottom": "14px"},
        ),

        _footnote(
            "El detalle completo abre Otros inversionistas locales en Aseguradoras y afianzadoras, Otros residentes locales "
            "y las posiciones asociadas a Banxico. El modo de 5 grupos conserva la estructura del reporte PDF.",
            "Otros inversionistas locales = Residentes locales - Bancos - Siefores - Fondos de inversión",
        ),
        dcc.Store(id="hflow-store-1"),
        dcc.Store(id="hflow-store-3"),
        dcc.Store(id="hflow-store-6"),
        dcc.Store(id="hflow-store-12"),
        dcc.Store(id="hflow-store-history"),
        dcc.Store(id="hflow-store-period-sum"),
    ]
)


@callback(
    Output("hflow-1", "figure"),
    Output("hflow-3", "figure"),
    Output("hflow-6", "figure"),
    Output("hflow-12", "figure"),
    Output("hflow-store-1", "data"),
    Output("hflow-store-3", "data"),
    Output("hflow-store-6", "data"),
    Output("hflow-store-12", "data"),
    Input("hflow-asof", "date"),
    Input("hflow-instrument", "value"),
    Input("hflow-breakdown", "value"),
)
def update_horizon_flows(as_of, instrument, breakdown):
    data = horizon_flows(instrument, as_of, horizons=(1, 3, 6, 12), breakdown=breakdown).round(4)
    subsets = [data[data["Horizon"] == h].copy() for h in (1, 3, 6, 12)]
    return (
        horizon_flow_fig(data, 1, instrument, breakdown),
        horizon_flow_fig(data, 3, instrument, breakdown),
        horizon_flow_fig(data, 6, instrument, breakdown),
        horizon_flow_fig(data, 12, instrument, breakdown),
        *(safe_records(x) for x in subsets),
    )


def _send(records, filename):
    return dcc.send_data_frame(
        pd.DataFrame(records or []).to_excel,
        filename,
        index=False,
        sheet_name="Datos",
    )


def _reg(h):
    @callback(
        Output(f"hflow-dl-{h}", "data"),
        Input(f"hflow-dl-{h}-btn", "n_clicks"),
        State(f"hflow-store-{h}", "data"),
        prevent_initial_call=True,
    )
    def _download(n, data):
        return _send(data, f"flujos_gubernamentales_{h}m.xlsx")


for _h in (1, 3, 6, 12):
    _reg(_h)


@callback(
    Output("hflow-history", "figure"),
    Output("hflow-period-sum", "figure"),
    Output("hflow-kpi-net", "children"),
    Output("hflow-kpi-buyer", "children"),
    Output("hflow-kpi-seller", "children"),
    Output("hflow-store-history", "data"),
    Output("hflow-store-period-sum", "data"),
    Input("hflow-history-dates", "start_date"),
    Input("hflow-history-dates", "end_date"),
    Input("hflow-instrument", "value"),
    Input("hflow-breakdown", "value"),
)
def update_flow_history(start_date, end_date, instrument, breakdown):
    data = flow_history(instrument, start_date, end_date, breakdown=breakdown).round(4)
    summary = period_flow_summary(data, breakdown).round(4)
    valid = summary.dropna(subset=["Net Flow USD bn"]) if not summary.empty else summary
    net = valid["Net Flow USD bn"].sum(min_count=1) if not valid.empty else float("nan")
    buyer = valid.loc[valid["Net Flow USD bn"].idxmax()] if not valid.empty else None
    seller = valid.loc[valid["Net Flow USD bn"].idxmin()] if not valid.empty else None
    if buyer is not None and buyer["Net Flow USD bn"] <= 0:
        buyer = None
    if seller is not None and seller["Net Flow USD bn"] >= 0:
        seller = None

    def fmt(v):
        return f"{v:,.2f}" if pd.notna(v) else "-"

    buyer_label = f"{buyer['Participant']} | {fmt(buyer['Net Flow USD bn'])}" if buyer is not None else "-"
    seller_label = f"{seller['Participant']} | {fmt(seller['Net Flow USD bn'])}" if seller is not None else "-"

    history_fig = monthly_flow_history_fig(data, instrument, breakdown)
    summary_fig = period_flow_summary_fig(data, instrument, breakdown)
    summary_fig.update_layout(height=500)

    return (
        history_fig,
        summary_fig,
        f"{fmt(net)} USD bn",
        buyer_label,
        seller_label,
        safe_records(data),
        safe_records(summary),
    )


@callback(
    Output("hflow-dl-history", "data"),
    Input("hflow-dl-history-btn", "n_clicks"),
    State("hflow-store-history", "data"),
    prevent_initial_call=True,
)
def dl_flow_history(n, data):
    return _send(data, "flujos_gubernamentales_historia_mensual.xlsx")


@callback(
    Output("hflow-dl-period-sum", "data"),
    Input("hflow-dl-period-sum-btn", "n_clicks"),
    State("hflow-store-period-sum", "data"),
    prevent_initial_call=True,
)
def dl_period_sum(n, data):
    return _send(data, "flujos_gubernamentales_suma_periodo.xlsx")
