# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from pages_lt.ui_utils import BBVA_BLUE, BBVA_COLORS, empty_fig, apply_layout


FLOW_MAP = {
    "USD": ("Compras netas USD", "USD mn"),
    "DV01": ("ComprasnetasnominalDV01", "DV01 USDk"),
}


def prepare_base(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Día"] = pd.to_datetime(out["Día"], errors="coerce")
    if "Mensual" not in out.columns:
        out["Mensual"] = out["Día"].dt.to_period("M").dt.to_timestamp()
    else:
        out["Mensual"] = pd.to_datetime(out["Mensual"], errors="coerce")
    if "Anual" not in out.columns:
        out["Anual"] = out["Día"].dt.year
    out["Anual"] = pd.to_numeric(out["Anual"], errors="coerce")

    for c in ["Compras netas USD", "ComprasnetasnominalDV01"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def participants(df: pd.DataFrame, market: str):
    d = df[(df["Tipo"] == market) & (df["Tipo de Contraparte"] != "Total")]
    preferred = ["Siefores", "Soc Inversion", "Otros Nac.", "Res. Exterior", "Interbancaria"]
    vals = [x for x in preferred if x in d["Tipo de Contraparte"].dropna().unique()]
    return vals


def bonds(df: pd.DataFrame, market: str):
    d = df[df["Tipo"] == market].copy()
    if "Vencimiento" in d.columns:
        d["Vencimiento"] = pd.to_datetime(d["Vencimiento"], errors="coerce")
        latest = d["Día"].max()
        d = d[(d["Vencimiento"].isna()) | (d["Vencimiento"] > latest)]
        order = (
            d[["Emisión", "Vencimiento"]]
            .drop_duplicates()
            .sort_values(["Vencimiento", "Emisión"])["Emisión"]
            .astype(str)
            .tolist()
        )
    else:
        order = sorted(d["Emisión"].dropna().astype(str).unique().tolist())
    return order + ["Total"]


def _filter(df, market, participant, start=None, end=None):
    mask = (
        (df["Tipo"] == market)
        & (df["Tipo de Contraparte"] == participant)
    )
    if start is not None:
        mask &= df["Día"] >= pd.to_datetime(start)
    if end is not None:
        mask &= df["Día"] <= pd.to_datetime(end)
    return df.loc[mask].copy()


def by_instrument(df, market, participant, start, end, unit):
    """Net purchases por emisión ordenadas por vencimiento.

    El dashboard anterior ordenaba por magnitud absoluta del flujo. Para que la
    gráfica se lea como una curva de bonos, ahora conserva el orden cronológico
    de vencimientos (corto -> largo).
    """
    col, _ = FLOW_MAP[unit]
    d = _filter(df, market, participant, start, end)
    if d.empty:
        return pd.DataFrame(columns=["Emisión", "Vencimiento", "Net Flow"])

    out = (
        d.groupby("Emisión", as_index=False)[col]
        .sum()
        .rename(columns={col: "Net Flow"})
    )

    if "Vencimiento" in d.columns:
        maturity = (
            d[["Emisión", "Vencimiento"]]
            .assign(Vencimiento=lambda x: pd.to_datetime(x["Vencimiento"], errors="coerce"))
            .groupby("Emisión", as_index=False)["Vencimiento"]
            .max()
        )
        out = out.merge(maturity, on="Emisión", how="left")
        out = out.sort_values(["Vencimiento", "Emisión"], na_position="last")
    else:
        out["Vencimiento"] = pd.NaT
        out = out.sort_values("Emisión")

    return out.reset_index(drop=True)


def monthly_flow(df, market, participant, tenor, start, end, unit):
    col, _ = FLOW_MAP[unit]
    d = _filter(df, market, participant, start, end)
    if d.empty:
        return pd.DataFrame(columns=["Mensual", "Net Flow"])

    if tenor != "Total":
        d = d[d["Emisión"] == tenor]

    out = (
        d.groupby("Mensual", as_index=False)[col]
        .sum()
        .rename(columns={col: "Net Flow"})
        .sort_values("Mensual")
    )
    return out


def annual_flow(df, market, participant, tenor, start_year, end_year, unit):
    col, _ = FLOW_MAP[unit]
    d = df[
        (df["Tipo"] == market)
        & (df["Tipo de Contraparte"] == participant)
        & (df["Anual"] >= start_year)
        & (df["Anual"] <= end_year)
    ].copy()

    if tenor != "Total":
        d = d[d["Emisión"] == tenor]

    if d.empty:
        return pd.DataFrame(columns=["Anual", "Net Flow"])

    return (
        d.groupby("Anual", as_index=False)[col]
        .sum()
        .rename(columns={col: "Net Flow"})
        .sort_values("Anual")
    )


def cumulative_flow(df, market, participant, tenor, start, end, unit):
    col, _ = FLOW_MAP[unit]
    d = _filter(df, market, participant, start, end)

    if tenor != "Total":
        d = d[d["Emisión"] == tenor]

    if d.empty:
        return pd.DataFrame(columns=["Día", "Daily Flow", "Cumulative Flow"])

    out = (
        d.groupby("Día", as_index=False)[col]
        .sum()
        .rename(columns={col: "Daily Flow"})
        .sort_values("Día")
    )
    out["Cumulative Flow"] = out["Daily Flow"].cumsum()
    return out


def flow_bar_fig(data, title, unit_label, horizontal=False):
    if data is None or data.empty:
        return empty_fig(title)

    fig = go.Figure()

    if "Emisión" in data.columns:
        x = data["Net Flow"] if horizontal else data["Emisión"]
        y = data["Emisión"] if horizontal else data["Net Flow"]
        orientation = "h" if horizontal else "v"
    elif "Mensual" in data.columns:
        x, y, orientation = data["Mensual"], data["Net Flow"], "v"
    else:
        x, y, orientation = data["Anual"], data["Net Flow"], "v"

    colors = np.where(data["Net Flow"] >= 0, "#2DCCCD", "#B00028")

    fig.add_trace(
        go.Bar(
            x=x,
            y=y,
            orientation=orientation,
            marker_color=colors,
            hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>" if not horizontal else "%{y}<br>%{x:,.2f}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color="#46536D") if not horizontal else fig.add_vline(x=0, line_dash="dot", line_color="#46536D")

    return apply_layout(
        fig,
        title,
        unit_label if not horizontal else "Instrument",
        "Date / instrument" if not horizontal else unit_label,
    )


def cumulative_fig(data, title, unit_label):
    if data is None or data.empty:
        return empty_fig(title)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["Día"],
            y=data["Cumulative Flow"],
            mode="lines",
            line=dict(color=BBVA_COLORS[0], width=3),
            name="Cumulative",
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color="#46536D")
    return apply_layout(fig, title, unit_label, "Date")
