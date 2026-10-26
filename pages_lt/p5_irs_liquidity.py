# -*- coding: utf-8 -*-
"""IRS | Liquidity Tracker -- Dash page #5 with Excel exports for every view.

Place beside irs_liquidity_utils.py inside Liquidity_Tracker/pages_lt.
The IRS CSV is stored in the parent Liquidity directory, not Liquidity_Tracker.
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import os

import numpy as np
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, dcc, html, dash_table

from pages_lt.ui_utils import BBVA_BLUE, BBVA_GREY, card, page_title
from pages_lt.irs_liquidity_utils import (
    find_irs_csv, load_irs_csv, quality_events, annual_summary,
    kpis, rolling_volume_fig, investor_volume_history_fig,
    annual_instrument_share_fig, annual_investor_share_fig,
    annual_tenor_volume_fig, annual_tenor_share_fig,
    current_tenor_fig, tenor_heatmap_fig,
)

dash.register_page(__name__, path='/irs-liquidity-tracker', name='IRS | Liquidity Tracker', order=4)

# Important: pages_lt -> Liquidity_Tracker -> Liquidity (CSV directory).
_DATA_DIR = Path(os.getenv("DASHBOARD_DATA_DIR", str(Path(__file__).resolve().parents[1] / "data_files"))).expanduser()
_LOAD_ERROR = None
try:
    _IRS_PATH = find_irs_csv(_DATA_DIR)
    _IRS = load_irs_csv(_IRS_PATH)
except Exception as exc:
    _LOAD_ERROR = str(exc)
    _IRS = pd.DataFrame()

_FIGURE_IDS = [
    'irs-volume-history', 'irs-investor-history',
    'irs-instrument-share', 'irs-investor-share',
    'irs-tenor-volume', 'irs-tenor-share',
    'irs-current-tenor', 'irs-tenor-heatmap',
]
_FILE_KEYS = [
    'swaps_volume_30d_sma', 'investor_volume_30d_sma',
    'instrument_share', 'investor_share',
    'tenor_volume', 'tenor_share', 'current_tenor', 'tenor_heatmap',
    'annual_summary', 'data_quality_flags',
]


def _figures(history, sma, annual_years, tenor_years):
    """Shared chart definitions: displayed charts == exported chart data."""
    return [
        rolling_volume_fig(_IRS, sma, history),
        investor_volume_history_fig(_IRS, sma, history),
        annual_instrument_share_fig(_IRS, annual_years),
        annual_investor_share_fig(_IRS, annual_years),
        annual_tenor_volume_fig(_IRS, tenor_years),
        annual_tenor_share_fig(_IRS, tenor_years),
        current_tenor_fig(_IRS, 30),
        tenor_heatmap_fig(_IRS, min(10, annual_years)),
    ]


def _annual_table_data():
    a = annual_summary(_IRS)
    cols = ['Year', 'IRS share (%)', 'Foreign share (%)', 'Local share (%)']
    for col in cols:
        if col not in a.columns:
            a[col] = np.nan
    return a[cols].tail(16).round(2).to_dict('records')


def _graph_card(index, graph_id):
    return dbc.Col(card([
        html.Div(dbc.Button(
            'Descargar Excel', size='sm', outline=True, color='primary',
            id={'type': 'irs-excel-btn', 'index': index}, n_clicks=0,
        ), style={'textAlign': 'right', 'marginBottom': '4px'}),
        dcc.Graph(id=graph_id, config={'displaylogo': False}, style={'width': '100%'}),
    ]), lg=6, xs=12)


def _kpi(title, value, subtitle=''):
    return dbc.Col(html.Div([
        html.Div(title, style={'fontSize': '11px', 'color': BBVA_GREY}),
        html.Div(value, style={'fontSize': '24px', 'fontWeight': '700', 'color': BBVA_BLUE}),
        html.Div(subtitle, style={'fontSize': '10px', 'color': BBVA_GREY}),
    ], style={'border': '1px solid #DDE3EA', 'borderRadius': '8px', 'padding': '12px', 'height': '100%'}),
        lg=3, md=6, xs=12)


def _data_from_figure(fig) -> pd.DataFrame:
    """Export actual plotted coordinates, never an unrelated raw subset."""
    dfs = []
    for j, tr in enumerate(fig.data):
        name = tr.name or f'Series {j+1}'
        if tr.type == 'heatmap':
            z = np.asarray(tr.z, dtype=float)
            return pd.DataFrame(z, index=list(tr.y), columns=list(tr.x)).rename_axis('Tenor').reset_index()
        x = list(tr.x) if tr.x is not None else []
        y = list(tr.y) if tr.y is not None else []
        if len(x) != len(y):
            continue
        t = pd.DataFrame({'Period': x, name: y})
        if not dfs:
            dfs.append(t)
        else:
            dfs[0] = dfs[0].merge(t, on='Period', how='outer')
    return dfs[0] if dfs else pd.DataFrame()


if _LOAD_ERROR:
    layout = html.Div([
        page_title('IRS | Liquidity Tracker', 'Banxico swaps liquidity and trading activity.'),
        dbc.Alert(_LOAD_ERROR, color='danger'),
    ], style={'padding': '14px'})
else:
    qc = quality_events(_IRS)
    layout = html.Div([
        page_title('IRS | Liquidity Tracker', 'Swaps liquidity, investor participation and tenor breakdown.'),
        dbc.Row([
            dbc.Col([html.Label('History'), dcc.Dropdown(id='irs-history-years', options=[{'label': f'{x} years', 'value': x} for x in [3,5,7,10]], value=5, clearable=False)], lg=3),
            dbc.Col([html.Label('Moving average'), dcc.Dropdown(id='irs-sma', options=[{'label': f'{x} days', 'value': x} for x in [10,20,30,60]], value=30, clearable=False)], lg=3),
            dbc.Col([html.Label('Annual history'), dcc.Dropdown(id='irs-annual-years', options=[{'label': f'{x} years', 'value': x} for x in [5,10,16]], value=16, clearable=False)], lg=3),
            dbc.Col([html.Label('Tenor years'), dcc.Dropdown(id='irs-tenor-years', options=[{'label': f'{x} years', 'value': x} for x in [4,5,7,10]], value=5, clearable=False)], lg=3),
        ], class_name='g-2 mb-3'),
        dbc.Row(id='irs-kpis', class_name='g-2 mb-3'),
        html.H4('Market activity', style={'color': BBVA_BLUE}),
        dbc.Row([_graph_card(0, _FIGURE_IDS[0]), _graph_card(1, _FIGURE_IDS[1])], class_name='g-3'),
        html.H4('Market structure', style={'color': BBVA_BLUE, 'marginTop': '18px'}),
        dbc.Row([_graph_card(2, _FIGURE_IDS[2]), _graph_card(3, _FIGURE_IDS[3])], class_name='g-3'),
        html.H4('Tenor distribution', style={'color': BBVA_BLUE, 'marginTop': '18px'}),
        dbc.Row([_graph_card(4, _FIGURE_IDS[4]), _graph_card(5, _FIGURE_IDS[5])], class_name='g-3'),
        html.H4('Additional analytics', style={'color': BBVA_BLUE, 'marginTop': '18px'}),
        dbc.Row([_graph_card(6, _FIGURE_IDS[6]), _graph_card(7, _FIGURE_IDS[7])], class_name='g-3'),
        html.H4('Annual IRS metrics', style={'color': BBVA_BLUE, 'marginTop': '18px'}),
        html.Div(dbc.Button('Descargar Excel', id={'type': 'irs-excel-btn', 'index': 8}, color='primary', outline=True, size='sm'), style={'textAlign':'right'}),
        dash_table.DataTable(
            id='irs-annual-summary-table',
            columns=[{'name': c, 'id': c} for c in ['Year','IRS share (%)','Foreign share (%)','Local share (%)']],
            data=_annual_table_data(), sort_action='native', page_size=16,
            style_cell={'padding': '7px', 'textAlign': 'right', 'fontFamily': 'Arial', 'fontSize': '12px'},
            style_header={'backgroundColor': '#F7F8F8', 'fontWeight':'bold', 'color': BBVA_BLUE},
            style_table={'overflowX': 'auto'},
        ),
        html.Div([
            html.B('Data quality control: '),
            html.Span(f'{len(qc)} unusually large isolated daily values are flagged and excluded from analytical series; no values are interpolated. Original CSV unchanged.'),
            dbc.Button('Download quality log (Excel)', id={'type': 'irs-excel-btn', 'index': 9}, n_clicks=0, size='sm', outline=True, color='secondary', class_name='ms-2'),
        ], style={'fontSize': '11px', 'color': BBVA_GREY, 'marginTop': '12px'}),
        html.Div([html.B('Source: '), html.Span('Banco de México / BBVA Markets Intelligence & Strategy Unit (MISU). Market figures are in MXN mn; tenor buckets aggregate organized and OTC activity.')], style={'fontSize': '11px', 'color': BBVA_GREY, 'marginTop':'12px'}),
        dcc.Download(id='irs-excel-download'),
    ], style={'padding': '14px'})

    @callback(
        Output('irs-kpis', 'children'),
        *(Output(x, 'figure') for x in _FIGURE_IDS),
        Input('irs-history-years', 'value'), Input('irs-sma', 'value'),
        Input('irs-annual-years', 'value'), Input('irs-tenor-years', 'value'),
    )
    def update_irs(history, sma, annual_years, tenor_years):
        z = kpis(_IRS, 30)
        cards = [
            _kpi('30D avg IRS volume', f"{z['avg_irs']:,.0f}", 'MXN mn / day'),
            _kpi('IRS share', f"{z['irs_share']:.1f}%", 'of total swaps volume'),
            _kpi('Foreign share', f"{z['foreign_share']:.1f}%", 'of local + foreign activity'),
            _kpi('0-1Y tenor share', f"{z['short_share']:.1f}%", '30D average'),
        ]
        return (cards, *_figures(history, sma, annual_years, tenor_years))

    @callback(
        Output('irs-excel-download', 'data'),
        Input({'type': 'irs-excel-btn', 'index': ALL}, 'n_clicks'),
        State('irs-history-years', 'value'), State('irs-sma', 'value'),
        State('irs-annual-years', 'value'), State('irs-tenor-years', 'value'),
        prevent_initial_call=True,
    )
    def download_irs(n_clicks, history, sma, annual_years, tenor_years):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict) or triggered.get('type') != 'irs-excel-btn':
            return dash.no_update
        index = int(triggered['index'])
        if index == 8:
            data = pd.DataFrame(_annual_table_data())
        elif index == 9:
            data = quality_events(_IRS)
            if data.empty:
                data = pd.DataFrame({'Status': ['No extreme isolated spikes flagged']})
        else:
            data = _data_from_figure(_figures(history, sma, annual_years, tenor_years)[index])
        data = data.copy()
        with BytesIO() as buf:
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                data.to_excel(writer, sheet_name='Chart data', index=False)
                if index != 9:
                    log = quality_events(_IRS)
                    (log if not log.empty else pd.DataFrame({'Status':['No flags']})).to_excel(writer, sheet_name='Quality flags', index=False)
                pd.DataFrame({'Note': [
                    'Source: Banco de México; BBVA Markets Intelligence & Strategy Unit (MISU)',
                    'IRS data: cleaned only when a single extreme date meets all three conservative tests.',
                    'Original CSV is never overwritten. Quality flags give the exact excluded values.',
                ]}).to_excel(writer, sheet_name='Methodology', index=False)
            payload = buf.getvalue()
        return dcc.send_bytes(payload, f"MISU_IRS_{_FILE_KEYS[index]}.xlsx")
