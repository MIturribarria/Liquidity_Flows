# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from pages_lt.ui_utils import BBVA_BLUE, BBVA_GREY, card, download_button, page_title, safe_records
from pages_lt.holdings_utils import (
    HOLDINGS_LOAD_ERROR,
    INSTRUMENTS,
    SUMMARY_PARTICIPANTS,
    DETAIL_PARTICIPANTS,
    date_bounds,
)
from pages_lt.positioning_utils import (
    HEATMAP_METRICS,
    ownership_change_table,
    current_vs_history,
    hhi_history,
    issuance_absorption,
    asset_allocation_history,
    positioning_kpis,
    position_range_fig,
    flow_ownership_scatter_fig,
    ownership_change_heatmap_fig,
    hhi_history_fig,
    issuance_absorption_fig,
    asset_allocation_history_fig,
)


dash.register_page(
    __name__,
    path="/positioning-ownership-overview",
    name="Summary | Positioning & Ownership ",
    order=9,
)

_MIN_DATE, _MAX_DATE = date_bounds()
_DEFAULT_ALLOCATION_START = max(_MIN_DATE, _MAX_DATE - pd.DateOffset(years=5))


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
            "color": BBVA_GREY,
            "borderTop": "1px solid #E2E6EA",
            "paddingTop": "8px",
            "marginTop": "4px",
            "lineHeight": "1.45",
        },
    )


def _graph_card(btn_id, dl_id, graph_id, note, equation=None):
    return card(
        [
            download_button(btn_id, dl_id),
            dcc.Loading(type="circle", color=BBVA_BLUE, children=dcc.Graph(id=graph_id)),
            _footnote(note, equation),
        ],
        style={"height": "auto"},
    )


def _kpi(title, value_id, subtitle):
    return html.Div(
        [
            html.Div(title, style={"fontSize": "12px", "color": BBVA_GREY}),
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
            html.Div(subtitle, style={"fontSize": "10px", "color": BBVA_GREY, "marginTop": "2px"}),
        ],
        style={
            "backgroundColor": "white",
            "border": "1px solid #E2E6EA",
            "borderRadius": "10px",
            "padding": "12px 14px",
            "boxShadow": "0 1px 4px rgba(7,14,70,0.08)",
            "height": "100%",
        },
    )


layout = html.Div(
    [
        page_title(
            "Positioning & Ownership Overview",
            "Posicionamiento relativo, concentración de tenedores, cambios de participación y absorción de oferta a partir de la tenencia sectorizada de Banxico.",
        ),
        dbc.Alert(HOLDINGS_LOAD_ERROR, color="danger") if HOLDINGS_LOAD_ERROR else None,

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Fecha de corte"),
                        dcc.DatePickerSingle(
                            id="pos-asof",
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
                        html.Label("Instrumento"),
                        dcc.Dropdown(
                            id="pos-instrument",
                            value="MBonos",
                            clearable=False,
                            options=[{"label": x, "value": x} for x in INSTRUMENTS],
                        ),
                    ],
                    width=2,
                ),
                dbc.Col(
                    [
                        html.Label("Horizonte"),
                        dcc.Dropdown(
                            id="pos-horizon",
                            value=12,
                            clearable=False,
                            options=[{"label": f"{x}M", "value": x} for x in [1, 3, 6, 12]],
                        ),
                    ],
                    width=2,
                ),
                dbc.Col(
                    [
                        html.Label("Nivel de desglose"),
                        dcc.Dropdown(
                            id="pos-breakdown",
                            value="summary",
                            clearable=False,
                            options=[
                                {"label": "5 grupos del reporte", "value": "summary"},
                                {"label": "Detalle completo", "value": "detail"},
                            ],
                        ),
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        html.Label("Historia"),
                        dcc.Dropdown(
                            id="pos-lookback",
                            value=5,
                            clearable=False,
                            options=[{"label": f"{x} años", "value": x} for x in [3, 5, 10]],
                        ),
                    ],
                    width=3,
                ),
            ],
            class_name="g-3",
            style={"marginBottom": "12px"},
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Métrica del heatmap"),
                        dcc.Dropdown(
                            id="pos-heat-metric",
                            value="flow",
                            clearable=False,
                            options=[{"label": label, "value": key} for key, label in HEATMAP_METRICS.items()],
                        ),
                    ],
                    lg=4, md=12,
                ),
                dbc.Col(
                    [
                        html.Label("Inversionista para asset allocation"),
                        dcc.Dropdown(
                            id="pos-allocation-participant",
                            value="Inversionistas extranjeros",
                            clearable=False,
                            options=[{"label": x, "value": x} for x in SUMMARY_PARTICIPANTS],
                        ),
                    ],
                    lg=4, md=12,
                ),
                dbc.Col(
                    [
                        html.Label("Periodo histórico de asset allocation"),
                        dcc.DatePickerRange(
                            id="pos-allocation-dates",
                            min_date_allowed=_MIN_DATE,
                            max_date_allowed=_MAX_DATE,
                            start_date=_DEFAULT_ALLOCATION_START,
                            end_date=_MAX_DATE,
                            display_format="YYYY-MM-DD",
                        ),
                    ],
                    lg=4, md=12,
                ),
            ],
            class_name="g-3",
            style={"marginBottom": "16px"},
        ),

        dbc.Row(
            [
                dbc.Col(_kpi("Participación extranjera", "pos-kpi-foreign", "del instrumento seleccionado"), width=3),
                dbc.Col(_kpi("HHI de tenedores", "pos-kpi-hhi", "5 grupos; escala 0-10,000"), width=3),
                dbc.Col(_kpi("Mayor comprador", "pos-kpi-buyer", "en el horizonte seleccionado"), width=3),
                dbc.Col(_kpi("Mayor vendedor", "pos-kpi-seller", "en el horizonte seleccionado"), width=3),
            ],
            class_name="g-3",
            style={"marginBottom": "16px"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    _graph_card(
                        "pos-dl-range-btn", "pos-dl-range", "pos-range",
                        "Compara la participación actual de cada grupo con su mínimo, mediana y máximo del periodo histórico seleccionado. La etiqueta Pxx indica el percentil histórico de la observación actual.",
                        "Percentil_i = rango porcentual de Share_actual_i dentro de Share_histórico_i",
                    ),
                    lg=6, md=12,
                ),
                dbc.Col(
                    _graph_card(
                        "pos-dl-scatter-btn", "pos-dl-scatter", "pos-scatter",
                        "Relaciona el tamaño de la posición actual con el flujo acumulado del horizonte. El tamaño de la burbuja representa las tenencias actuales; la línea vertical es la mediana cross-section de participación.",
                        "Y_i = suma de flujos mensuales; X_i = participación actual (%)",
                    ),
                    lg=6, md=12,
                ),
            ],
            class_name="g-3",
            style={"marginBottom": "16px"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    _graph_card(
                        "pos-dl-heat-btn", "pos-dl-heat", "pos-heatmap",
                        "Resume quién está comprando/vendiendo o ganando/perdiendo participación en Cetes, Udibonos, Bondes D/F/G y MBonos durante el horizonte elegido.",
                        "Cambio share = Share_actual - Share_horizonte_anterior",
                    ),
                    width=12,
                )
            ],
            style={"marginBottom": "16px"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    _graph_card(
                        "pos-dl-abs-btn", "pos-dl-abs", "pos-absorption",
                        "Muestra qué sectores explican el cambio de tenencias frente al cambio de circulación del instrumento durante el horizonte. Un porcentaje de absorción es más interpretable cuando el cambio de circulación es positivo y material.",
                        "Absorción_i (%) = ΔTenencias_i / ΔCirculación × 100",
                    ),
                    lg=6, md=12,
                ),
                dbc.Col(
                    _graph_card(
                        "pos-dl-hhi-btn", "pos-dl-hhi", "pos-hhi",
                        "El HHI mide qué tan concentrada está la propiedad del instrumento entre los cinco grandes grupos de tenedores. Se eleva al cuadrado la participación porcentual de cada grupo y después se suman esos cuadrados. La escala va de 0 a 10,000: cuanto mayor es el HHI, más concentradas están las tenencias en pocos sectores; cuanto menor, más diversificada está la base de tenedores. Como referencia mecánica, si los cinco grupos tuvieran exactamente 20% cada uno, HHI = 2,000; si dos grupos tuvieran 50% cada uno, HHI = 5,000; y si un solo grupo concentrara 100%, HHI = 10,000. En este dashboard conviene interpretar sobre todo la dirección y magnitud del cambio del HHI en el tiempo. El HHI mide concentración de ownership, no liquidez de negociación ni riesgo por sí mismo.",
                        "HHI_t = Σ_i (Share_i,t en %)²",
                    ),
                    lg=6, md=12,
                ),
            ],
            class_name="g-3",
            style={"marginBottom": "16px"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    _graph_card(
                        "pos-dl-allocation-btn", "pos-dl-allocation", "pos-allocation",
                        "Evolución mensual de la distribución de cartera del inversionista seleccionado entre Cetes, Udibonos, Bondes D/F/G y MBonos durante el periodo elegido. El área total suma 100% en cada fecha. Al pasar el cursor se muestran tanto la participación como el monto de tenencias en MXN bn.",
                        "Allocation_j,t (%) = Holdings_j,t / Σ_k Holdings_k,t × 100",
                    ),
                    width=12,
                )
            ]
        ),

        html.Div(
            [
                html.Strong("Fuente y metodología: ", style={"color": BBVA_BLUE}),
                html.Span(
                    "Banxico - tenencia sectorizada de valores gubernamentales. Los flujos se aproximan con cambios mensuales de tenencias convertidos a USD con el USDMXN promedio mensual; no representan transacciones observadas directamente."
                ),
            ],
            style={
                "fontSize": "11px",
                "color": BBVA_GREY,
                "borderTop": "1px solid #E2E6EA",
                "paddingTop": "10px",
                "marginTop": "12px",
            },
        ),

        dcc.Store(id="pos-store-range"),
        dcc.Store(id="pos-store-scatter"),
        dcc.Store(id="pos-store-heat"),
        dcc.Store(id="pos-store-abs"),
        dcc.Store(id="pos-store-hhi"),
        dcc.Store(id="pos-store-allocation"),
    ]
)


@callback(
    Output("pos-allocation-participant", "options"),
    Output("pos-allocation-participant", "value"),
    Input("pos-breakdown", "value"),
    State("pos-allocation-participant", "value"),
)
def update_participant_options(breakdown, current):
    participants = SUMMARY_PARTICIPANTS if breakdown == "summary" else DETAIL_PARTICIPANTS
    value = current if current in participants else ("Inversionistas extranjeros" if "Inversionistas extranjeros" in participants else participants[0])
    return [{"label": x, "value": x} for x in participants], value


@callback(
    Output("pos-range", "figure"),
    Output("pos-scatter", "figure"),
    Output("pos-heatmap", "figure"),
    Output("pos-absorption", "figure"),
    Output("pos-hhi", "figure"),
    Output("pos-allocation", "figure"),
    Output("pos-kpi-foreign", "children"),
    Output("pos-kpi-hhi", "children"),
    Output("pos-kpi-buyer", "children"),
    Output("pos-kpi-seller", "children"),
    Output("pos-store-range", "data"),
    Output("pos-store-scatter", "data"),
    Output("pos-store-heat", "data"),
    Output("pos-store-abs", "data"),
    Output("pos-store-hhi", "data"),
    Output("pos-store-allocation", "data"),
    Input("pos-asof", "date"),
    Input("pos-instrument", "value"),
    Input("pos-horizon", "value"),
    Input("pos-breakdown", "value"),
    Input("pos-lookback", "value"),
    Input("pos-heat-metric", "value"),
    Input("pos-allocation-participant", "value"),
    Input("pos-allocation-dates", "start_date"),
    Input("pos-allocation-dates", "end_date"),
)
def update_positioning(
    as_of, instrument, horizon, breakdown, lookback, heat_metric,
    allocation_participant, allocation_start, allocation_end
):
    changes = ownership_change_table(as_of, int(horizon), breakdown).round(4)
    selected_changes = changes[changes["Instrument"] == instrument].copy() if not changes.empty else changes
    ranges = current_vs_history(instrument, as_of, int(lookback), breakdown).round(4)
    hhi = hhi_history(instrument, as_of, int(lookback)).round(4)
    absorption = issuance_absorption(instrument, as_of, int(horizon), breakdown).round(4)
    allocation = asset_allocation_history(
        allocation_participant, allocation_start, allocation_end
    ).round(4)
    kpis = positioning_kpis(instrument, as_of, int(horizon), breakdown)

    def fmt(v, digits=1):
        return f"{v:,.{digits}f}" if pd.notna(v) and np.isfinite(v) else "-"

    buyer = kpis["buyer"]
    buyer_val = kpis["buyer_value"]
    seller = kpis["seller"]
    seller_val = kpis["seller_value"]

    return (
        position_range_fig(ranges, instrument, int(lookback)),
        flow_ownership_scatter_fig(changes, instrument, int(horizon)),
        ownership_change_heatmap_fig(changes, heat_metric, breakdown),
        issuance_absorption_fig(absorption, instrument, int(horizon), breakdown),
        hhi_history_fig(hhi, instrument),
        asset_allocation_history_fig(allocation, allocation_participant),
        f"{fmt(kpis['foreign_share'])}%",
        fmt(kpis["hhi"], 0),
        f"{buyer} | {fmt(buyer_val, 2)} USD bn" if buyer != "-" else "-",
        f"{seller} | {fmt(seller_val, 2)} USD bn" if seller != "-" else "-",
        safe_records(ranges),
        safe_records(selected_changes),
        safe_records(changes),
        safe_records(absorption),
        safe_records(hhi),
        safe_records(allocation),
    )


def _send(records, filename):
    return dcc.send_data_frame(pd.DataFrame(records or []).to_excel, filename, index=False, sheet_name="Datos")


def _register_download(output_id, button_id, store_id, filename):
    @callback(
        Output(output_id, "data"),
        Input(button_id, "n_clicks"),
        State(store_id, "data"),
        prevent_initial_call=True,
    )
    def _download(n, data):
        return _send(data, filename)


_register_download("pos-dl-range", "pos-dl-range-btn", "pos-store-range", "positioning_historical_range.xlsx")
_register_download("pos-dl-scatter", "pos-dl-scatter-btn", "pos-store-scatter", "positioning_flow_vs_ownership.xlsx")
_register_download("pos-dl-heat", "pos-dl-heat-btn", "pos-store-heat", "positioning_investor_instrument_heatmap.xlsx")
_register_download("pos-dl-abs", "pos-dl-abs-btn", "pos-store-abs", "positioning_issuance_absorption.xlsx")
_register_download("pos-dl-hhi", "pos-dl-hhi-btn", "pos-store-hhi", "positioning_hhi_history.xlsx")
_register_download("pos-dl-allocation", "pos-dl-allocation-btn", "pos-store-allocation", "positioning_asset_allocation.xlsx")
