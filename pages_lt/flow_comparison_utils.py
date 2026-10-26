# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from pages_lt.holdings_utils import monthly_flows
from pages_lt.ui_utils import BBVA_BLUE, BBVA_GREY, empty_fig, apply_layout


COMPARISON_PARTICIPANTS = [
    "Siefores",
    "Fondos de inversión",
    "Otros inversionistas locales",
    "Inversionistas extranjeros",
    "Total",
]

# Base_M usa estas etiquetas. Interbancaria se excluye deliberadamente.
NET_PURCHASES_PARTICIPANT_MAP = {
    "Siefores": ["Siefores"],
    "Fondos de inversión": ["Soc Inversion"],
    "Otros inversionistas locales": ["Otros Nac."],
    "Inversionistas extranjeros": ["Res. Exterior"],
    "Total": ["Siefores", "Soc Inversion", "Otros Nac.", "Res. Exterior"],
}

HOLDINGS_PARTICIPANT_MAP = {
    "Siefores": ["Siefores"],
    "Fondos de inversión": ["Fondos de inversión"],
    "Otros inversionistas locales": ["Otros inversionistas locales"],
    "Inversionistas extranjeros": ["Inversionistas extranjeros"],
    "Total": [
        "Siefores",
        "Fondos de inversión",
        "Otros inversionistas locales",
        "Inversionistas extranjeros",
    ],
}

COMPARISON_INSTRUMENTS = [
    "MBonos",
    "Udibonos",
    "Total comparable (MBonos + Udibonos)",
]

NET_PURCHASES_MARKET_MAP = {
    "MBonos": ["BONOTF"],
    "Udibonos": ["UDIBONOS"],
    "Total comparable (MBonos + Udibonos)": ["BONOTF", "UDIBONOS"],
}

HOLDINGS_INSTRUMENT_MAP = {
    "MBonos": ["MBonos"],
    "Udibonos": ["Udibonos"],
    "Total comparable (MBonos + Udibonos)": ["MBonos", "Udibonos"],
}


def comparison_date_bounds(trades_df: pd.DataFrame):
    hmins, hmaxs = [], []
    # monthly_flows ya carga la base de tenencias; tomamos sus fechas de ambas
    # familias para no acoplar este módulo a variables globales internas.
    for inst in ("MBonos", "Udibonos"):
        f = monthly_flows(inst, breakdown="summary")
        if not f.empty:
            hmins.append(pd.to_datetime(f["Date"], errors="coerce").min())
            hmaxs.append(pd.to_datetime(f["Date"], errors="coerce").max())

    tdates = pd.to_datetime(trades_df.get("Día"), errors="coerce")
    tmin, tmax = tdates.min(), tdates.max()
    hmin = min(hmins) if hmins else tmin
    hmax = max(hmaxs) if hmaxs else tmax
    start = max(x for x in [hmin, tmin] if pd.notna(x))
    end = min(x for x in [hmax, tmax] if pd.notna(x))
    return pd.Timestamp(start), pd.Timestamp(end)


def _holdings_monthly(instrument: str, participant: str, end_date) -> pd.DataFrame:
    frames = []
    wanted = HOLDINGS_PARTICIPANT_MAP[participant]

    for inst in HOLDINGS_INSTRUMENT_MAP[instrument]:
        f = monthly_flows(inst, as_of=end_date, total_mode="display", breakdown="summary")
        if f.empty:
            continue
        f = f[f["Participant"].isin(wanted)].copy()
        f["Month"] = pd.to_datetime(f["Date"], errors="coerce").dt.to_period("M")
        frames.append(f[["Month", "Monthly Flow USD bn"]])

    if not frames:
        return pd.DataFrame(columns=["Month", "Cambio de tenencia USD bn"])

    out = pd.concat(frames, ignore_index=True)
    out = (
        out.groupby("Month", as_index=False)["Monthly Flow USD bn"]
        .sum(min_count=1)
        .rename(columns={"Monthly Flow USD bn": "Cambio de tenencia USD bn"})
    )
    return out


def _net_purchases_monthly(
    trades_df: pd.DataFrame,
    instrument: str,
    participant: str,
    end_date,
) -> pd.DataFrame:
    d = trades_df.copy()
    d["Día"] = pd.to_datetime(d["Día"], errors="coerce")
    d = d[d["Día"] <= pd.to_datetime(end_date)]
    d = d[
        d["Tipo"].isin(NET_PURCHASES_MARKET_MAP[instrument])
        & d["Tipo de Contraparte"].isin(NET_PURCHASES_PARTICIPANT_MAP[participant])
    ].copy()

    if d.empty:
        return pd.DataFrame(columns=["Month", "Net Purchases USD bn"])

    d["Month"] = d["Día"].dt.to_period("M")
    d["Compras netas USD"] = pd.to_numeric(d["Compras netas USD"], errors="coerce")
    out = (
        d.groupby("Month", as_index=False)["Compras netas USD"]
        .sum(min_count=1)
        .rename(columns={"Compras netas USD": "Net Purchases USD mn"})
    )
    # Las páginas de Net Purchases expresan esta columna en USD mn.
    out["Net Purchases USD bn"] = out["Net Purchases USD mn"] / 1000.0
    return out[["Month", "Net Purchases USD bn"]]


def comparison_frame(
    trades_df: pd.DataFrame,
    instrument: str,
    participant: str,
    start_date,
    end_date,
) -> pd.DataFrame:
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    h = _holdings_monthly(instrument, participant, end)
    n = _net_purchases_monthly(trades_df, instrument, participant, end)
    out = h.merge(n, on="Month", how="outer").sort_values("Month")

    if out.empty:
        return pd.DataFrame(columns=[
            "Fecha", "Cambio de tenencia USD bn", "Net Purchases USD bn",
            "Brecha USD bn", "Cambio de tenencia acumulado USD bn",
            "Net Purchases acumulado USD bn",
        ])

    out["Fecha"] = out["Month"].dt.to_timestamp("M")
    out = out[(out["Fecha"] >= start) & (out["Fecha"] <= end)].copy()

    out["Brecha USD bn"] = out["Cambio de tenencia USD bn"] - out["Net Purchases USD bn"]
    out["Cambio de tenencia acumulado USD bn"] = out["Cambio de tenencia USD bn"].fillna(0).cumsum()
    out["Net Purchases acumulado USD bn"] = out["Net Purchases USD bn"].fillna(0).cumsum()
    return out.drop(columns="Month").reset_index(drop=True)


def comparison_stats(data: pd.DataFrame) -> dict:
    if data is None or data.empty:
        return {"holdings": np.nan, "netp": np.nan, "gap": np.nan, "corr": np.nan}
    h = pd.to_numeric(data["Cambio de tenencia USD bn"], errors="coerce")
    n = pd.to_numeric(data["Net Purchases USD bn"], errors="coerce")
    valid = h.notna() & n.notna()
    corr = h[valid].corr(n[valid]) if valid.sum() >= 2 else np.nan
    hs, ns = h.sum(min_count=1), n.sum(min_count=1)
    return {
        "holdings": hs,
        "netp": ns,
        "gap": hs - ns if pd.notna(hs) and pd.notna(ns) else np.nan,
        "corr": corr,
    }


def monthly_comparison_fig(data: pd.DataFrame, instrument: str, participant: str):
    title = f"{instrument} | {participant} | Flujo mensual"
    if data is None or data.empty:
        return empty_fig(title)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data["Fecha"], y=data["Cambio de tenencia USD bn"],
        name="Cambio de tenencia", marker_color="#2DCCCD",
        hovertemplate="%{x|%b-%Y}<br>Cambio de tenencia: %{y:,.2f} USD bn<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=data["Fecha"], y=data["Net Purchases USD bn"],
        name="Net Purchases", marker_color=BBVA_BLUE,
        hovertemplate="%{x|%b-%Y}<br>Net Purchases: %{y:,.2f} USD bn<extra></extra>",
    ))
    fig.add_hline(y=0, line_width=1.2, line_color=BBVA_GREY)
    fig.update_layout(barmode="group", bargap=0.18, bargroupgap=0.06)
    fig = apply_layout(fig, title, "Flujo (USD bn)", "Fecha")
    fig.update_layout(height=470, legend=dict(orientation="h", y=1.02, x=0))
    return fig


def cumulative_comparison_fig(data: pd.DataFrame, instrument: str, participant: str):
    title = f"{instrument} | {participant} | Flujo acumulado en el periodo"
    if data is None or data.empty:
        return empty_fig(title)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["Fecha"], y=data["Cambio de tenencia acumulado USD bn"],
        mode="lines", name="Cambio de tenencia acumulado",
        line=dict(color="#2DCCCD", width=3),
        hovertemplate="%{x|%b-%Y}<br>Cambio acumulado: %{y:,.2f} USD bn<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=data["Fecha"], y=data["Net Purchases acumulado USD bn"],
        mode="lines", name="Net Purchases acumulado",
        line=dict(color=BBVA_BLUE, width=3),
        hovertemplate="%{x|%b-%Y}<br>Net Purchases acumulado: %{y:,.2f} USD bn<extra></extra>",
    ))
    fig.add_hline(y=0, line_width=1.2, line_color=BBVA_GREY)
    fig = apply_layout(fig, title, "Flujo acumulado (USD bn)", "Fecha")
    fig.update_layout(height=470, legend=dict(orientation="h", y=1.02, x=0))
    return fig
