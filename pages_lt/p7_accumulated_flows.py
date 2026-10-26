# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from pages_lt.ui_utils import BBVA_BLUE, card, download_button, page_title, safe_records
from pages_lt.holdings_utils import (
    HOLDINGS_DAILY,
    HOLDINGS_LOAD_ERROR,
    INSTRUMENTS,
    SELECTABLE_PARTICIPANTS,
    date_bounds,
    accumulated_ytd,
    annual_flows,
    cumulative_ytd_fig,
    annual_flow_fig,
)


dash.register_page(
    __name__,
    path="/accumulated-holdings-flows",
    name="Accumulated flows by Investor",
    order=7,
)

_MIN_DATE, _MAX_DATE = date_bounds()
_MIN_YEAR = int(HOLDINGS_DAILY["Fecha"].dt.year.min()) if not HOLDINGS_DAILY.empty else 2010
_MAX_YEAR = int(HOLDINGS_DAILY["Fecha"].dt.year.max()) if not HOLDINGS_DAILY.empty else pd.Timestamp.today().year
_DEFAULT_START_YEAR = 2010 if _MIN_YEAR <= 2010 <= _MAX_YEAR else max(_MIN_YEAR, _MAX_YEAR - 15)
_AVAILABLE_YEARS = sorted(HOLDINGS_DAILY["Fecha"].dropna().dt.year.unique().astype(int).tolist()) if not HOLDINGS_DAILY.empty else list(range(2010, _MAX_YEAR + 1))
_DEFAULT_YEARS = _AVAILABLE_YEARS[-5:] if len(_AVAILABLE_YEARS) >= 5 else _AVAILABLE_YEARS


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
            "fontSize": "11px",
            "color": "#46536D",
            "borderTop": "1px solid #E2E6EA",
            "paddingTop": "7px",
            "marginTop": "2px",
        },
    )


def _slot(slot, default_instrument):
    return dbc.Col(
        [
            html.Label(f"Instrumento {slot}"),
            dcc.Dropdown(
                id=f"acc-inst-{slot}",
                value=default_instrument,
                clearable=False,
                options=[{"label": x, "value": x} for x in INSTRUMENTS],
                style={"marginBottom": "8px"},
            ),
            card(
                [
                    download_button(f"acc-dl-cum-{slot}-btn", f"acc-dl-cum-{slot}"),
                    dcc.Loading(
                        type="circle",
                        color=BBVA_BLUE,
                        children=dcc.Graph(id=f"acc-cum-{slot}", style={"height": "315px"}),
                    ),
                    _footnote(
                        "Compara únicamente los años seleccionados. La línea Promedio es el promedio aritmético, mes a mes, "
                        "de los flujos acumulados de esos años. Si un año está incompleto, el promedio de cada mes usa las observaciones disponibles.",
                        "Promedio_m = (1/N_m) × suma_y Acumulado_y,m",
                    ),
                ],
                style={"height": "auto", "marginBottom": "12px"},
            ),
            card(
                [
                    download_button(f"acc-dl-ann-{slot}-btn", f"acc-dl-ann-{slot}"),
                    dcc.Loading(
                        type="circle",
                        color=BBVA_BLUE,
                        children=dcc.Graph(id=f"acc-ann-{slot}", style={"height": "285px"}),
                    ),
                    _footnote(
                        "Flujo neto total por año calculado como la suma de los flujos mensuales en USD.",
                        "Flujo anual_y = suma Flujo mensual_y,m",
                    ),
                ],
                style={"height": "auto"},
            ),
        ],
        width=4,
        style={"alignSelf": "flex-start"},
    )


layout = html.Div(
    [
        page_title(
            "Flujos Acumulados por Inversionista",
            "Compara años específicos en la evolución mensual acumulada y muestra su promedio, además del flujo total anual por participante e instrumento.",
        ),
        dbc.Alert(HOLDINGS_LOAD_ERROR, color="danger") if HOLDINGS_LOAD_ERROR else None,
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Participante"),
                        dcc.Dropdown(
                            id="acc-participant",
                            value="Bancos locales",
                            clearable=False,
                            options=[{"label": x, "value": x} for x in SELECTABLE_PARTICIPANTS],
                        ),
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        html.Label("Fecha de corte"),
                        dcc.DatePickerSingle(
                            id="acc-asof",
                            min_date_allowed=_MIN_DATE,
                            max_date_allowed=_MAX_DATE,
                            date=_MAX_DATE,
                            display_format="YYYY-MM-DD",
                        ),
                    ],
                    width=2,
                ),
                dbc.Col(
                    [
                        html.Label("Años a comparar"),
                        dcc.Dropdown(
                            id="acc-years",
                            value=_DEFAULT_YEARS,
                            multi=True,
                            clearable=False,
                            options=[{"label": str(y), "value": y} for y in _AVAILABLE_YEARS],
                            placeholder="Selecciona uno o más años",
                        ),
                    ],
                    width=5,
                ),
                dbc.Col(
                    [
                        html.Label("Inicio de barras anuales"),
                        dcc.Dropdown(
                            id="acc-start-year",
                            value=_DEFAULT_START_YEAR,
                            clearable=False,
                            options=[
                                {"label": str(y), "value": y}
                                for y in range(max(_MIN_YEAR, 1992), _MAX_YEAR + 1)
                            ],
                        ),
                    ],
                    width=2,
                ),
            ],
            style={"marginBottom": "14px"},
        ),
        dbc.Row(
            [_slot(1, "Cetes"), _slot(2, "MBonos"), _slot(3, "Total")],
            style={"alignItems": "flex-start"},
        ),
        _footnote(
            "Los flujos mensuales se aproximan con cambios en tenencias y el USDMXN promedio mensual. "
            "Puedes seleccionar años no consecutivos, por ejemplo 2010, 2012 y 2014; el promedio se calcula únicamente con esos años.",
            "Flujo_m = Delta Tenencias_m / Promedio(USDMXN_m) / 1000",
        ),
        *[dcc.Store(id=f"acc-store-cum-{i}") for i in (1, 2, 3)],
        *[dcc.Store(id=f"acc-store-ann-{i}") for i in (1, 2, 3)],
    ]
)


@callback(
    Output("acc-cum-1", "figure"),
    Output("acc-ann-1", "figure"),
    Output("acc-cum-2", "figure"),
    Output("acc-ann-2", "figure"),
    Output("acc-cum-3", "figure"),
    Output("acc-ann-3", "figure"),
    Output("acc-store-cum-1", "data"),
    Output("acc-store-ann-1", "data"),
    Output("acc-store-cum-2", "data"),
    Output("acc-store-ann-2", "data"),
    Output("acc-store-cum-3", "data"),
    Output("acc-store-ann-3", "data"),
    Input("acc-participant", "value"),
    Input("acc-asof", "date"),
    Input("acc-years", "value"),
    Input("acc-start-year", "value"),
    Input("acc-inst-1", "value"),
    Input("acc-inst-2", "value"),
    Input("acc-inst-3", "value"),
)
def update_accumulated(participant, as_of, years, start_year, inst1, inst2, inst3):
    selected_years = sorted({int(y) for y in (years or _DEFAULT_YEARS)})
    outputs, stores = [], []

    for inst in [inst1, inst2, inst3]:
        cum = accumulated_ytd(
            inst,
            participant,
            as_of,
            years_back=None,
            years=selected_years,
        ).round(4)
        ann = annual_flows(inst, participant, as_of, int(start_year)).round(4)
        outputs.extend(
            [
                cumulative_ytd_fig(cum, inst, participant),
                annual_flow_fig(ann, inst, participant),
            ]
        )
        stores.extend([safe_records(cum), safe_records(ann)])

    return (*outputs, *stores)


def _send(records, filename):
    return dcc.send_data_frame(
        pd.DataFrame(records or []).to_excel,
        filename,
        index=False,
        sheet_name="Datos",
    )


def _register(slot, kind):
    @callback(
        Output(f"acc-dl-{kind}-{slot}", "data"),
        Input(f"acc-dl-{kind}-{slot}-btn", "n_clicks"),
        State(f"acc-store-{kind}-{slot}", "data"),
        prevent_initial_call=True,
    )
    def _download(n, data):
        return _send(data, f"flujos_acumulados_{kind}_{slot}.xlsx")


for _slot_id in (1, 2, 3):
    _register(_slot_id, "cum")
    _register(_slot_id, "ann")
