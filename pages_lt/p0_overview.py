# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from data import df_base
from pages_lt.ui_utils import (
    BBVA_BLUE,
    BBVA_COLORS,
    download_button,
    page_title,
    card,
    safe_records,
    empty_fig,
    apply_layout,
)
from pages_lt.liquidity_utils import (
    MARKET_LABELS,
    METRIC_LABELS,
    prepare_liquidity_base,
    liquidity_snapshot,
    liquidity_momentum,
    liquidity_heatmap_data,
    participant_flow_series,
    investor_bond_heatmap,
    flow_liquidity_data,
    market_kpis,
)


dash.register_page(
    __name__,
    path="/liquidity-overview",
    name="Summary | Liquidity & Net purchases",
    order=0,
)


BBVA_RED = "#B00028"
BBVA_GREEN = "#024700"
BBVA_GREY = "#46536D"
BBVA_LIGHT = "#F4F6F8"

_df = prepare_liquidity_base(df_base)
_min_date = _df["Día"].min()
_max_date = _df["Día"].max()


def _footnote(text: str, equation: str | None = None):
    children = [
        html.Span(
            "Nota: ",
            style={"fontWeight": "bold", "color": BBVA_BLUE},
        ),
        html.Span(text),
    ]
    if equation:
        children += [
            html.Br(),
            html.Span(
                "Ecuación: ",
                style={"fontWeight": "bold", "color": BBVA_BLUE},
            ),
            html.Code(
                equation,
                style={
                    "fontSize": "11px",
                    "color": "#070E46",
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
            "lineHeight": "1.45",
            "marginTop": "4px",
            "paddingTop": "8px",
            "borderTop": "1px solid #E2E6EA",
        },
    )


def _chart_card(button_id, download_id, graph_id, footnote_text, equation=None):
    return card(
        [
            download_button(button_id, download_id),
            dcc.Loading(
                type="circle",
                color=BBVA_BLUE,
                children=dcc.Graph(id=graph_id, figure=empty_fig("Cargando análisis...")),
            ),
            _footnote(footnote_text, equation),
        ]
    )


def _kpi_box(title, value_id, suffix=""):
    return html.Div(
        [
            html.Div(title, style={"fontSize": "12px", "color": BBVA_GREY}),
            html.Div(
                id=value_id,
                children="-",
                style={
                    "fontSize": "24px",
                    "fontWeight": "bold",
                    "color": BBVA_BLUE,
                    "marginTop": "3px",
                },
            ),
            html.Div(suffix, style={"fontSize": "11px", "color": BBVA_GREY}),
        ],
        style={
            "backgroundColor": "white",
            "border": "1px solid #E2E6EA",
            "borderRadius": "10px",
            "padding": "12px 14px",
            "boxShadow": "0 1px 4px rgba(7, 14, 70, 0.08)",
            "height": "100%",
        },
    )


layout = html.Div(
    [
        page_title(
            "Government Bond Market Liquidity & Flows",
            "Liquidez cross-section, momentum, concentración temporal y flujos por tipo de inversionista.",
        ),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Mercado"),
                        dcc.Dropdown(
                            id="liq-market",
                            value="BONOTF",
                            clearable=False,
                            options=[
                                {"label": "MBono", "value": "BONOTF"},
                                {"label": "Udibono", "value": "UDIBONOS"},
                            ],
                        ),
                    ],
                    width=2,
                ),
                dbc.Col(
                    [
                        html.Label("Fecha final"),
                        dcc.DatePickerSingle(
                            id="liq-end-date",
                            min_date_allowed=_min_date,
                            max_date_allowed=_max_date,
                            date=_max_date,
                            display_format="YYYY-MM-DD",
                        ),
                    ],
                    width=2,
                ),
                dbc.Col(
                    [
                        html.Label("Ventana de análisis"),
                        dcc.Dropdown(
                            id="liq-window",
                            value=90,
                            clearable=False,
                            options=[
                                {"label": "30 días", "value": 30},
                                {"label": "60 días", "value": 60},
                                {"label": "90 días", "value": 90},
                                {"label": "180 días", "value": 180},
                                {"label": "1 año", "value": 365},
                            ],
                        ),
                    ],
                    width=2,
                ),
                dbc.Col(
                    [
                        html.Label("Participante"),
                        dcc.Dropdown(
                            id="liq-participant",
                            value="Res. Exterior",
                            clearable=False,
                            options=[
                                {"label": x, "value": x}
                                for x in [
                                    "Total",
                                    "Siefores",
                                    "Soc Inversion",
                                    "Otros Nac.",
                                    "Res. Exterior",
                                ]
                            ],
                        ),
                    ],
                    width=2,
                ),
                dbc.Col(
                    [
                        html.Label("Unidad de flow"),
                        dcc.Dropdown(
                            id="liq-flow-unit",
                            value="USD",
                            clearable=False,
                            options=[
                                {"label": "USD mn", "value": "USD"},
                                {"label": "DV01 USDk", "value": "DV01"},
                            ],
                        ),
                    ],
                    width=2,
                ),
                dbc.Col(
                    [
                        html.Label(" "),
                        dbc.Button(
                            "Cargar / actualizar análisis",
                            id="liq-run",
                            color="primary",
                            n_clicks=0,
                            style={"width": "100%"},
                        ),
                    ],
                    width=2,
                ),
            ],
            style={"marginBottom": "14px"},
        ),

        html.H4("Market overview", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(_kpi_box("Average daily volume", "liq-kpi-volume", "MXN mn"), width=3),
                dbc.Col(_kpi_box("Average turnover", "liq-kpi-turnover", "%"), width=3),
                dbc.Col(_kpi_box("Average ticket", "liq-kpi-ticket", "MXN mn"), width=3),
                dbc.Col(_kpi_box("Average number of trades", "liq-kpi-trades", "trades/day"), width=3),
            ],
            style={"marginBottom": "14px"},
        ),

        html.H4("Liquidity score", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(
                    _chart_card(
                        "liq-dl-ranking-btn",
                        "liq-dl-ranking",
                        "liq-ranking",
                        "Ranking cross-section de emisiones vigentes. El Liquidity Score combina percentiles de volumen, turnover, número de operaciones y ticket promedio. Un score mayor indica mayor liquidez relativa dentro del mercado y periodo seleccionados.",
                        "Liquidity Score = 0.25×Pctl(Volume) + 0.25×Pctl(Turnover) + 0.25×Pctl(Trades) + 0.25×Pctl(Ticket)",
                    ),
                    width=6,
                ),
                dbc.Col(
                    _chart_card(
                        "liq-dl-momentum-btn",
                        "liq-dl-momentum",
                        "liq-momentum",
                        "Compara el nivel de liquidez actual con la ventana inmediatamente anterior de igual longitud. Arriba de cero = mejora relativa; abajo de cero = deterioro relativo.",
                        "Liquidity Momentum = Liquidity Score(t) − Liquidity Score(t−1 ventana)",
                    ),
                    width=6,
                ),
            ],
            style={"marginBottom": "14px"},
        ),

        html.H4("Liquidity through time", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Métrica del heatmap"),
                        dcc.Dropdown(
                            id="liq-heat-metric",
                            value="Liquidity Score",
                            clearable=False,
                            options=[
                                {"label": METRIC_LABELS[x], "value": x}
                                for x in [
                                    "Liquidity Score",
                                    "Volumen",
                                    "Turnover",
                                    "Total N Operaciones",
                                    "Ticket",
                                ]
                            ],
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        html.Label("Media móvil"),
                        dcc.Dropdown(
                            id="liq-rolling",
                            value=30,
                            clearable=False,
                            options=[
                                {"label": "5 observaciones", "value": 5},
                                {"label": "20 observaciones", "value": 20},
                                {"label": "30 observaciones", "value": 30},
                                {"label": "60 observaciones", "value": 60},
                            ],
                        ),
                    ],
                    width=3,
                ),
            ],
            style={"marginBottom": "10px"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    _chart_card(
                        "liq-dl-heat-btn",
                        "liq-dl-heat",
                        "liq-heatmap",
                        "Mapa temporal de liquidez por emisión. Para Liquidity Score, cada fecha compara cada bono contra el resto de la curva usando las métricas suavizadas por la media móvil seleccionada.",
                        "Score(d,b) = mean[Pctl(Volume), Pctl(Turnover), Pctl(Trades), Pctl(Ticket)]",
                    ),
                    width=12,
                )
            ],
            style={"marginBottom": "16px"},
        ),

        html.H4("Investor flows", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(
                    _chart_card(
                        "liq-dl-cum-btn",
                        "liq-dl-cum",
                        "liq-cumulative",
                        "Compras netas acumuladas por emisión para el participante seleccionado. Se muestran todas las emisiones del mercado. Cuando Participante = Total, el flujo suma Siefores, Soc Inversion, Otros Nac. y Res. Exterior; Interbancaria se excluye de los análisis de flujos en esta página.",
                        "Cumulative Flow_b(t) = Σ Net Purchases_b(i), i ≤ t",
                    ),
                    width=12,
                ),
            ],
            style={"marginBottom": "14px"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    _chart_card(
                        "liq-dl-investor-heat-btn",
                        "liq-dl-investor-heat",
                        "liq-investor-heat",
                        "Heatmap de compras netas acumuladas por tipo de inversionista y emisión durante la ventana seleccionada. Interbancaria se excluye para concentrar el análisis en flujos de inversionistas finales; valores positivos y negativos siguen la convención de compras netas de la base.",
                        "Net Flow(investor,bond) = Σ Net Purchases durante la ventana",
                    ),
                    width=12,
                ),
            ],
            style={"marginBottom": "14px"},
        ),

        html.H4("Liquidity × Flow", style={"color": BBVA_BLUE, "fontWeight": "bold"}),

        dbc.Row(
            [
                dbc.Col(
                    _chart_card(
                        "liq-dl-flowliq-btn",
                        "liq-dl-flowliq",
                        "liq-flow-liquidity",
                        "Relaciona el Liquidity Score de cada bono con las compras netas del participante seleccionado. El tamaño de la burbuja aproxima el monto en circulación cuando está disponible.",
                        "x = Liquidity Score; y = Σ Net Purchases; bubble size ≈ Outstanding",
                    ),
                    width=12,
                ),
            ]
        ),

        dcc.Store(id="liq-store-ranking"),
        dcc.Store(id="liq-store-momentum"),
        dcc.Store(id="liq-store-heat"),
        dcc.Store(id="liq-store-cumulative"),
        dcc.Store(id="liq-store-investor-heat"),
        dcc.Store(id="liq-store-flowliq"),
    ],
    style={"fontFamily": "Arial", "backgroundColor": "white"},
)


def _bar_ranking(data: pd.DataFrame, market: str):
    if data is None or data.empty:
        return empty_fig("Liquidity Score")

    p = data.sort_values("Liquidity Score").tail(20)

    fig = go.Figure(
        go.Bar(
            x=p["Liquidity Score"],
            y=p["Emisión"],
            orientation="h",
            marker_color=BBVA_COLORS[0],
            customdata=np.column_stack(
                [
                    p["Avg_Volume"],
                    p["Avg_Turnover"],
                    p["Avg_Trades"],
                    p["Avg_Ticket"],
                ]
            ),
            hovertemplate=(
                "Bond: %{y}<br>"
                "Liquidity Score: %{x:.1f}<br>"
                "Avg volume: %{customdata[0]:,.2f}<br>"
                "Avg turnover: %{customdata[1]:,.3f}%<br>"
                "Avg trades: %{customdata[2]:,.1f}<br>"
                "Avg ticket: %{customdata[3]:,.2f}"
                "<extra></extra>"
            ),
        )
    )
    fig = apply_layout(
        fig,
        f"{MARKET_LABELS.get(market, market)} | Liquidity Score ranking",
        "Liquidity Score (0-100)",
        "Bond",
    )
    fig.update_xaxes(range=[0, 100])
    return fig


def _momentum_fig(data: pd.DataFrame, market: str):
    if data is None or data.empty:
        return empty_fig("Liquidity momentum")

    p = data.dropna(subset=["Liquidity Score", "Score Change"]).copy()
    if p.empty:
        return empty_fig("Liquidity momentum")

    size_raw = pd.to_numeric(p["Outstanding"], errors="coerce").fillna(0).clip(lower=0)
    if size_raw.max() > 0:
        sizes = 10 + 35 * np.sqrt(size_raw / size_raw.max())
    else:
        sizes = np.repeat(16, len(p))

    colors = np.where(p["Score Change"] >= 0, "#2DCCCD", "#B00028")

    fig = go.Figure(
        go.Scatter(
            x=p["Liquidity Score"],
            y=p["Score Change"],
            text=p["Emisión"],
            mode="markers+text",
            textposition="top center",
            marker=dict(size=sizes, color=colors, opacity=0.80, line=dict(width=1, color="white")),
            customdata=np.column_stack([p["Previous Score"], p["Avg_Volume"], p["Avg_Turnover"]]),
            hovertemplate=(
                "Bond: %{text}<br>"
                "Current score: %{x:.1f}<br>"
                "Change: %{y:+.1f}<br>"
                "Previous score: %{customdata[0]:.1f}<br>"
                "Avg volume: %{customdata[1]:,.2f}<br>"
                "Avg turnover: %{customdata[2]:,.3f}%"
                "<extra></extra>"
            ),
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color=BBVA_GREY)
    fig.add_vline(x=50, line_dash="dot", line_color=BBVA_GREY)
    fig = apply_layout(
        fig,
        f"{MARKET_LABELS.get(market, market)} | Liquidity momentum",
        "Change in Liquidity Score",
        "Current Liquidity Score",
    )
    return fig


def _heatmap_fig(data: pd.DataFrame, metric: str, rolling_days: int, market: str):
    if data is None or data.empty:
        return empty_fig("Liquidity heatmap")

    p = data.copy()
    pivot = p.pivot_table(index="Emisión", columns="Día", values="Value", aggfunc="mean")
    pivot = pivot.dropna(how="all")
    if pivot.empty:
        return empty_fig("Liquidity heatmap")

    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index.astype(str),
            colorscale=[
                [0.00, "#F9D6D5"],
                [0.50, "#FFF4BF"],
                [1.00, "#2DCCCD"],
            ],
            colorbar=dict(title=METRIC_LABELS.get(metric, metric)),
            hovertemplate=(
                "Date: %{x|%Y-%m-%d}<br>"
                "Bond: %{y}<br>"
                "Value: %{z:,.2f}"
                "<extra></extra>"
            ),
        )
    )
    fig = apply_layout(
        fig,
        f"{MARKET_LABELS.get(market, market)} | {METRIC_LABELS.get(metric, metric)} heatmap ({rolling_days} obs. MA)",
        METRIC_LABELS.get(metric, metric),
        "Date",
    )
    fig.update_layout(height=max(520, 24 * len(pivot.index) + 180))
    return fig


def _flow_line_fig(data: pd.DataFrame, value_col: str, title: str, ytitle: str):
    if data is None or data.empty:
        return empty_fig(title)

    p = data.copy()
    # Se muestran todas las emisiones. El orden usa la actividad absoluta
    # para que las series más relevantes aparezcan primero en la leyenda.
    bonds = (
        p.groupby("Emisión")["Daily Flow"]
        .apply(lambda x: x.abs().sum())
        .sort_values(ascending=False)
        .index.tolist()
    )

    fig = go.Figure()
    for i, bond in enumerate(bonds):
        q = p[p["Emisión"] == bond].sort_values("Día")
        fig.add_trace(
            go.Scatter(
                x=q["Día"],
                y=q[value_col],
                mode="lines",
                name=str(bond),
                line=dict(color=BBVA_COLORS[i % len(BBVA_COLORS)], width=2),
            )
        )

    fig.add_hline(y=0, line_dash="dot", line_color=BBVA_GREY)
    fig = apply_layout(fig, title, ytitle, "Date")
    fig.update_layout(
        height=650,
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
        margin=dict(l=60, r=30, t=70, b=150),
    )
    return fig


def _investor_heat_fig(data: pd.DataFrame, market: str, flow_unit: str):
    if data is None or data.empty:
        return empty_fig("Investor × bond flows")

    p = data.copy()

    # Conservamos hasta 20 emisiones con actividad para mantener legibilidad,
    # pero el eje X se ordena por vencimiento (menor a mayor plazo), no por flujo.
    totals = p.groupby("Emisión")["Net Flow"].apply(lambda s: s.abs().sum()).sort_values(ascending=False)
    active_bonds = totals.head(20).index.tolist()
    p = p[p["Emisión"].isin(active_bonds)].copy()

    if "Maturity" in p.columns:
        maturity_order = (
            p[["Emisión", "Maturity"]]
            .drop_duplicates(subset=["Emisión"])
            .assign(Maturity=lambda x: pd.to_datetime(x["Maturity"], errors="coerce"))
            .sort_values(["Maturity", "Emisión"], na_position="last")
        )
        bonds = maturity_order["Emisión"].tolist()
    else:
        bonds = sorted(active_bonds)

    piv = p.pivot_table(
        index="Tipo de Contraparte",
        columns="Emisión",
        values="Net Flow",
        aggfunc="sum",
        fill_value=0,
    )
    piv = piv.reindex(columns=bonds)

    vmax = float(np.nanmax(np.abs(piv.values))) if piv.size else 1.0
    if not np.isfinite(vmax) or vmax == 0:
        vmax = 1.0

    fig = go.Figure(
        go.Heatmap(
            z=piv.values,
            x=piv.columns,
            y=piv.index,
            zmid=0,
            zmin=-vmax,
            zmax=vmax,
            colorscale=[
                [0.0, "#B00028"],
                [0.5, "#FFFFFF"],
                [1.0, "#2DCCCD"],
            ],
            colorbar=dict(title="Net Flow"),
            hovertemplate=(
                "Investor: %{y}<br>"
                "Bond: %{x}<br>"
                "Net flow: %{z:,.2f}"
                "<extra></extra>"
            ),
        )
    )
    return apply_layout(
        fig,
        f"{MARKET_LABELS.get(market, market)} | Investor × bond net flows ({flow_unit})",
        f"Net purchases ({flow_unit})",
        "Bond",
    )


def _flow_liq_fig(data: pd.DataFrame, market: str, participant: str, flow_unit: str):
    if data is None or data.empty:
        return empty_fig("Flow × Liquidity")

    p = data.dropna(subset=["Liquidity Score", "Net Flow"]).copy()
    if p.empty:
        return empty_fig("Flow × Liquidity")

    s = pd.to_numeric(p["Bubble Size"], errors="coerce").fillna(0).clip(lower=0)
    sizes = 12 + (42 * np.sqrt(s / s.max()) if s.max() > 0 else 12)

    fig = go.Figure(
        go.Scatter(
            x=p["Liquidity Score"],
            y=p["Net Flow"],
            text=p["Emisión"],
            mode="markers+text",
            textposition="top center",
            marker=dict(
                size=sizes,
                color=p["Liquidity Score"],
                colorscale=[[0, "#85C8FF"], [1, "#001391"]],
                showscale=True,
                colorbar=dict(title="Liquidity Score"),
                opacity=0.82,
                line=dict(width=1, color="white"),
            ),
            customdata=np.column_stack([p["Avg_Volume"], p["Avg_Turnover"], p["Outstanding"]]),
            hovertemplate=(
                "Bond: %{text}<br>"
                "Liquidity Score: %{x:.1f}<br>"
                "Net flow: %{y:,.2f}<br>"
                "Avg volume: %{customdata[0]:,.2f}<br>"
                "Avg turnover: %{customdata[1]:,.3f}%<br>"
                "Outstanding: %{customdata[2]:,.0f}"
                "<extra></extra>"
            ),
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color=BBVA_GREY)
    fig.add_vline(x=50, line_dash="dot", line_color=BBVA_GREY)
    return apply_layout(
        fig,
        f"{MARKET_LABELS.get(market, market)} | Flow × Liquidity | {participant}",
        f"Net purchases ({flow_unit})",
        "Liquidity Score (0-100)",
    )


@callback(
    Output("liq-ranking", "figure"),
    Output("liq-momentum", "figure"),
    Output("liq-heatmap", "figure"),
    Output("liq-cumulative", "figure"),
    Output("liq-investor-heat", "figure"),
    Output("liq-flow-liquidity", "figure"),
    Output("liq-kpi-volume", "children"),
    Output("liq-kpi-turnover", "children"),
    Output("liq-kpi-ticket", "children"),
    Output("liq-kpi-trades", "children"),
    Output("liq-store-ranking", "data"),
    Output("liq-store-momentum", "data"),
    Output("liq-store-heat", "data"),
    Output("liq-store-cumulative", "data"),
    Output("liq-store-investor-heat", "data"),
    Output("liq-store-flowliq", "data"),
    Input("liq-run", "n_clicks"),
    State("liq-market", "value"),
    State("liq-end-date", "date"),
    State("liq-window", "value"),
    State("liq-participant", "value"),
    State("liq-flow-unit", "value"),
    State("liq-heat-metric", "value"),
    State("liq-rolling", "value"),
    prevent_initial_call=True,
)
def update_liquidity_page(
    n_clicks,
    market,
    end_date,
    window_days,
    participant,
    flow_unit,
    heat_metric,
    rolling_days,
):
    if not n_clicks:
        raise PreventUpdate

    end = pd.to_datetime(end_date)
    start = end - pd.Timedelta(days=int(window_days))

    ranking = liquidity_snapshot(_df, market, start, end)
    momentum = liquidity_momentum(_df, market, end, int(window_days))
    heat = liquidity_heatmap_data(
        _df,
        market,
        end,
        int(window_days),
        heat_metric,
        int(rolling_days),
    )
    flows = participant_flow_series(
        _df,
        market,
        participant,
        end,
        int(window_days),
        flow_unit,
        int(rolling_days),
    )
    inv_heat = investor_bond_heatmap(
        _df,
        market,
        end,
        int(window_days),
        flow_unit,
    )
    flowliq = flow_liquidity_data(
        _df,
        market,
        participant,
        end,
        int(window_days),
        flow_unit,
    )
    kpis = market_kpis(_df, market, end, int(window_days))

    unit_label = "USD mn" if flow_unit == "USD" else "DV01 USDk"

    cumulative_fig = _flow_line_fig(
        flows,
        "Cumulative",
        f"{MARKET_LABELS.get(market, market)} | Cumulative net purchases | {participant}",
        unit_label,
    )
    kv = kpis.iloc[0] if not kpis.empty else pd.Series(dtype=float)

    return (
        _bar_ranking(ranking, market),
        _momentum_fig(momentum, market),
        _heatmap_fig(heat, heat_metric, int(rolling_days), market),
        cumulative_fig,
        _investor_heat_fig(inv_heat, market, flow_unit),
        _flow_liq_fig(flowliq, market, participant, flow_unit),
        f"{kv.get('Average daily volume', np.nan):,.1f}" if pd.notna(kv.get("Average daily volume")) else "-",
        f"{kv.get('Average turnover', np.nan):,.3f}" if pd.notna(kv.get("Average turnover")) else "-",
        f"{kv.get('Average ticket', np.nan):,.2f}" if pd.notna(kv.get("Average ticket")) else "-",
        f"{kv.get('Average trades', np.nan):,.1f}" if pd.notna(kv.get("Average trades")) else "-",
        safe_records(ranking),
        safe_records(momentum),
        safe_records(heat),
        safe_records(flows[["Día", "Emisión", "Daily Flow", "Cumulative"]] if not flows.empty else flows),
        safe_records(inv_heat),
        safe_records(flowliq),
    )


def _send(records, filename):
    df = pd.DataFrame(records or [])
    return dcc.send_data_frame(
        df.to_excel,
        filename,
        index=False,
        sheet_name="Datos",
    )


@callback(
    Output("liq-dl-ranking", "data"),
    Input("liq-dl-ranking-btn", "n_clicks"),
    State("liq-store-ranking", "data"),
    prevent_initial_call=True,
)
def dl_ranking(n, data):
    return _send(data, "liquidity_score_ranking.xlsx")


@callback(
    Output("liq-dl-momentum", "data"),
    Input("liq-dl-momentum-btn", "n_clicks"),
    State("liq-store-momentum", "data"),
    prevent_initial_call=True,
)
def dl_momentum(n, data):
    return _send(data, "liquidity_momentum.xlsx")


@callback(
    Output("liq-dl-heat", "data"),
    Input("liq-dl-heat-btn", "n_clicks"),
    State("liq-store-heat", "data"),
    prevent_initial_call=True,
)
def dl_heat(n, data):
    return _send(data, "liquidity_heatmap.xlsx")


@callback(
    Output("liq-dl-cum", "data"),
    Input("liq-dl-cum-btn", "n_clicks"),
    State("liq-store-cumulative", "data"),
    prevent_initial_call=True,
)
def dl_cumulative(n, data):
    return _send(data, "cumulative_net_purchases.xlsx")


@callback(
    Output("liq-dl-investor-heat", "data"),
    Input("liq-dl-investor-heat-btn", "n_clicks"),
    State("liq-store-investor-heat", "data"),
    prevent_initial_call=True,
)
def dl_investor_heat(n, data):
    return _send(data, "investor_bond_flow_heatmap.xlsx")


@callback(
    Output("liq-dl-flowliq", "data"),
    Input("liq-dl-flowliq-btn", "n_clicks"),
    State("liq-store-flowliq", "data"),
    prevent_initial_call=True,
)
def dl_flowliq(n, data):
    return _send(data, "flow_liquidity_matrix.xlsx")
