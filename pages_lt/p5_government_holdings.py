# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html

from pages_lt.ui_utils import BBVA_BLUE, card, download_button, page_title, safe_records
from pages_lt.holdings_utils import (
    HOLDINGS_LOAD_ERROR,
    INSTRUMENTS,
    date_bounds,
    holdings_table,
    snapshot,
    holdings_history,
    donut_fig,
    holdings_history_fig,
)


dash.register_page(
    __name__,
    path="/government-holdings",
    name="Government Securities Holdings by Investor",
    order=5,
)

_MIN_DATE, _MAX_DATE = date_bounds()


def _footnote(text, equation=None):
    children = [
        html.Span("Nota: ", style={"fontWeight": "bold", "color": BBVA_BLUE}),
        html.Span(text),
    ]
    if equation:
        children += [
            html.Br(),
            html.Span("Ecuación: ", style={"fontWeight": "bold", "color": BBVA_BLUE}),
            html.Code(equation, style={"fontSize": "11px", "backgroundColor": "#F4F6F8", "padding": "2px 5px"}),
        ]
    return html.Div(
        children,
        style={
            "fontSize": "11px", "color": "#46536D",
            "borderTop": "1px solid #E2E6EA", "paddingTop": "8px", "marginTop": "4px",
        },
    )


def _graph_card(btn_id, dl_id, graph_id, note, equation):
    return card([
        download_button(btn_id, dl_id),
        dcc.Loading(type="circle", color=BBVA_BLUE, children=dcc.Graph(id=graph_id)),
        _footnote(note, equation),
    ], style={"height": "auto"})


_error_box = dbc.Alert(HOLDINGS_LOAD_ERROR, color="danger", style={"marginBottom": "14px"}) if HOLDINGS_LOAD_ERROR else None

layout = html.Div([
    page_title(
        "Tenencias de Valores Gubernamentales",
        "Tenencias y participación por tipo de inversionista, con opción de ver los 5 grupos del reporte o el desglose completo del CSV.",
    ),
    _error_box,
    dbc.Row([
        dbc.Col([
            html.Label("Fecha de corte"),
            dcc.DatePickerSingle(
                id="hold-asof", min_date_allowed=_MIN_DATE, max_date_allowed=_MAX_DATE,
                date=_MAX_DATE, display_format="YYYY-MM-DD",
            ),
        ], width=3),
        dbc.Col([
            html.Label("Historia"),
            dcc.Dropdown(
                id="hold-months", value=48, clearable=False,
                options=[
                    {"label": "24 meses", "value": 24}, {"label": "48 meses", "value": 48},
                    {"label": "60 meses", "value": 60}, {"label": "10 años", "value": 120},
                ],
            ),
        ], width=3),
        dbc.Col([
            html.Label("Instrumento para detalle"),
            dcc.Dropdown(
                id="hold-instrument", value="MBonos", clearable=False,
                options=[{"label": x, "value": x} for x in INSTRUMENTS],
            ),
        ], width=3),
        dbc.Col([
            html.Label("Nivel de desglose"),
            dcc.Dropdown(
                id="hold-breakdown", value="detail", clearable=False,
                options=[
                    {"label": "Detalle completo", "value": "detail"},
                    {"label": "5 grupos del reporte", "value": "summary"},
                ],
            ),
        ], width=3),
    ], style={"marginBottom": "14px"}),

    html.H4("Resumen de tenencias", style={"color": BBVA_BLUE, "fontWeight": "bold"}),
    card([
        download_button("hold-dl-table-btn", "hold-dl-table"),
        dash_table.DataTable(
            id="hold-table", page_action="none",
            style_table={"overflowX": "auto"},
            style_header={"backgroundColor": BBVA_BLUE, "color": "white", "fontWeight": "bold"},
            style_cell={
                "fontFamily": "Arial", "fontSize": "12px", "padding": "6px",
                "textAlign": "center", "minWidth": "105px",
            },
        ),
        _footnote(
            "En 'Detalle completo', el bloque de Otros inversionistas locales se abre en Aseguradoras y afianzadoras, Otros residentes locales, Valores adquiridos por Banxico, Reportos con Banxico y Garantías recibidas por Banxico.",
            "Otros inversionistas locales = Residentes locales - Bancos - Siefores - Fondos de inversión",
        ),
    ], style={"marginBottom": "16px", "height": "auto"}),

    html.H4("Tenencias totales", style={"color": BBVA_BLUE, "fontWeight": "bold"}),
    dbc.Row([
        dbc.Col(_graph_card(
            "hold-dl-total-donut-btn", "hold-dl-total-donut", "hold-total-donut",
            "Distribución de las tenencias totales entre los inversionistas seleccionados.",
            "Participación_i = Tenencias_i / Circulacion total x 100",
        ), width=4),
        dbc.Col(_graph_card(
            "hold-dl-total-history-btn", "hold-dl-total-history", "hold-total-history",
            "Evolución mensual de la participación porcentual en las tenencias totales.",
            "Participación_i,t = Tenencias_i,t / Circulacion total_t x 100",
        ), width=8),
    ], style={"marginBottom": "16px"}),

    html.H4("Detalle por instrumento", style={"color": BBVA_BLUE, "fontWeight": "bold"}),
    dbc.Row([
        dbc.Col(_graph_card(
            "hold-dl-inst-donut-btn", "hold-dl-inst-donut", "hold-inst-donut",
            "Composición de tenencias del instrumento seleccionado a la fecha de corte.",
            "Participación_i = Tenencias_i / Circulacion total x 100",
        ), width=4),
        dbc.Col(_graph_card(
            "hold-dl-inst-history-btn", "hold-dl-inst-history", "hold-inst-history",
            "Historia mensual de la composición del instrumento seleccionado.",
            "Participación_i,t = Tenencias_i,t / Circulacion total_t x 100",
        ), width=8),
    ]),

    dcc.Store(id="hold-store-table"), dcc.Store(id="hold-store-total-donut"),
    dcc.Store(id="hold-store-total-history"), dcc.Store(id="hold-store-inst-donut"),
    dcc.Store(id="hold-store-inst-history"),
])


@callback(
    Output("hold-table", "data"), Output("hold-table", "columns"),
    Output("hold-total-donut", "figure"), Output("hold-total-history", "figure"),
    Output("hold-inst-donut", "figure"), Output("hold-inst-history", "figure"),
    Output("hold-store-table", "data"), Output("hold-store-total-donut", "data"),
    Output("hold-store-total-history", "data"), Output("hold-store-inst-donut", "data"),
    Output("hold-store-inst-history", "data"),
    Input("hold-asof", "date"), Input("hold-months", "value"),
    Input("hold-instrument", "value"), Input("hold-breakdown", "value"),
)
def update_holdings(as_of, months, instrument, breakdown):
    table = holdings_table(as_of, breakdown=breakdown).round(2)
    total_snap = snapshot("Total", as_of, total_mode="display", breakdown=breakdown).round(4)
    total_hist = holdings_history("Total", as_of, int(months), total_mode="display", breakdown=breakdown)
    inst_snap = snapshot(instrument, as_of, total_mode="display", breakdown=breakdown).round(4)
    inst_hist = holdings_history(instrument, as_of, int(months), total_mode="display", breakdown=breakdown)

    date_label = pd.to_datetime(as_of).strftime("%b %Y") if as_of else ""
    columns = []
    for c in table.columns:
        if c == "Participant":
            columns.append({"name": "Participante", "id": c, "type": "text"})
        else:
            columns.append({"name": c, "id": c, "type": "numeric", "format": {"specifier": ",.2f"}})

    return (
        safe_records(table), columns,
        donut_fig(total_snap, f"Tenencias totales (%) | {date_label}"),
        holdings_history_fig(total_hist, "Historia de tenencias totales (%)"),
        donut_fig(inst_snap, f"{instrument} | Tenencias (%) | {date_label}"),
        holdings_history_fig(inst_hist, f"{instrument} | Historia de tenencias (%)"),
        safe_records(table), safe_records(total_snap), safe_records(total_hist),
        safe_records(inst_snap), safe_records(inst_hist),
    )


def _send(records, filename):
    df = pd.DataFrame(records or [])
    return dcc.send_data_frame(df.to_excel, filename, index=False, sheet_name="Datos")


def _register_download(output_id, button_id, store_id, filename):
    @callback(Output(output_id, "data"), Input(button_id, "n_clicks"), State(store_id, "data"), prevent_initial_call=True)
    def _download(n, data):
        return _send(data, filename)


_register_download("hold-dl-table", "hold-dl-table-btn", "hold-store-table", "tenencias_gubernamentales_tabla.xlsx")
_register_download("hold-dl-total-donut", "hold-dl-total-donut-btn", "hold-store-total-donut", "tenencias_totales_snapshot.xlsx")
_register_download("hold-dl-total-history", "hold-dl-total-history-btn", "hold-store-total-history", "tenencias_totales_historia.xlsx")
_register_download("hold-dl-inst-donut", "hold-dl-inst-donut-btn", "hold-store-inst-donut", "tenencias_instrumento_snapshot.xlsx")
_register_download("hold-dl-inst-history", "hold-dl-inst-history-btn", "hold-store-inst-history", "tenencias_instrumento_historia.xlsx")
