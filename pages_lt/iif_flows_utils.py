# -*- coding: utf-8 -*-
"""Utilities for IIF Emerging Markets portfolio-flow analysis.

Expected workbook sheets (suffixes such as ``_nw`` are accepted):
- Total Flows
- Regional Flows
- Country Flows

Units in the IIF workbook:
- Total / Regional flows: USD billion
- Country flows: USD million (converted here to USD billion)
"""
from __future__ import annotations

from pathlib import Path
import os
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from openpyxl import load_workbook
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
IIF_DATA_DIR = Path(os.getenv(
    "IIF_DATA_DIR",
    os.getenv("DASHBOARD_DATA_DIR", str(_PROJECT_ROOT / "data_files"))
)).expanduser()


BBVA_BLUE = "#001391"
BBVA_NAVY = "#072146"
BBVA_LIGHT_BLUE = "#85C8FF"
BBVA_AQUA = "#2DCCCD"
BBVA_GREEN = "#88E783"
BBVA_GREY = "#46536D"
BBVA_MID_GREY = "#A5B3BF"
BBVA_RED = "#B00028"
BBVA_ORANGE = "#F7893B"
BBVA_PURPLE = "#8F7AE5"
BBVA_BG = "#F7F8F8"

MONTH_LABELS_EN = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

REGIONS = ["Emerging Asia", "Latin America", "Emerging Europe", "Africa & Middle East"]
FLOW_TYPES = ["Total", "Equity", "Debt"]


def _sheet_by_prefix(wb, prefix: str):
    target = prefix.strip().lower()
    for name in wb.sheetnames:
        if name.strip().lower().startswith(target):
            return wb[name]
    raise KeyError(f"Workbook does not contain a sheet beginning with '{prefix}'. Found: {wb.sheetnames}")


def _has_required_sheets(path: Path) -> bool:
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
        names = [s.strip().lower() for s in wb.sheetnames]
        return all(any(n.startswith(prefix) for n in names) for prefix in ["total flows", "regional flows", "country flows"])
    except Exception:
        return False


def find_iif_workbook(data_dir: str | Path, explicit: str | Path | None = None) -> Path:
    """Find the IIF workbook next to the dashboard data files."""
    if explicit:
        p = Path(explicit).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"IIF workbook not found: {p}")
        if not _has_required_sheets(p):
            raise ValueError(f"The selected workbook does not contain Total/Regional/Country Flows sheets: {p}")
        return p

    root = Path(data_dir).expanduser()
    preferred = root / "monthly_em_portfolio_flows_database.xlsx"
    if preferred.exists() and _has_required_sheets(preferred):
        return preferred

    candidates = sorted(list(root.glob("*.xlsx")) + list(root.glob("*.xlsm")))
    matches = [p for p in candidates if _has_required_sheets(p)]
    if not matches:
        raise FileNotFoundError(
            f"No IIF workbook with Total Flows, Regional Flows and Country Flows sheets was found in: {root}"
        )
    return matches[0]


def _numeric(value):
    if value is None:
        return np.nan
    if isinstance(value, (int, float, np.number)) and not isinstance(value, bool):
        return float(value)
    try:
        s = str(value).strip().replace(",", "")
        if not s or s.lower() in {"na", "n/a", "nan", "-"}:
            return np.nan
        return float(s)
    except Exception:
        return np.nan


def load_total_flows(path: str | Path) -> pd.DataFrame:
    """Monthly IIF headline tracker and China / ex-China decomposition, USD bn."""
    wb = load_workbook(Path(path), read_only=False, data_only=True)
    ws = _sheet_by_prefix(wb, "Total Flows")
    headers = {
        3: "Total",
        4: "Debt",
        5: "Equity",
        6: "China Equity",
        7: "EM ex-China Equity",
        8: "China Debt",
        9: "EM ex-China Debt",
    }
    rows = []
    for r in range(18, ws.max_row + 1):
        dt = ws.cell(r, 2).value
        if not isinstance(dt, (pd.Timestamp,)) and not hasattr(dt, "year"):
            continue
        rec = {"Date": pd.Timestamp(dt).to_period("M").to_timestamp()}
        for c, name in headers.items():
            rec[name] = _numeric(ws.cell(r, c).value)
        rows.append(rec)
    out = pd.DataFrame(rows).sort_values("Date").drop_duplicates("Date", keep="last")
    return out.reset_index(drop=True)


def load_regional_flows(path: str | Path) -> pd.DataFrame:
    """Regional total/equity/debt flows in long form, USD bn."""
    wb = load_workbook(Path(path), read_only=False, data_only=True)
    ws = _sheet_by_prefix(wb, "Regional Flows")
    blocks = {
        "Total": {3: "Emerging Asia", 4: "Latin America", 5: "Emerging Europe", 6: "Africa & Middle East", 7: "Total"},
        "Equity": {9: "Emerging Asia", 10: "Latin America", 11: "Emerging Europe", 12: "Africa & Middle East", 13: "Total"},
        "Debt": {15: "Emerging Asia", 16: "Latin America", 17: "Emerging Europe", 18: "Africa & Middle East", 19: "Total"},
    }
    rows = []
    for r in range(5, ws.max_row + 1):
        dt = ws.cell(r, 2).value
        if not hasattr(dt, "year"):
            continue
        dt = pd.Timestamp(dt).to_period("M").to_timestamp()
        for flow_type, cmap in blocks.items():
            for c, region in cmap.items():
                rows.append({
                    "Date": dt,
                    "Flow Type": flow_type,
                    "Region": region,
                    "Flow USD bn": _numeric(ws.cell(r, c).value),
                })
    out = pd.DataFrame(rows)
    out = out.sort_values(["Date", "Flow Type", "Region"]).reset_index(drop=True)
    return out


def load_country_flows(path: str | Path) -> pd.DataFrame:
    """Country flows in long form converted from USD mn to USD bn."""
    wb = load_workbook(Path(path), read_only=False, data_only=True)
    ws = _sheet_by_prefix(wb, "Country Flows")

    # Row 4 contains country labels, often merged over Equity/Debt columns.
    mapping = []
    current_country = None
    for c in range(2, ws.max_column + 1):
        country_cell = ws.cell(4, c).value
        if country_cell not in (None, ""):
            current_country = str(country_cell).strip()
        metric = ws.cell(5, c).value
        if metric not in (None, "") and current_country:
            metric = str(metric).strip().title()
            if metric in {"Equity", "Debt", "Portfolio"}:
                mapping.append((c, current_country, metric))

    rows = []
    for r in range(6, ws.max_row + 1):
        dt = ws.cell(r, 1).value
        if not hasattr(dt, "year"):
            continue
        dt = pd.Timestamp(dt).to_period("M").to_timestamp()
        for c, country, metric in mapping:
            value_mn = _numeric(ws.cell(r, c).value)
            rows.append({
                "Date": dt,
                "Country": country,
                "Flow Type": metric,
                "Flow USD bn": value_mn / 1000.0 if pd.notna(value_mn) else np.nan,
            })

    out = pd.DataFrame(rows)
    return out.sort_values(["Date", "Country", "Flow Type"]).reset_index(drop=True)


def load_iif_workbook(path: str | Path) -> dict[str, pd.DataFrame]:
    path = Path(path)
    return {
        "total": load_total_flows(path),
        "regional": load_regional_flows(path),
        "country": load_country_flows(path),
    }


def country_list(country_flows: pd.DataFrame, include_em: bool = True) -> list[str]:
    countries = sorted(country_flows["Country"].dropna().astype(str).unique().tolist())
    return (["EM Aggregate"] + countries) if include_em else countries


def _country_metric_series(country_flows: pd.DataFrame, country: str, metric: str) -> pd.Series:
    q = country_flows[country_flows["Country"] == country]
    s = q[q["Flow Type"] == metric].groupby("Date")["Flow USD bn"].sum(min_count=1)
    return s.sort_index()


def country_monthly(country_flows: pd.DataFrame, country: str) -> pd.DataFrame:
    """Monthly Total/Equity/Debt for a country or the EM Aggregate.

    For a country with both Equity and Debt columns, Total is only available when
    both components are available in that month. Countries reported only as
    Portfolio use that series as Total.

    EM Aggregate is the sum of all country-level Total series. Equity and Debt
    aggregate only their respective country columns. This follows the user's
    requested country-sum methodology and is intentionally different from the
    model-driven headline IIF tracker.
    """
    country = str(country)
    all_dates = pd.Index(sorted(country_flows["Date"].dropna().unique()), name="Date")

    if country == "EM Aggregate":
        # Exact country-column sum requested by the report: sum every available
        # Equity, Debt and Portfolio-only observation in Country Flows.
        def _aggregate_metric(metric: str):
            q = country_flows[country_flows["Flow Type"] == metric]
            return q.groupby("Date")["Flow USD bn"].sum(min_count=1).reindex(all_dates)

        equity = _aggregate_metric("Equity")
        debt = _aggregate_metric("Debt")
        portfolio = _aggregate_metric("Portfolio")
        total = pd.concat([equity, debt, portfolio], axis=1).sum(axis=1, min_count=1)
        out = pd.DataFrame({
            "Date": all_dates,
            "Total": total.values,
            "Equity": equity.values,
            "Debt": debt.values,
        })
        return out.sort_values("Date").reset_index(drop=True)

    q = country_flows[country_flows["Country"] == country]
    if q.empty:
        return pd.DataFrame(columns=["Date", "Total", "Equity", "Debt"])

    metrics_present = set(q["Flow Type"].dropna().unique())
    equity = _country_metric_series(country_flows, country, "Equity").reindex(all_dates)
    debt = _country_metric_series(country_flows, country, "Debt").reindex(all_dates)
    portfolio = _country_metric_series(country_flows, country, "Portfolio").reindex(all_dates)

    if "Portfolio" in metrics_present and not ({"Equity", "Debt"} & metrics_present):
        total = portfolio
    elif "Equity" in metrics_present and "Debt" in metrics_present:
        total = pd.concat([equity, debt], axis=1).sum(axis=1, min_count=2)
    elif "Equity" in metrics_present:
        total = equity.copy()
    elif "Debt" in metrics_present:
        total = debt.copy()
    else:
        total = portfolio.copy()

    out = pd.DataFrame({
        "Date": all_dates,
        "Total": total.values,
        "Equity": equity.values,
        "Debt": debt.values,
    })
    # Drop dates where this country has no information at all.
    out = out.dropna(subset=["Total", "Equity", "Debt"], how="all")
    return out.sort_values("Date").reset_index(drop=True)


def annual_cumulative_profile(
    monthly: pd.DataFrame,
    metric: str,
    display_years: int = 4,
    average_years: int = 5,
) -> pd.DataFrame:
    if monthly is None or monthly.empty or metric not in monthly.columns:
        return pd.DataFrame(columns=["Month", "Year", "Series", "Value"])
    q = monthly[["Date", metric]].copy()
    q["Date"] = pd.to_datetime(q["Date"], errors="coerce")
    q[metric] = pd.to_numeric(q[metric], errors="coerce")
    q = q.dropna(subset=["Date", metric]).sort_values("Date")
    if q.empty:
        return pd.DataFrame(columns=["Month", "Year", "Series", "Value"])

    q["Year"] = q["Date"].dt.year
    q["Month"] = q["Date"].dt.month
    q["Value"] = q.groupby("Year")[metric].cumsum()
    current_year = int(q["Year"].max())
    shown_years = list(range(current_year - int(display_years) + 1, current_year + 1))
    avg_years = list(range(current_year - int(average_years) + 1, current_year + 1))

    shown = q[q["Year"].isin(shown_years)][["Month", "Year", "Value"]].copy()
    shown["Series"] = shown["Year"].astype(int).astype(str)
    avg = q[q["Year"].isin(avg_years)].groupby("Month", as_index=False)["Value"].mean()
    avg["Year"] = np.nan
    avg["Series"] = f"{average_years}Y average"
    return pd.concat([shown, avg], ignore_index=True).sort_values(["Series", "Month"]).reset_index(drop=True)


def regional_monthly(regional_flows: pd.DataFrame, flow_type: str) -> pd.DataFrame:
    q = regional_flows[regional_flows["Flow Type"] == flow_type].copy()
    return q.sort_values(["Date", "Region"]).reset_index(drop=True)


def regional_series(regional_flows: pd.DataFrame, flow_type: str, region: str) -> pd.DataFrame:
    q = regional_flows[(regional_flows["Flow Type"] == flow_type) & (regional_flows["Region"] == region)].copy()
    return q[["Date", "Flow USD bn"]].rename(columns={"Flow USD bn": flow_type}).sort_values("Date")


def _style(fig: go.Figure, title: str, ytitle: str = "USD bn", xtitle: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=16, color=BBVA_NAVY)),
        template="simple_white",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial", size=11, color=BBVA_GREY),
        margin=dict(l=65, r=35, t=78, b=65),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="closest",
    )
    fig.update_xaxes(title=xtitle, gridcolor="#EEF1F4", zeroline=False)
    fig.update_yaxes(title=ytitle, gridcolor="#EEF1F4", zeroline=False)
    return fig


def fig_total_tracker(total_flows: pd.DataFrame, lookback_months: int = 30) -> go.Figure:
    q = total_flows.dropna(subset=["Date"]).sort_values("Date").tail(int(lookback_months)).copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=q["Date"], y=q["Equity"], name="Equity flows", marker_color=BBVA_RED))
    fig.add_trace(go.Bar(x=q["Date"], y=q["Debt"], name="Debt flows", marker_color=BBVA_BLUE))
    fig.add_trace(go.Scatter(x=q["Date"], y=q["Total"], name="Total flows", mode="lines", line=dict(color="#000000", width=2.8)))
    fig.update_layout(barmode="relative")
    fig.add_hline(y=0, line_color="#000000", line_width=1)
    return _style(fig, "IIF Tracker: Total Portfolio Flows into Emerging Markets [USD bn]", "USD bn")


def fig_total_decomposition(total_flows: pd.DataFrame, lookback_months: int = 30) -> go.Figure:
    q = total_flows.dropna(subset=["Date"]).sort_values("Date").tail(int(lookback_months)).copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=q["Date"], y=q["China Debt"], name="China Debt flows", marker_color="#F8CD51"))
    fig.add_trace(go.Bar(x=q["Date"], y=q["China Equity"], name="China Equity flows", marker_color="#2DCC70"))
    fig.add_trace(go.Bar(x=q["Date"], y=q["EM ex-China Equity"], name="EM ex-China Equity flows", marker_color=BBVA_RED))
    fig.add_trace(go.Bar(x=q["Date"], y=q["EM ex-China Debt"], name="EM ex-China Debt flows", marker_color=BBVA_BLUE))
    fig.add_trace(go.Scatter(x=q["Date"], y=q["Total"], name="Total flows", mode="lines", line=dict(color="#000000", width=2.8)))
    fig.update_layout(barmode="relative")
    fig.add_hline(y=0, line_color="#000000", line_width=1)
    return _style(fig, "IIF Tracker: Total Portfolio Flows into Emerging Markets [USD bn]", "USD bn")


def fig_cumulative_profile(profile: pd.DataFrame, title: str, average_years: int = 5) -> go.Figure:
    fig = go.Figure()
    if profile is None or profile.empty:
        return _style(fig, title, "USD bn", "Month")
    year_series = sorted([s for s in profile["Series"].dropna().unique() if not str(s).endswith("average")])
    palette = [BBVA_MID_GREY, BBVA_LIGHT_BLUE, BBVA_AQUA, BBVA_BLUE]
    current = max(year_series) if year_series else None
    current_last = None
    for i, series in enumerate(year_series):
        q = profile[profile["Series"] == series].sort_values("Month")
        is_current = series == current
        fig.add_trace(go.Scatter(
            x=q["Month"], y=q["Value"], mode="lines+markers" if is_current else "lines",
            name=str(series),
            line=dict(color=BBVA_BLUE if is_current else palette[i % len(palette)], width=3.2 if is_current else 1.9),
            marker=dict(size=6 if is_current else 4),
            hovertemplate=f"{series}<br>%{{x}}<br>Cumulative flow: %{{y:+,.2f}} USD bn<extra></extra>",
        ))
        if is_current:
            current_last = q.dropna(subset=["Value"]).tail(1)
    avg_name = f"{average_years}Y average"
    avg = profile[profile["Series"] == avg_name].sort_values("Month")
    if not avg.empty:
        fig.add_trace(go.Scatter(
            x=avg["Month"], y=avg["Value"], mode="lines", name=avg_name,
            line=dict(color=BBVA_ORANGE, width=3.0, dash="dash"),
            hovertemplate=f"{avg_name}<br>%{{x}}<br>Average: %{{y:+,.2f}} USD bn<extra></extra>",
        ))
    if current_last is not None and not current_last.empty:
        x = float(current_last["Month"].iloc[0]); y = float(current_last["Value"].iloc[0])
        fig.add_annotation(x=x, y=y, text=f"{y:+.2f}", showarrow=True, arrowhead=0, ax=28, ay=-24 if y >= 0 else 24,
                           bgcolor="rgba(255,255,255,.92)", bordercolor=BBVA_BLUE, borderwidth=1, borderpad=3,
                           font=dict(size=12, color=BBVA_BLUE))
    fig.add_hline(y=0, line_color=BBVA_GREY, line_width=1)
    fig = _style(fig, title, "USD bn", "Month")
    fig.update_xaxes(tickmode="array", tickvals=list(range(1,13)), ticktext=[MONTH_LABELS_EN[i] for i in range(1,13)], range=[0.7,12.3])
    fig.update_layout(hovermode="x unified")
    return fig


def fig_regional_monthly(regional_flows: pd.DataFrame, flow_type: str = "Total", lookback_months: int = 36) -> go.Figure:
    q = regional_monthly(regional_flows, flow_type)
    dates = sorted(q["Date"].dropna().unique())[-int(lookback_months):]
    q = q[q["Date"].isin(dates)].copy()
    colors = {
        "Emerging Asia": BBVA_BLUE,
        "Latin America": BBVA_AQUA,
        "Emerging Europe": BBVA_ORANGE,
        "Africa & Middle East": BBVA_GREEN,
    }
    fig = go.Figure()
    for region in REGIONS:
        r = q[q["Region"] == region]
        fig.add_trace(go.Bar(x=r["Date"], y=r["Flow USD bn"], name=region, marker_color=colors[region]))
    total = q[q["Region"] == "Total"]
    fig.add_trace(go.Scatter(x=total["Date"], y=total["Flow USD bn"], name="Total", mode="lines", line=dict(color="#000000", width=2.8)))
    fig.update_layout(barmode="relative")
    fig.add_hline(y=0, line_color="#000000", line_width=1)
    return _style(fig, f"Regional {flow_type.lower()} portfolio flows [USD bn]", "USD bn")
