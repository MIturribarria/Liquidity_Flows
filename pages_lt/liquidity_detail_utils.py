# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from pages_lt.ui_utils import BBVA_BLUE, BBVA_COLORS, empty_fig, apply_layout


MARKET_LABELS = {
    "BONOTF": "MBono",
    "UDIBONOS": "Udibono",
}

METRIC_MAP = {
    "MXN": {
        "Volume": "Volumen",
        "Ticket": "Ticket",
    },
    "DV01": {
        "Volume": "VolumenDV01",
        "Ticket": "TicketDV01",
    },
}


def prepare_liquidity_detail_base(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Día"] = pd.to_datetime(out["Día"], errors="coerce")
    out["Vencimiento"] = pd.to_datetime(out.get("Vencimiento"), errors="coerce")

    numeric_cols = [
        "Volumen",
        "VolumenDV01",
        "Ticket",
        "TicketDV01",
        "Turnover",
        "Total N Operaciones",
        "Número de Títulos en Circulación",
        "Duración",
    ]
    for c in numeric_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def active_bonds(df: pd.DataFrame, market: str, end_date=None):
    d = df[df["Tipo"] == market].copy()
    end = pd.to_datetime(end_date) if end_date is not None else d["Día"].max()

    if "Vencimiento" in d.columns:
        d = d[(d["Vencimiento"].isna()) | (d["Vencimiento"] > end)]
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


def participants(df: pd.DataFrame, market: str):
    d = df[df["Tipo"] == market]
    preferred = ["Siefores", "Soc Inversion", "Interbancaria", "Otros Nac.", "Res. Exterior", "Total"]
    vals = d["Tipo de Contraparte"].dropna().astype(str).unique().tolist()
    return [x for x in preferred if x in vals]


def _filter(df, market, participant, start, end):
    mask = (
        (df["Tipo"] == market)
        & (df["Tipo de Contraparte"] == participant)
        & (df["Día"] >= pd.to_datetime(start))
        & (df["Día"] <= pd.to_datetime(end))
    )
    return df.loc[mask].copy()


def metric_series(
    df,
    market,
    participant,
    bonds_selected,
    start,
    end,
    metric,
    terms="MXN",
    rolling_window=30,
):
    """
    Serie histórica suavizada para Volume / Ticket / Turnover.
    """
    d = _filter(df, market, participant, start, end)

    if metric == "Turnover":
        col = "Turnover"
        agg_total = "mean"
    elif metric == "Trades":
        col = "Total N Operaciones"
        agg_total = "sum"
    else:
        col = METRIC_MAP[terms][metric]
        agg_total = "sum" if metric == "Volume" else "mean"

    if d.empty or col not in d.columns:
        return pd.DataFrame()

    piv = d.pivot_table(index="Día", columns="Emisión", values=col, aggfunc="mean")
    piv = piv.sort_index()

    if agg_total == "sum":
        piv["Total"] = piv.sum(axis=1, skipna=True)
    else:
        piv["Total"] = piv.mean(axis=1, skipna=True)

    piv = piv.rolling(window=int(rolling_window), min_periods=1).mean()
    piv = piv.reset_index().rename(columns={"Día": "Date"})

    selected = bonds_selected or ["Total"]
    cols = ["Date"] + [c for c in selected if c in piv.columns]
    return piv[cols]


def annual_share(df, market):
    d = df[
        (df["Tipo"] == market)
        & (df["Tipo de Contraparte"] != "Total")
    ].copy()

    if d.empty:
        return pd.DataFrame()

    daily = (
        d.groupby(["Día", "Tipo de Contraparte"], as_index=False)["Volumen"]
        .sum()
    )
    daily["Año"] = daily["Día"].dt.year

    annual = (
        daily.groupby(["Año", "Tipo de Contraparte"], as_index=False)["Volumen"]
        .sum()
    )
    annual["Share (%)"] = (
        annual["Volumen"]
        / annual.groupby("Año")["Volumen"].transform("sum")
        * 100.0
    )
    return annual


def summary_table(df, market, participant, terms, years_back=3):
    """
    Tabla por bono con promedio de volumen, turnover y ticket para los últimos N años.
    """
    d = df[
        (df["Tipo"] == market)
        & (df["Tipo de Contraparte"] == participant)
    ].copy()

    if d.empty:
        return pd.DataFrame()

    max_year = int(d["Día"].dt.year.max())
    years = [max_year - i for i in range(years_back)]

    vol_col = METRIC_MAP[terms]["Volume"]
    ticket_col = METRIC_MAP[terms]["Ticket"]

    rows = []
    bond_order = active_bonds(df, market, d["Día"].max())

    for bond in bond_order:
        row = {"Bonds": bond}
        bd = d if bond == "Total" else d[d["Emisión"] == bond]

        for y in years:
            yd = bd[bd["Día"].dt.year == y]
            if bond == "Total":
                daily = (
                    yd.groupby("Día", as_index=False)
                    .agg(
                        Volume=(vol_col, "sum"),
                        Turnover=("Turnover", "mean"),
                        Ticket=(ticket_col, "mean"),
                    )
                )
                row[f"Average trading volume {y}"] = daily["Volume"].mean() if not daily.empty else np.nan
                row[f"Average turnover (%) {y}"] = daily["Turnover"].mean() if not daily.empty else np.nan
                row[f"Average ticket per trade {y}"] = daily["Ticket"].mean() if not daily.empty else np.nan
            else:
                row[f"Average trading volume {y}"] = yd[vol_col].mean() if not yd.empty else np.nan
                row[f"Average turnover (%) {y}"] = yd["Turnover"].mean() if not yd.empty else np.nan
                row[f"Average ticket per trade {y}"] = yd[ticket_col].mean() if not yd.empty else np.nan

        rows.append(row)

    return pd.DataFrame(rows)


def current_year_range(df, market, participant, terms, metric):
    """
    Promedio / mínimo / máximo del año más reciente por bono.
    """
    d = df[
        (df["Tipo"] == market)
        & (df["Tipo de Contraparte"] == participant)
    ].copy()

    if d.empty:
        return pd.DataFrame()

    year = int(d["Día"].dt.year.max())
    d = d[d["Día"].dt.year == year]

    if metric == "Volume":
        col = METRIC_MAP[terms]["Volume"]
    elif metric == "Ticket":
        col = METRIC_MAP[terms]["Ticket"]
    else:
        col = "Turnover"

    rows = []
    for bond in active_bonds(df, market, d["Día"].max()):
        bd = d if bond == "Total" else d[d["Emisión"] == bond]

        if bond == "Total":
            if metric == "Volume":
                s = bd.groupby("Día")[col].sum()
            else:
                s = bd.groupby("Día")[col].mean()
        else:
            s = bd[col]

        if s.empty:
            continue

        rows.append(
            {
                "Bond": bond,
                "Average": s.mean(),
                "Min": s.min(),
                "Max": s.max(),
                "Year": year,
            }
        )
    return pd.DataFrame(rows)


def line_fig(data, title, ytitle):
    if data is None or data.empty:
        return empty_fig(title)

    fig = go.Figure()
    cols = [c for c in data.columns if c != "Date"]

    for i, c in enumerate(cols):
        fig.add_trace(
            go.Scatter(
                x=data["Date"],
                y=data[c],
                mode="lines",
                name=str(c),
                line=dict(color=BBVA_COLORS[i % len(BBVA_COLORS)], width=2),
            )
        )

    return apply_layout(fig, title, ytitle, "Date")


def share_fig(data, market):
    if data is None or data.empty:
        return empty_fig("Average trading volume share")

    piv = data.pivot_table(
        index="Año",
        columns="Tipo de Contraparte",
        values="Share (%)",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    fig = go.Figure()
    for i, c in enumerate([x for x in piv.columns if x != "Año"]):
        fig.add_trace(
            go.Bar(
                x=piv["Año"],
                y=piv[c],
                name=str(c),
                marker_color=BBVA_COLORS[i % len(BBVA_COLORS)],
                text=np.round(piv[c], 1),
                textposition="inside",
            )
        )

    fig.update_layout(barmode="stack")
    return apply_layout(
        fig,
        f"{MARKET_LABELS.get(market, market)} | Average trading volume share by investor",
        "Share (%)",
        "Year",
    )


def range_fig(data, title, ytitle):
    if data is None or data.empty:
        return empty_fig(title)

    d = data.copy()
    d = d.dropna(subset=["Average", "Min", "Max"])
    if d.empty:
        return empty_fig(title)

    up = d["Max"] - d["Average"]
    down = d["Average"] - d["Min"]

    fig = go.Figure(
        go.Scatter(
            x=d["Bond"],
            y=d["Average"],
            mode="markers",
            marker=dict(color="#2DCCCD", size=8),
            error_y=dict(
                type="data",
                symmetric=False,
                array=up,
                arrayminus=down,
                color="#004481",
                thickness=2,
                width=7,
            ),
            text=d["Bond"],
            hovertemplate=(
                "Bond: %{text}<br>"
                "Average: %{y:,.3f}<br>"
                "<extra></extra>"
            ),
        )
    )

    fig = apply_layout(fig, title, ytitle, "Bond")
    fig.update_xaxes(tickangle=45)
    return fig
