# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html
from dash.exceptions import PreventUpdate

from data import df_base
from pages_lt.ui_utils import (
    BBVA_BLUE,
    download_button,
    page_title,
    card,
    safe_records,
)
from pages_lt.liquidity_detail_utils import (
    MARKET_LABELS,
    prepare_liquidity_detail_base,
    active_bonds,
    participants,
    metric_series,
    annual_share,
    summary_table,
    current_year_range,
    line_fig,
    share_fig,
    range_fig,
)

MARKET = "BONOTF"
MARKET_LABEL = "MBono"
PREFIX = "mbono-liq"
PAGE_NAME = "MBono | Liquidity Tracker"

dash.register_page(__name__, path="/mbono-liquidity", name=PAGE_NAME, order=1)

_df = prepare_liquidity_detail_base(df_base)
_min_date = _df["Día"].min()
_max_date = _df["Día"].max()
_participants = participants(_df, MARKET)
_bond_list = active_bonds(_df, MARKET, _max_date)
_default_participant = "Total" if "Total" in _participants else (_participants[0] if _participants else None)


def _footnote(text, equation=None):
    children = [
        html.Span("Nota: ", style={"fontWeight": "bold", "color": BBVA_BLUE}),
        html.Span(text),
    ]
    if equation:
        children += [
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
        children,
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
            f"{MARKET_LABEL} Liquidity Tracker",
            "Volumen, ticket, turnover, estadísticas por bono y participación por tipo de inversionista.",
        ),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Periodo"),
                        dcc.DatePickerRange(
                            id=f"{PREFIX}-dates",
                            min_date_allowed=_min_date,
                            max_date_allowed=_max_date,
                            start_date=max(_min_date, _max_date - pd.DateOffset(years=10)),
                            end_date=_max_date,
                            display_format="YYYY-MM-DD",
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        html.Label("Bono(s)"),
                        dcc.Dropdown(
                            id=f"{PREFIX}-bonds",
                            options=[{"label": x, "value": x} for x in _bond_list],
                            value=["Total"],
                            multi=True,
                            clearable=False,
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        html.Label("Participante"),
                        dcc.Dropdown(
                            id=f"{PREFIX}-participant",
                            options=[{"label": x, "value": x} for x in _participants],
                            value=_default_participant,
                            clearable=False,
                        ),
                    ],
                    width=2,
                ),
                dbc.Col(
                    [
                        html.Label("Términos"),
                        dcc.Dropdown(
                            id=f"{PREFIX}-terms",
                            options=[
                                {"label": "MXN", "value": "MXN"},
                                {"label": "DV01", "value": "DV01"},
                            ],
                            value="MXN",
                            clearable=False,
                        ),
                    ],
                    width=2,
                ),
            ],
            style={"marginBottom": "10px"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Media móvil"),
                        dcc.Dropdown(
                            id=f"{PREFIX}-rolling",
                            options=[
                                {"label": "5 observaciones", "value": 5},
                                {"label": "20 observaciones", "value": 20},
                                {"label": "30 observaciones", "value": 30},
                                {"label": "60 observaciones", "value": 60},
                            ],
                            value=30,
                            clearable=False,
                        ),
                    ],
                    width=3,
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
                    width=9,
                ),
            ],
            style={"marginBottom": "16px"},
        ),

        html.H4("Liquidity metrics", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-vol-btn",
                        f"{PREFIX}-dl-vol",
                        f"{PREFIX}-vol",
                        "Volumen promedio negociado suavizado con la media móvil seleccionada. En MXN usa la métrica Volumen; en DV01 usa VolumenDV01.",
                        "MA_N(Volume)_t = (1/N) × Σ Volume_{t-i}",
                    ),
                    width=12,
                ),
            ],
            style={"marginBottom": "12px"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-ticket-btn",
                        f"{PREFIX}-dl-ticket",
                        f"{PREFIX}-ticket",
                        "Ticket promedio por operación suavizado con la media móvil seleccionada. Permite evaluar el tamaño típico de las operaciones.",
                        "Ticket = Traded Volume / Number of Trades",
                    ),
                    width=6,
                ),
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-turnover-btn",
                        f"{PREFIX}-dl-turnover",
                        f"{PREFIX}-turnover",
                        "Turnover representa el volumen negociado relativo al monto en circulación de la emisión.",
                        "Turnover (%) = Traded Volume / Outstanding × 100",
                    ),
                    width=6,
                ),
            ],
            style={"marginBottom": "16px"},
        ),

        html.H4("Historical summary", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(
                    card(
                        [
                            download_button(f"{PREFIX}-dl-table-btn", f"{PREFIX}-dl-table"),
                            dash_table.DataTable(
                                id=f"{PREFIX}-table",
                                page_action="none",
                                sort_action="native",
                                filter_action="native",
                                style_table={
                                    "overflowX": "auto",
                                    "maxHeight": "700px",
                                    "overflowY": "auto",
                                },
                                style_header={
                                    "backgroundColor": BBVA_BLUE,
                                    "color": "white",
                                    "fontWeight": "bold",
                                },
                                style_cell={
                                    "fontFamily": "Arial",
                                    "fontSize": "12px",
                                    "padding": "6px",
                                    "textAlign": "center",
                                    "minWidth": "110px",
                                },
                            ),
                            _footnote(
                                "Comparativo por bono para los tres años más recientes disponibles. Incluye promedio de volumen, turnover y ticket.",
                                "Average(metric, year) = mean(metric_t) for observations within year",
                            ),
                        ]
                    ),
                    width=12,
                )
            ],
            style={"marginBottom": "16px"},
        ),

        html.H4("Current-year ranges", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-range-vol-btn",
                        f"{PREFIX}-dl-range-vol",
                        f"{PREFIX}-range-vol",
                        "Promedio, mínimo y máximo observados durante el año más reciente disponible para el volumen por bono.",
                        "Range = [min(Volume), max(Volume)] around mean(Volume)",
                    ),
                    width=6,
                ),
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-range-ticket-btn",
                        f"{PREFIX}-dl-range-ticket",
                        f"{PREFIX}-range-ticket",
                        "Promedio, mínimo y máximo observados durante el año más reciente disponible para el ticket por bono.",
                        "Range = [min(Ticket), max(Ticket)] around mean(Ticket)",
                    ),
                    width=6,
                ),
            ],
            style={"marginBottom": "16px"},
        ),

        html.H4("Investor participation", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(
                    _graph_card(
                        f"{PREFIX}-dl-share-btn",
                        f"{PREFIX}-dl-share",
                        f"{PREFIX}-share",
                        "Participación anual de cada tipo de inversionista en el volumen negociado del mercado seleccionado.",
                        "Share_i,y (%) = Volume_i,y / Σ_j Volume_j,y × 100",
                    ),
                    width=12,
                )
            ]
        ),

        dcc.Store(id=f"{PREFIX}-store-vol"),
        dcc.Store(id=f"{PREFIX}-store-ticket"),
        dcc.Store(id=f"{PREFIX}-store-turnover"),
        dcc.Store(id=f"{PREFIX}-store-table"),
        dcc.Store(id=f"{PREFIX}-store-range-vol"),
        dcc.Store(id=f"{PREFIX}-store-range-ticket"),
        dcc.Store(id=f"{PREFIX}-store-share"),
    ],
    style={"fontFamily": "Arial", "backgroundColor": "white"},
)


@callback(
    Output(f"{PREFIX}-vol", "figure"),
    Output(f"{PREFIX}-ticket", "figure"),
    Output(f"{PREFIX}-turnover", "figure"),
    Output(f"{PREFIX}-table", "data"),
    Output(f"{PREFIX}-table", "columns"),
    Output(f"{PREFIX}-range-vol", "figure"),
    Output(f"{PREFIX}-range-ticket", "figure"),
    Output(f"{PREFIX}-share", "figure"),
    Output(f"{PREFIX}-store-vol", "data"),
    Output(f"{PREFIX}-store-ticket", "data"),
    Output(f"{PREFIX}-store-turnover", "data"),
    Output(f"{PREFIX}-store-table", "data"),
    Output(f"{PREFIX}-store-range-vol", "data"),
    Output(f"{PREFIX}-store-range-ticket", "data"),
    Output(f"{PREFIX}-store-share", "data"),
    Input(f"{PREFIX}-run", "n_clicks"),
    State(f"{PREFIX}-dates", "start_date"),
    State(f"{PREFIX}-dates", "end_date"),
    State(f"{PREFIX}-bonds", "value"),
    State(f"{PREFIX}-participant", "value"),
    State(f"{PREFIX}-terms", "value"),
    State(f"{PREFIX}-rolling", "value"),
    prevent_initial_call=True,
)
def update_page(n_clicks, start_date, end_date, bonds_selected, participant, terms, rolling):
    if not n_clicks:
        raise PreventUpdate

    bonds_selected = bonds_selected or ["Total"]

    vol = metric_series(
        _df, MARKET, participant, bonds_selected, start_date, end_date,
        "Volume", terms, rolling
    )
    ticket = metric_series(
        _df, MARKET, participant, bonds_selected, start_date, end_date,
        "Ticket", terms, rolling
    )
    turnover = metric_series(
        _df, MARKET, participant, bonds_selected, start_date, end_date,
        "Turnover", terms, rolling
    )

    table = summary_table(_df, MARKET, participant, terms, years_back=3).round(2)
    range_vol = current_year_range(_df, MARKET, participant, terms, "Volume")
    range_ticket = current_year_range(_df, MARKET, participant, terms, "Ticket")
    share = annual_share(_df, MARKET)

    unit = "MXN mn" if terms == "MXN" else "DV01 USDk"

    return (
        line_fig(vol, f"{MARKET_LABEL} | Average traded volume ({unit})", unit),
        line_fig(ticket, f"{MARKET_LABEL} | Average traded ticket ({unit})", unit),
        line_fig(turnover, f"{MARKET_LABEL} | Turnover (%)", "%"),
        safe_records(table),
        [{"name": c, "id": c} for c in table.columns],
        range_fig(
            range_vol,
            f"{MARKET_LABEL} | Average, minimum and maximum traded volume",
            unit,
        ),
        range_fig(
            range_ticket,
            f"{MARKET_LABEL} | Average, minimum and maximum ticket",
            unit,
        ),
        share_fig(share, MARKET),
        safe_records(vol),
        safe_records(ticket),
        safe_records(turnover),
        safe_records(table),
        safe_records(range_vol),
        safe_records(range_ticket),
        safe_records(share),
    )


def _send(records, filename):
    df = pd.DataFrame(records or [])
    return dcc.send_data_frame(
        df.to_excel,
        filename,
        index=False,
        sheet_name="Datos",
    )


def _register_download(output_id, button_id, store_id, filename):
    @callback(
        Output(output_id, "data"),
        Input(button_id, "n_clicks"),
        State(store_id, "data"),
        prevent_initial_call=True,
    )
    def _download(n, data):
        return _send(data, filename)


_register_download(f"{PREFIX}-dl-vol", f"{PREFIX}-dl-vol-btn", f"{PREFIX}-store-vol", f"{PREFIX}_volume.xlsx")
_register_download(f"{PREFIX}-dl-ticket", f"{PREFIX}-dl-ticket-btn", f"{PREFIX}-store-ticket", f"{PREFIX}_ticket.xlsx")
_register_download(f"{PREFIX}-dl-turnover", f"{PREFIX}-dl-turnover-btn", f"{PREFIX}-store-turnover", f"{PREFIX}_turnover.xlsx")
_register_download(f"{PREFIX}-dl-table", f"{PREFIX}-dl-table-btn", f"{PREFIX}-store-table", f"{PREFIX}_summary_table.xlsx")
_register_download(f"{PREFIX}-dl-range-vol", f"{PREFIX}-dl-range-vol-btn", f"{PREFIX}-store-range-vol", f"{PREFIX}_volume_range.xlsx")
_register_download(f"{PREFIX}-dl-range-ticket", f"{PREFIX}-dl-range-ticket-btn", f"{PREFIX}-store-range-ticket", f"{PREFIX}_ticket_range.xlsx")
_register_download(f"{PREFIX}-dl-share", f"{PREFIX}-dl-share-btn", f"{PREFIX}-store-share", f"{PREFIX}_investor_share.xlsx")
