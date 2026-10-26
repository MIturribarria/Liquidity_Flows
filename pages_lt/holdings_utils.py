# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from pages_lt.ui_utils import BBVA_BLUE, BBVA_GREY, empty_fig, apply_layout


# -----------------------------------------------------------------------------
# Configuracion
# -----------------------------------------------------------------------------

SUMMARY_PARTICIPANTS = [
    "Bancos locales",
    "Siefores",
    "Fondos de inversión",
    "Otros inversionistas locales",
    "Inversionistas extranjeros",
]

DETAIL_PARTICIPANTS = [
    "Bancos locales",
    "Siefores",
    "Fondos de inversión",
    "Aseguradoras y afianzadoras",
    "Otros residentes locales",
    "Valores adquiridos por Banxico",
    "Reportos con Banxico",
    "Garantías recibidas por Banxico",
    "Inversionistas extranjeros",
]

# Se usa en la pagina de acumulados: permite escoger el agregado del reporte o
# cualquiera de sus componentes detallados.
SELECTABLE_PARTICIPANTS = [
    "Bancos locales",
    "Siefores",
    "Fondos de inversión",
    "Otros inversionistas locales",
    "Aseguradoras y afianzadoras",
    "Otros residentes locales",
    "Valores adquiridos por Banxico",
    "Reportos con Banxico",
    "Garantías recibidas por Banxico",
    "Inversionistas extranjeros",
]

# Alias para compatibilidad con versiones anteriores.
PARTICIPANTS = DETAIL_PARTICIPANTS

SUMMARY_FLOW_ORDER = [
    "Inversionistas extranjeros",
    "Otros inversionistas locales",
    "Fondos de inversión",
    "Siefores",
    "Bancos locales",
]

DETAIL_FLOW_ORDER = [
    "Inversionistas extranjeros",
    "Otros residentes locales",
    "Aseguradoras y afianzadoras",
    "Garantías recibidas por Banxico",
    "Reportos con Banxico",
    "Valores adquiridos por Banxico",
    "Fondos de inversión",
    "Siefores",
    "Bancos locales",
]

PARTICIPANT_COLORS = {
    "Bancos locales": "#001391",
    "Siefores": "#85C8FF",
    "Fondos de inversión": "#A5B3BF",
    "Otros inversionistas locales": "#88E783",
    "Aseguradoras y afianzadoras": "#2DCCCD",
    "Otros residentes locales": "#88E783",
    "Valores adquiridos por Banxico": "#1973B8",
    "Reportos con Banxico": "#8F7AE5",
    "Garantías recibidas por Banxico": "#F7893B",
    "Inversionistas extranjeros": "#070E46",
}

INSTRUMENT_COMPONENTS = {
    "Cetes": ["Cetes"],
    "Udibonos": ["UDIBonos"],
    "Bondes D/F/G": ["BondesD", "BondesF", "BondesG"],
    "MBonos": ["MBonos"],
    "Total": ["Cetes", "UDIBonos", "BondesD", "BondesF", "BondesG", "MBonos"],
}
INSTRUMENTS = list(INSTRUMENT_COMPONENTS.keys())

MONTH_LABELS = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}


def participants_for_breakdown(breakdown: str = "detail") -> list[str]:
    return SUMMARY_PARTICIPANTS if breakdown == "summary" else DETAIL_PARTICIPANTS


def flow_order_for_breakdown(breakdown: str = "detail") -> list[str]:
    return SUMMARY_FLOW_ORDER if breakdown == "summary" else DETAIL_FLOW_ORDER


# -----------------------------------------------------------------------------
# Carga de datos
# -----------------------------------------------------------------------------

def _candidate_paths() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    candidates: list[Path] = []
    explicit = os.getenv("HOLDINGS_BASE_PATH")
    if explicit:
        candidates.append(Path(explicit).expanduser())
    data_dir = Path(os.getenv("DASHBOARD_DATA_DIR", str(root / "data_files"))).expanduser()
    candidates.append(data_dir / "df_final_tenencias.csv")
    candidates.append(root / "df_final_tenencias.csv")
    liquidity_base = os.getenv("LIQUIDITY_BASE_PATH")
    if liquidity_base:
        candidates.append(Path(liquidity_base).expanduser().parent / "df_final_tenencias.csv")
    return list(dict.fromkeys(candidates))


def resolve_holdings_path() -> Path:
    for path in _candidate_paths():
        try:
            if path.exists():
                return path
        except OSError:
            continue
    tried = "\n - ".join(str(x) for x in _candidate_paths())
    raise FileNotFoundError("No se encontro df_final_tenencias.csv. Se intento:\n - " + tried)


def _parse_holdings_fecha(values: pd.Series) -> pd.Series:
    """Convierte fechas YYYY-MM-DD o DD/MM/YYYY sin inferencia ambigua.

    El origen puede alternar ambos formatos entre actualizaciones; por eso
    se parsea por patron, y las fechas desconocidas generan un error claro.
    """
    text = values.astype("string").str.strip()
    parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")

    formats = (
        (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
        (r"\d{1,2}/\d{1,2}/\d{4}", "%d/%m/%Y"),
        (r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "%Y-%m-%d %H:%M:%S"),
        (r"\d{1,2}/\d{1,2}/\d{4} \d{2}:\d{2}:\d{2}", "%d/%m/%Y %H:%M:%S"),
    )
    for regex, fmt in formats:
        mask = text.str.fullmatch(regex).fillna(False)
        if mask.any():
            parsed.loc[mask] = pd.to_datetime(
                text.loc[mask], format=fmt, errors="coerce"
            )

    invalid = text.notna() & text.ne("") & parsed.isna()
    if invalid.any():
        examples = text.loc[invalid].head(5).tolist()
        raise ValueError(
            f"La columna Fecha contiene {int(invalid.sum())} fechas invalidas "
            f"o de formato no reconocido. Ejemplos: {examples}. "
            "Se admiten YYYY-MM-DD y DD/MM/YYYY."
        )
    return parsed


def load_holdings_base() -> tuple[pd.DataFrame, str]:
    path = resolve_holdings_path()
    df = pd.read_csv(path, encoding="utf-8")
    df["Fecha"] = _parse_holdings_fecha(df["Fecha"])
    df = df.dropna(subset=["Fecha"]).sort_values("Fecha").reset_index(drop=True)
    for c in df.columns:
        if c != "Fecha":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df, str(path)


try:
    HOLDINGS_DAILY, HOLDINGS_SOURCE_PATH = load_holdings_base()
    HOLDINGS_LOAD_ERROR = None
except Exception as exc:
    HOLDINGS_DAILY = pd.DataFrame()
    HOLDINGS_SOURCE_PATH = ""
    HOLDINGS_LOAD_ERROR = str(exc)


def date_bounds() -> tuple[pd.Timestamp, pd.Timestamp]:
    if HOLDINGS_DAILY.empty:
        today = pd.Timestamp.today().normalize()
        return today - pd.DateOffset(years=1), today
    return HOLDINGS_DAILY["Fecha"].min(), HOLDINGS_DAILY["Fecha"].max()


# -----------------------------------------------------------------------------
# Construccion de tenencias
# -----------------------------------------------------------------------------

def _sum_existing(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    cols = [c for c in columns if c in df.columns]
    if not cols:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return df[cols].sum(axis=1, min_count=1)


def _direct_col(df: pd.DataFrame, prefix: str) -> pd.Series:
    col = f"{prefix} Total"
    if col not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def participant_holdings_frame(
    df: pd.DataFrame,
    instrument: str,
    total_mode: str = "display",
) -> pd.DataFrame:
    """Tenencias MXN mn con agregado y desglose completo de inversionistas locales."""
    if instrument not in INSTRUMENT_COMPONENTS:
        raise ValueError(f"Instrumento no reconocido: {instrument}")

    out = pd.DataFrame(index=df.index)
    out["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    if instrument == "Total" and total_mode == "csv":
        local = _direct_col(df, "Residentes locales")
        banks = _direct_col(df, "Sector bancario")
        pension = _direct_col(df, "Siefores")
        mutual = _direct_col(df, "Sociedades de inversion")
        # El CSV usa acentos; se accede de forma explicita abajo cuando aplica.
        if "Sociedades de inversión Total" in df.columns:
            mutual = pd.to_numeric(df["Sociedades de inversión Total"], errors="coerce")
        insurers = _direct_col(df, "Aseguradoras y afianzadoras")
        other_local = _direct_col(df, "Otros residentes locales")
        banxico_values = _direct_col(df, "Valores adquiridos por Banxico")
        repos = _direct_col(df, "Reportos con Banxico")
        guarantees = _direct_col(df, "Garantías recibidas por Banxico")
        if "Garantías recibidas por Banxico Total" in df.columns:
            guarantees = pd.to_numeric(df["Garantías recibidas por Banxico Total"], errors="coerce")
        foreign = _direct_col(df, "Residentes en el Extranjero")
        circulation = _direct_col(df, "Total circulación")
    else:
        components = INSTRUMENT_COMPONENTS[instrument]
        banks = _sum_existing(df, [f"Sector bancario {x}" for x in components])
        pension = _sum_existing(df, [f"Siefores {x}" for x in components])
        mutual = _sum_existing(df, [f"Sociedades de inversión {x}" for x in components])
        insurers = _sum_existing(df, [f"Aseguradoras y afianzadoras {x}" for x in components])
        other_local = _sum_existing(df, [f"Otros residentes locales {x}" for x in components])
        banxico_values = _sum_existing(df, [f"Valores adquiridos por Banxico {x}" for x in components])
        repos = _sum_existing(df, [f"Reportos con Banxico {x}" for x in components])
        guarantees = _sum_existing(df, [f"Garantías recibidas por Banxico {x}" for x in components])
        foreign = _sum_existing(df, [f"Residentes en el Extranjero {x}" for x in components])
        local = _sum_existing(df, [f"Residentes locales {x}" for x in components])
        circulation = _sum_existing(df, [f"Total circulación {x}" for x in components])

    out["Bancos locales"] = banks
    out["Siefores"] = pension
    out["Fondos de inversión"] = mutual
    out["Aseguradoras y afianzadoras"] = insurers
    out["Otros residentes locales"] = other_local
    out["Valores adquiridos por Banxico"] = banxico_values
    out["Reportos con Banxico"] = repos
    out["Garantías recibidas por Banxico"] = guarantees
    out["Inversionistas extranjeros"] = foreign

    # Agregado utilizado por el reporte: incluye aseguradoras, otros residentes y
    # las tres posiciones asociadas a Banxico que forman parte de residentes locales.
    out["Otros inversionistas locales"] = local - banks - pension - mutual
    out["Total circulation"] = circulation
    return out


def _subset_as_of(as_of=None) -> pd.DataFrame:
    if HOLDINGS_DAILY.empty:
        return HOLDINGS_DAILY.copy()
    d = HOLDINGS_DAILY.copy()
    if as_of is not None:
        d = d[d["Fecha"] <= pd.to_datetime(as_of)]
    return d


def monthly_base(as_of=None) -> pd.DataFrame:
    d = _subset_as_of(as_of)
    if d.empty:
        return d
    d = d.sort_values("Fecha").copy()
    d["Period"] = d["Fecha"].dt.to_period("M")
    fx = d.groupby("Period")["USDMXN"].mean().rename("FX monthly avg")
    month_end = d.groupby("Period", as_index=False).tail(1).copy()
    month_end["FX monthly avg"] = month_end["Period"].map(fx)
    return month_end.sort_values("Fecha").reset_index(drop=True)


def snapshot(
    instrument: str,
    as_of=None,
    total_mode: str = "display",
    breakdown: str = "detail",
) -> pd.DataFrame:
    d = _subset_as_of(as_of)
    if d.empty:
        return pd.DataFrame(columns=["Participant", "Holdings MXN bn", "Share (%)", "Date"])

    h = participant_holdings_frame(d.tail(1), instrument, total_mode=total_mode)
    total = h["Total circulation"].iloc[0]
    date = h["Fecha"].iloc[0]
    records = []
    for p in participants_for_breakdown(breakdown):
        value = h[p].iloc[0]
        records.append({
            "Participant": p,
            "Holdings MXN bn": value / 1000.0 if pd.notna(value) else np.nan,
            "Share (%)": value / total * 100.0 if pd.notna(value) and pd.notna(total) and total != 0 else np.nan,
            "Date": date,
        })
    return pd.DataFrame(records)


def holdings_table(as_of=None, breakdown: str = "detail") -> pd.DataFrame:
    participants = participants_for_breakdown(breakdown)
    rows = {p: {"Participant": p} for p in participants}
    rows["Total"] = {"Participant": "Total"}

    for inst in ["Cetes", "Udibonos", "Bondes D/F/G", "MBonos", "Total"]:
        s = snapshot(inst, as_of, total_mode="display", breakdown=breakdown)
        for _, r in s.iterrows():
            p = r["Participant"]
            rows[p][f"{inst} MXN bn"] = r["Holdings MXN bn"]
            rows[p][f"{inst} %"] = r["Share (%)"]
        rows["Total"][f"{inst} MXN bn"] = s["Holdings MXN bn"].sum(min_count=1)
        rows["Total"][f"{inst} %"] = 100.0
    return pd.DataFrame(list(rows.values()))


def holdings_history(
    instrument: str,
    as_of=None,
    months: int = 48,
    total_mode: str = "display",
    breakdown: str = "detail",
) -> pd.DataFrame:
    mb = monthly_base(as_of)
    if mb.empty:
        return pd.DataFrame(columns=["Date", "Participant", "Holdings MXN bn", "Share (%)"])
    if months:
        mb = mb.tail(int(months))

    h = participant_holdings_frame(mb, instrument, total_mode=total_mode)
    records = []
    for p in participants_for_breakdown(breakdown):
        records.append(pd.DataFrame({
            "Date": h["Fecha"],
            "Participant": p,
            "Holdings MXN bn": h[p] / 1000.0,
            "Share (%)": h[p] / h["Total circulation"] * 100.0,
        }))
    return pd.concat(records, ignore_index=True)


# -----------------------------------------------------------------------------
# Flujos
# -----------------------------------------------------------------------------

def monthly_flows(
    instrument: str,
    as_of=None,
    total_mode: str = "display",
    breakdown: str = "detail",
) -> pd.DataFrame:
    """Flow_m = (Holdings_m - Holdings_m-1) / FX_promedio_m / 1000."""
    mb = monthly_base(as_of)
    if mb.empty:
        return pd.DataFrame(columns=["Date", "Participant", "Monthly Flow USD bn"])

    h = participant_holdings_frame(mb, instrument, total_mode=total_mode)
    fx = pd.to_numeric(mb["FX monthly avg"], errors="coerce").replace(0, np.nan)

    if breakdown == "all":
        participants = SELECTABLE_PARTICIPANTS
    else:
        participants = participants_for_breakdown(breakdown)

    frames = []
    for p in participants:
        frames.append(pd.DataFrame({
            "Date": h["Fecha"],
            "Participant": p,
            "Monthly Flow USD bn": h[p].diff() / fx / 1000.0,
        }))
    return pd.concat(frames, ignore_index=True)


def horizon_flows(
    instrument: str,
    as_of=None,
    horizons=(1, 3, 6, 12),
    breakdown: str = "detail",
) -> pd.DataFrame:
    f = monthly_flows(instrument, as_of, total_mode="display", breakdown=breakdown)
    if f.empty:
        return pd.DataFrame(columns=["Horizon", "Participant", "Net Flow USD bn"])

    rows = []
    for n in horizons:
        for p in flow_order_for_breakdown(breakdown):
            s = f[f["Participant"] == p].sort_values("Date").tail(int(n))["Monthly Flow USD bn"]
            rows.append({"Horizon": int(n), "Participant": p, "Net Flow USD bn": s.sum(min_count=1)})
    return pd.DataFrame(rows)


def accumulated_ytd(
    instrument: str,
    participant: str,
    as_of=None,
    years_back: int | None = 5,
    years: list[int] | None = None,
) -> pd.DataFrame:
    """YTD cumulative flows only through each year's last actual monthly datum.

    Missing data are missing, not zeros. The selected-years monthly average
    ignores a year when that year has no observation for the month.
    """
    empty = pd.DataFrame(columns=[
        "Date", "Year", "Month", "Month label",
        "Monthly Flow USD bn", "Cumulative Flow USD bn",
        "Average selected years USD bn",
    ])
    if HOLDINGS_DAILY.empty:
        return empty
    latest_source_date = pd.to_datetime(HOLDINGS_DAILY["Fecha"], errors="coerce").max()
    requested_end = pd.Timestamp(as_of) if as_of is not None else latest_source_date
    if pd.isna(latest_source_date) or pd.isna(requested_end):
        return empty
    effective_end = min(requested_end, latest_source_date)

    total_mode = "csv" if instrument == "Total" else "display"
    f = monthly_flows(instrument, effective_end, total_mode=total_mode, breakdown="all")
    if f is None or f.empty:
        return empty
    f = f[f["Participant"] == participant].copy()
    f["Date"] = pd.to_datetime(f["Date"], errors="coerce")
    f["Monthly Flow USD bn"] = pd.to_numeric(f["Monthly Flow USD bn"], errors="coerce")
    f = f.dropna(subset=["Date", "Monthly Flow USD bn"])
    f = f[f["Date"] <= effective_end]
    if f.empty:
        return empty

    f["Year"] = f["Date"].dt.year.astype(int)
    if years:
        f = f[f["Year"].isin({int(y) for y in years})].copy()
    elif years_back is not None:
        max_year = int(f["Year"].max())
        f = f[f["Year"] >= max_year - int(years_back) + 1].copy()
    if f.empty:
        return empty

    f = f.sort_values("Date")
    f["Month"] = f["Date"].dt.month.astype(int)
    f["Month label"] = f["Month"].map(MONTH_LABELS)
    f["Cumulative Flow USD bn"] = f.groupby("Year")["Monthly Flow USD bn"].cumsum()
    average = f.groupby("Month")["Cumulative Flow USD bn"].mean()
    f["Average selected years USD bn"] = f["Month"].map(average)
    return f


def annual_flows(
    instrument: str,
    participant: str,
    as_of=None,
    start_year: int = 2010,
) -> pd.DataFrame:
    total_mode = "csv" if instrument == "Total" else "display"
    f = monthly_flows(instrument, as_of, total_mode=total_mode, breakdown="all")
    f = f[f["Participant"] == participant].copy()
    if f.empty:
        return pd.DataFrame(columns=["Year", "Net Flow USD bn"])
    f["Year"] = f["Date"].dt.year
    out = f.groupby("Year", as_index=False)["Monthly Flow USD bn"].sum(min_count=1)
    out = out.rename(columns={"Monthly Flow USD bn": "Net Flow USD bn"})
    return out[out["Year"] >= int(start_year)].reset_index(drop=True)


# -----------------------------------------------------------------------------
# Figuras
# -----------------------------------------------------------------------------

def _translate_source(fig: go.Figure) -> go.Figure:
    if fig.layout.annotations:
        for ann in fig.layout.annotations:
            if isinstance(ann.text, str) and ann.text.startswith("Source:"):
                ann.text = "Fuente: BBVA Global Markets Strategy"
    return fig


def donut_fig(data: pd.DataFrame, title: str):
    if data is None or data.empty:
        return empty_fig(title)
    p = data.dropna(subset=["Share (%)"]).copy()
    if p.empty:
        return empty_fig(title)

    # En el desglose completo hay varias participaciones muy pequeñas. Para
    # evitar etiquetas superpuestas, solo escribimos dentro del donut las
    # participaciones >= 2%; el resto sigue disponible en hover y leyenda.
    labels_inside = [f"{v:.1f}%" if pd.notna(v) and abs(v) >= 2.0 else "" for v in p["Share (%)"]]

    fig = go.Figure(go.Pie(
        labels=p["Participant"],
        values=p["Share (%)"],
        hole=0.66,
        sort=False,
        direction="clockwise",
        marker=dict(colors=[PARTICIPANT_COLORS.get(x, BBVA_BLUE) for x in p["Participant"]]),
        text=labels_inside,
        texttemplate="%{text}",
        textposition="inside",
        insidetextorientation="horizontal",
        hovertemplate="%{label}<br>Participación: %{value:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        template="simple_white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=12, color=BBVA_GREY),
        legend=dict(orientation="h", y=-0.12, x=0, xanchor="left"),
        margin=dict(l=30, r=30, t=70, b=135),
        height=430,
    )
    return fig


def _month_axis(data: pd.DataFrame):
    """Eje mensual categórico para que todas las barras tengan separación idéntica."""
    dates = pd.to_datetime(data["Date"], errors="coerce").dropna().sort_values().drop_duplicates()
    if dates.empty:
        return [], [], []

    periods = dates.dt.to_period("M")
    keys = periods.astype(str).tolist()
    n = len(keys)
    step = 3 if n <= 24 else (6 if n <= 60 else 12)
    idx = list(range(0, n, step))
    if (n - 1) not in idx:
        idx.append(n - 1)

    tickvals = [keys[i] for i in idx]
    ticktext = [f"{MONTH_LABELS[int(periods.iloc[i].month)]} {int(periods.iloc[i].year)}" for i in idx]
    return keys, tickvals, ticktext


def holdings_history_fig(data: pd.DataFrame, title: str):
    if data is None or data.empty:
        return empty_fig(title)

    pdat = data.copy()
    pdat["Date"] = pd.to_datetime(pdat["Date"], errors="coerce")
    pdat = pdat.dropna(subset=["Date"])
    pdat["MonthKey"] = pdat["Date"].dt.to_period("M").astype(str)

    participants = pdat["Participant"].dropna().drop_duplicates().tolist()
    all_keys, tickvals, ticktext = _month_axis(pdat)

    fig = go.Figure()
    for p in participants:
        q = pdat[pdat["Participant"] == p].sort_values("Date")
        fig.add_trace(go.Bar(
            x=q["MonthKey"],
            y=q["Share (%)"],
            name=p,
            marker_color=PARTICIPANT_COLORS.get(p, BBVA_BLUE),
            hovertemplate=f"{p}<br>%{{customdata}}<br>%{{y:.1f}}%<extra></extra>",
            customdata=q["Date"].dt.strftime("%b-%Y"),
        ))

    # Usar un eje categórico mensual elimina la irregularidad de los últimos
    # días hábiles de cada mes y garantiza exactamente la misma separación entre
    # la primera, las intermedias y la última barra.
    fig.update_layout(barmode="stack", bargap=0.18)
    fig = apply_layout(fig, title, "Participación en tenencias (%)", "")
    fig = _translate_source(fig)
    fig.update_yaxes(range=[0, 100], dtick=10)
    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=all_keys,
        tickmode="array",
        tickvals=tickvals,
        ticktext=ticktext,
        tickangle=0,
    )

    # Separar fuente, leyenda y eje evita el encimamiento visible en pantallas
    # anchas y cuando hay 9 categorías en el desglose completo.
    if fig.layout.annotations:
        for ann in fig.layout.annotations:
            if isinstance(ann.text, str) and (ann.text.startswith("Fuente:") or ann.text.startswith("Source:")):
                ann.y = -0.41
    fig.update_layout(
        legend=dict(orientation="h", y=-0.23, x=0, xanchor="left"),
        margin=dict(l=55, r=42, t=75, b=155),
        height=445,
    )
    return fig


def flow_history(
    instrument: str,
    start_date,
    end_date,
    breakdown: str = "detail",
) -> pd.DataFrame:
    """Flujos mensuales entre dos fechas conservando el mes previo para el delta."""
    end = pd.to_datetime(end_date)
    start = pd.to_datetime(start_date)
    f = monthly_flows(instrument, as_of=end, total_mode="display", breakdown=breakdown)
    if f.empty:
        return f
    return f[(f["Date"] >= start) & (f["Date"] <= end)].sort_values(["Date", "Participant"]).reset_index(drop=True)


def period_flow_summary(data: pd.DataFrame, breakdown: str = "detail") -> pd.DataFrame:
    """Suma de los flujos mensuales del periodo seleccionado por participante."""
    if data is None or data.empty:
        return pd.DataFrame(columns=["Participant", "Net Flow USD bn"])

    order = flow_order_for_breakdown(breakdown)
    out = (
        data.groupby("Participant", as_index=False)["Monthly Flow USD bn"]
        .sum(min_count=1)
        .rename(columns={"Monthly Flow USD bn": "Net Flow USD bn"})
    )
    out["Participant"] = pd.Categorical(out["Participant"], categories=order, ordered=True)
    return out.sort_values("Participant").reset_index(drop=True)


def period_flow_summary_fig(data: pd.DataFrame, instrument: str, breakdown: str = "detail"):
    title = f"{instrument} | Flujo acumulado del periodo por participante"
    if data is None or data.empty:
        return empty_fig(title)

    q = period_flow_summary(data, breakdown)
    if q.empty:
        return empty_fig(title)

    order = flow_order_for_breakdown(breakdown)
    fig = go.Figure(go.Bar(
        x=q["Net Flow USD bn"],
        y=q["Participant"],
        orientation="h",
        marker_color=[PARTICIPANT_COLORS.get(str(x), BBVA_BLUE) for x in q["Participant"]],
        text=q["Net Flow USD bn"].map(lambda x: f"{x:,.2f}" if pd.notna(x) else ""),
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>Flujo acumulado: %{x:,.2f} USD bn<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=1.5, line_color=BBVA_BLUE)
    fig = apply_layout(fig, title, "", "Flujo acumulado (USD bn)")
    fig = _translate_source(fig)
    fig.update_yaxes(categoryorder="array", categoryarray=order[::-1])
    fig.update_layout(
        showlegend=False,
        height=max(390, 38 * len(order) + 150),
        margin=dict(l=210 if breakdown == "detail" else 165, r=65, t=75, b=70),
    )
    return fig


def monthly_flow_history_fig(data: pd.DataFrame, instrument: str, breakdown: str = "detail"):
    title = f"{instrument} | Evolución mensual de flujos"
    if data is None or data.empty:
        return empty_fig(title)

    pdat = data.copy()
    pdat["Date"] = pd.to_datetime(pdat["Date"], errors="coerce")
    pdat = pdat.dropna(subset=["Date"])
    pdat["MonthKey"] = pdat["Date"].dt.to_period("M").astype(str)
    order = flow_order_for_breakdown(breakdown)
    all_keys, tickvals, ticktext = _month_axis(pdat)

    fig = go.Figure()
    for p in order:
        q = pdat[pdat["Participant"] == p].sort_values("Date")
        if q.empty:
            continue
        fig.add_trace(go.Bar(
            x=q["MonthKey"],
            y=q["Monthly Flow USD bn"],
            name=p,
            marker_color=PARTICIPANT_COLORS.get(p, BBVA_BLUE),
            customdata=q["Date"].dt.strftime("%b-%Y"),
            hovertemplate=f"{p}<br>%{{customdata}}<br>Flujo: %{{y:,.2f}} USD bn<extra></extra>",
        ))

    fig.add_hline(y=0, line_width=1.2, line_color=BBVA_BLUE)
    fig.update_layout(barmode="relative", bargap=0.18)
    fig = apply_layout(fig, title, "Flujo mensual (USD bn)", "")
    fig = _translate_source(fig)
    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=all_keys,
        tickmode="array",
        tickvals=tickvals,
        ticktext=ticktext,
    )
    if fig.layout.annotations:
        for ann in fig.layout.annotations:
            if isinstance(ann.text, str) and (ann.text.startswith("Fuente:") or ann.text.startswith("Source:")):
                ann.y = -0.37
    fig.update_layout(
        legend=dict(orientation="h", y=-0.21, x=0, xanchor="left"),
        margin=dict(l=60, r=35, t=75, b=145),
        height=500,
    )
    return fig

def horizon_flow_fig(data: pd.DataFrame, horizon: int, instrument: str, breakdown: str = "detail"):
    q = data[data["Horizon"] == int(horizon)].copy() if data is not None else pd.DataFrame()
    title = f"{instrument} | Cambio {horizon} mes{'es' if horizon != 1 else ''}"
    if q.empty:
        return empty_fig(title)

    order = flow_order_for_breakdown(breakdown)
    q["Participant"] = pd.Categorical(q["Participant"], categories=order, ordered=True)
    q = q.sort_values("Participant")

    fig = go.Figure(go.Bar(
        x=q["Net Flow USD bn"], y=q["Participant"], orientation="h",
        marker_color=[PARTICIPANT_COLORS.get(str(x), BBVA_BLUE) for x in q["Participant"]],
        text=q["Net Flow USD bn"].map(lambda x: f"{x:,.2f}" if pd.notna(x) else ""),
        textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>Flujo neto: %{x:,.2f} USD bn<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=1.5, line_color=BBVA_BLUE)
    fig = apply_layout(fig, title, "", "Flujo neto (USD bn)")
    fig = _translate_source(fig)
    fig.update_layout(
        showlegend=False,
        height=max(390, 38 * len(order) + 160),
        margin=dict(l=210 if breakdown == "detail" else 165, r=60, t=75, b=70),
    )
    fig.update_yaxes(categoryorder="array", categoryarray=order[::-1])
    return fig


def cumulative_ytd_fig(data: pd.DataFrame, instrument: str, participant: str):
    title = f"{instrument} | Evolución mensual de flujos acumulados"
    if data is None or data.empty:
        return empty_fig(title)

    years = sorted(data["Year"].dropna().astype(int).unique().tolist())
    if not years:
        return empty_fig(title)

    # Colores consistentes para los años elegidos manualmente.
    year_colors = [
        "#001391", "#1973B8", "#2DCCCD", "#88E783", "#8F7AE5",
        "#F7893B", "#46536D", "#85C8FF", "#070E46", "#B79CF7",
    ]

    fig = go.Figure()
    for i, y in enumerate(years):
        q = data[data["Year"] == y].copy()
        q["Month"] = pd.to_numeric(q["Month"], errors="coerce")
        q["Cumulative Flow USD bn"] = pd.to_numeric(q["Cumulative Flow USD bn"], errors="coerce")
        if "Date" in q:
            q["Date"] = pd.to_datetime(q["Date"], errors="coerce")
            q = q[q["Date"].dt.year.eq(y) & q["Date"].dt.month.eq(q["Month"])]
            if "Monthly Flow USD bn" in q:
                q = q[pd.to_numeric(q["Monthly Flow USD bn"], errors="coerce").notna()]
        q = q.dropna(subset=["Month", "Cumulative Flow USD bn"]).sort_values("Month")
        if q.empty:
            continue
        fig.add_trace(go.Scatter(
            x=q["Month"],
            y=q["Cumulative Flow USD bn"],
            mode="lines+markers",
            name=str(y),
            line=dict(color=year_colors[i % len(year_colors)], width=2),
            marker=dict(size=5, color=year_colors[i % len(year_colors)]),
            hovertemplate=f"{y}<br>Mes %{{x}}<br>%{{y:,.2f}} USD bn<extra></extra>",
        ))

    # Promedio aritmético mes a mes de las curvas seleccionadas. Si algún año
    # está incompleto, el promedio de ese mes usa únicamente observaciones
    # disponibles entre los años elegidos.
    valid = data.copy()
    valid["Cumulative Flow USD bn"] = pd.to_numeric(valid["Cumulative Flow USD bn"], errors="coerce")
    if "Date" in valid:
        valid["Date"] = pd.to_datetime(valid["Date"], errors="coerce")
        valid = valid[valid["Date"].dt.month.eq(pd.to_numeric(valid["Month"], errors="coerce"))]
        if "Monthly Flow USD bn" in valid:
            valid = valid[pd.to_numeric(valid["Monthly Flow USD bn"], errors="coerce").notna()]
    avg = (
        valid.dropna(subset=["Month", "Cumulative Flow USD bn"])
        .groupby("Month", as_index=False)["Cumulative Flow USD bn"]
        .mean()
        .sort_values("Month")
    )
    if not avg.empty:
        fig.add_trace(go.Scatter(
            x=avg["Month"],
            y=avg["Cumulative Flow USD bn"],
            mode="lines+markers",
            name="Promedio",
            line=dict(color="#B00028", width=3.5, dash="dash"),
            marker=dict(size=6, color="#B00028"),
            hovertemplate="Promedio<br>Mes %{x}<br>%{y:,.2f} USD bn<extra></extra>",
        ))

    fig.add_hline(y=0, line_width=1, line_color=BBVA_BLUE)
    fig = apply_layout(fig, title, "Flujo acumulado (USD bn)", "")
    fig = _translate_source(fig)
    fig.update_xaxes(
        tickmode="array", tickvals=list(range(1, 13)),
        ticktext=[MONTH_LABELS[x] for x in range(1, 13)], range=[0.7, 12.3],
    )
    fig.update_layout(
        height=315,
        legend=dict(orientation="h", y=-0.28, x=0),
        margin=dict(l=55, r=25, t=65, b=90),
    )
    return fig


def annual_flow_fig(data: pd.DataFrame, instrument: str, participant: str):
    title = f"{instrument} | Flujo neto total por año"
    if data is None or data.empty:
        return empty_fig(title)
    q = data.dropna(subset=["Net Flow USD bn"]).copy()
    if q.empty:
        return empty_fig(title)

    fig = go.Figure(go.Bar(
        x=q["Year"].astype(int), y=q["Net Flow USD bn"], marker_color=BBVA_BLUE,
        text=q["Net Flow USD bn"].map(lambda x: f"{x:,.2f}"), textposition="outside",
        cliponaxis=False,
        hovertemplate="Año: %{x}<br>Flujo neto: %{y:,.2f} USD bn<extra></extra>",
    ))
    fig.add_hline(y=0, line_width=1, line_color=BBVA_BLUE)
    fig = apply_layout(fig, title, "Flujo neto (USD bn)", "Año")
    fig = _translate_source(fig)
    fig.update_layout(
        showlegend=False,
        height=285,
        margin=dict(l=55, r=25, t=65, b=70),
    )
    return fig
