# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
import pandas as pd


FLOW_PARTICIPANTS = ["Total", "Siefores", "Soc Inversion", "Otros Nac.", "Res. Exterior"]

MARKET_LABELS = {
    "BONOTF": "MBono",
    "UDIBONOS": "Udibono",
}

METRIC_LABELS = {
    "Volumen": "Average traded volume",
    "Turnover": "Turnover",
    "Total N Operaciones": "Number of trades",
    "Ticket": "Average ticket",
    "Liquidity Score": "Liquidity Score",
}

FLOW_COLUMNS = {
    "USD": "Compras netas USD",
    "DV01": "ComprasnetasnominalDV01",
}


def _dt(x):
    return pd.to_datetime(x, errors="coerce")


def prepare_liquidity_base(df: pd.DataFrame) -> pd.DataFrame:
    """Copia defensiva y tipificación mínima requerida por las nuevas páginas."""
    out = df.copy()
    out["Día"] = pd.to_datetime(out["Día"], errors="coerce")
    out["Vencimiento"] = pd.to_datetime(out.get("Vencimiento"), errors="coerce")

    numeric_cols = [
        "Volumen",
        "Turnover",
        "Total N Operaciones",
        "Ticket",
        "Número de Títulos en Circulación",
        "Duración",
        "Compras netas USD",
        "ComprasnetasnominalDV01",
    ]
    for c in numeric_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    return out


def window_bounds(end_date, window_days: int):
    end = pd.to_datetime(end_date)
    start = end - pd.Timedelta(days=int(window_days))
    prev_start = start - pd.Timedelta(days=int(window_days))
    return prev_start, start, end


def _market_total_rows(df: pd.DataFrame, market: str, start=None, end=None) -> pd.DataFrame:
    mask = (df["Tipo"] == market) & (df["Tipo de Contraparte"] == "Total")
    if start is not None:
        mask &= df["Día"] > pd.to_datetime(start)
    if end is not None:
        mask &= df["Día"] <= pd.to_datetime(end)

    out = df.loc[mask].copy()
    if "Vencimiento" in out.columns and end is not None:
        # Evita emisiones vencidas en rankings actuales.
        out = out[(out["Vencimiento"].isna()) | (out["Vencimiento"] > pd.to_datetime(end))]
    return out


def _flow_rows(df: pd.DataFrame, market: str, start=None, end=None) -> pd.DataFrame:
    """
    Filas base para análisis de flows en Overview.

    Se excluyen:
      - las filas pre-agregadas Tipo de Contraparte = Total, para evitar doble conteo;
      - Interbancaria, por definición de los flujos de inversionistas de esta página.
    """
    mask = (
        (df["Tipo"] == market)
        & (df["Tipo de Contraparte"] != "Total")
        & (df["Tipo de Contraparte"] != "Interbancaria")
    )
    if start is not None:
        mask &= df["Día"] > pd.to_datetime(start)
    if end is not None:
        mask &= df["Día"] <= pd.to_datetime(end)
    return df.loc[mask].copy()


def _pct_score(s: pd.Series, higher_is_better=True) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    rank = x.rank(pct=True, method="average") * 100.0
    return rank if higher_is_better else 100.0 - rank


def liquidity_snapshot(df: pd.DataFrame, market: str, start, end) -> pd.DataFrame:
    """
    Una fila por emisión para el periodo indicado.

    Score = promedio simple de percentiles cross-section de:
      - volumen promedio
      - turnover promedio
      - número promedio de operaciones
      - ticket promedio

    El score está acotado de 0 a 100.
    """
    d = _market_total_rows(df, market, start, end)
    if d.empty:
        return pd.DataFrame()

    agg = (
        d.groupby("Emisión", as_index=False)
        .agg(
            Avg_Volume=("Volumen", "mean"),
            Avg_Turnover=("Turnover", "mean"),
            Avg_Trades=("Total N Operaciones", "mean"),
            Avg_Ticket=("Ticket", "mean"),
            Outstanding=("Número de Títulos en Circulación", "mean"),
            Duration=("Duración", "mean"),
            Maturity=("Vencimiento", "max"),
            Obs=("Día", "nunique"),
        )
    )

    for c in ["Avg_Volume", "Avg_Turnover", "Avg_Trades", "Avg_Ticket"]:
        agg[f"Pctl_{c}"] = _pct_score(agg[c])

    score_cols = [
        "Pctl_Avg_Volume",
        "Pctl_Avg_Turnover",
        "Pctl_Avg_Trades",
        "Pctl_Avg_Ticket",
    ]
    agg["Liquidity Score"] = agg[score_cols].mean(axis=1, skipna=True)
    agg["Liquidity Score"] = agg["Liquidity Score"].clip(0, 100)

    return agg.sort_values("Liquidity Score", ascending=False).reset_index(drop=True)


def liquidity_momentum(df: pd.DataFrame, market: str, end_date, window_days: int) -> pd.DataFrame:
    prev_start, cur_start, end = window_bounds(end_date, window_days)

    cur = liquidity_snapshot(df, market, cur_start, end)
    prev = liquidity_snapshot(df, market, prev_start, cur_start)

    if cur.empty:
        return pd.DataFrame()

    keep_prev = prev[["Emisión", "Liquidity Score"]].rename(
        columns={"Liquidity Score": "Previous Score"}
    ) if not prev.empty else pd.DataFrame(columns=["Emisión", "Previous Score"])

    out = cur.merge(keep_prev, on="Emisión", how="left")
    out["Score Change"] = out["Liquidity Score"] - out["Previous Score"]
    out["Window Start"] = cur_start
    out["Window End"] = end
    out["Previous Window Start"] = prev_start
    out["Previous Window End"] = cur_start

    return out


def liquidity_heatmap_data(
    df: pd.DataFrame,
    market: str,
    end_date,
    window_days: int,
    metric: str,
    rolling_days: int = 30,
) -> pd.DataFrame:
    """
    Datos diarios por emisión. Para Liquidity Score calcula un score cross-section
    sobre medias móviles de rolling_days.
    """
    end = pd.to_datetime(end_date)
    start = end - pd.Timedelta(days=int(window_days) + int(rolling_days) * 2)
    d = _market_total_rows(df, market, start, end)

    if d.empty:
        return pd.DataFrame()

    cols = ["Día", "Emisión", "Volumen", "Turnover", "Total N Operaciones", "Ticket"]
    d = d[[c for c in cols if c in d.columns]].copy()
    d = d.sort_values(["Emisión", "Día"])

    metric_cols = ["Volumen", "Turnover", "Total N Operaciones", "Ticket"]
    for c in metric_cols:
        d[f"R_{c}"] = (
            d.groupby("Emisión")[c]
            .transform(lambda s: s.rolling(rolling_days, min_periods=max(3, rolling_days // 5)).mean())
        )

    if metric == "Liquidity Score":
        tmp = d[["Día", "Emisión"] + [f"R_{c}" for c in metric_cols]].copy()
        pcols = []
        for c in metric_cols:
            pc = f"P_{c}"
            tmp[pc] = tmp.groupby("Día")[f"R_{c}"].rank(pct=True) * 100.0
            pcols.append(pc)
        tmp["Value"] = tmp[pcols].mean(axis=1, skipna=True)
    else:
        raw_col = metric if metric in metric_cols else "Volumen"
        tmp = d[["Día", "Emisión", f"R_{raw_col}"]].rename(columns={f"R_{raw_col}": "Value"})

    requested_start = end - pd.Timedelta(days=int(window_days))
    tmp = tmp[(tmp["Día"] > requested_start) & (tmp["Día"] <= end)].dropna(subset=["Value"])

    # Orden estable por vencimiento implícito en el nombre no siempre es seguro;
    # usamos el orden medio de duración si está disponible.
    order = (
        _market_total_rows(df, market, requested_start, end)
        .groupby("Emisión")["Duración"]
        .mean()
        .sort_values()
        .index.tolist()
    )
    tmp["Emisión"] = pd.Categorical(tmp["Emisión"], categories=order, ordered=True)
    return tmp.sort_values(["Emisión", "Día"]).reset_index(drop=True)


def participant_flow_series(
    df: pd.DataFrame,
    market: str,
    participant: str,
    end_date,
    window_days: int,
    flow_unit: str = "USD",
    rolling_days: int = 20,
) -> pd.DataFrame:
    """
    Serie diaria y acumulada por emisión.

    participant = "Total" suma todas las contrapartes de inversionistas
    excepto Interbancaria. El parámetro rolling_days se conserva en la
    firma por compatibilidad con la página, aunque ya no se calcula Rolling Flow.
    """
    end = pd.to_datetime(end_date)
    start = end - pd.Timedelta(days=int(window_days))
    col = FLOW_COLUMNS.get(flow_unit, FLOW_COLUMNS["USD"])

    d = _flow_rows(df, market, start, end)
    if participant != "Total":
        d = d[d["Tipo de Contraparte"] == participant]

    d = d[["Día", "Emisión", col]].copy()
    if d.empty:
        return pd.DataFrame(columns=["Día", "Emisión", "Daily Flow", "Cumulative"])

    daily = (
        d.groupby(["Día", "Emisión"], as_index=False)[col]
        .sum()
        .sort_values(["Emisión", "Día"])
    )

    daily["Cumulative"] = daily.groupby("Emisión")[col].cumsum()
    daily = daily.rename(columns={col: "Daily Flow"})
    return daily


def investor_bond_heatmap(
    df: pd.DataFrame,
    market: str,
    end_date,
    window_days: int,
    flow_unit: str = "USD",
) -> pd.DataFrame:
    end = pd.to_datetime(end_date)
    start = end - pd.Timedelta(days=int(window_days))
    col = FLOW_COLUMNS.get(flow_unit, FLOW_COLUMNS["USD"])

    d = _flow_rows(df, market, start, end)
    if d.empty:
        return pd.DataFrame()

    out = (
        d.groupby(["Tipo de Contraparte", "Emisión"], as_index=False)[col]
        .sum()
        .rename(columns={col: "Net Flow"})
    )

    # Añadimos vencimiento para que el heatmap pueda ordenar la curva
    # de menor a mayor plazo por vencer, independientemente del flujo.
    if "Vencimiento" in d.columns:
        maturity = (
            d.groupby("Emisión", as_index=False)["Vencimiento"]
            .max()
            .rename(columns={"Vencimiento": "Maturity"})
        )
        out = out.merge(maturity, on="Emisión", how="left")
    else:
        out["Maturity"] = pd.NaT

    return out


def flow_liquidity_data(
    df: pd.DataFrame,
    market: str,
    participant: str,
    end_date,
    window_days: int,
    flow_unit: str = "USD",
) -> pd.DataFrame:
    end = pd.to_datetime(end_date)
    start = end - pd.Timedelta(days=int(window_days))
    col = FLOW_COLUMNS.get(flow_unit, FLOW_COLUMNS["USD"])

    liq = liquidity_snapshot(df, market, start, end)
    if liq.empty:
        return pd.DataFrame()

    d = _flow_rows(df, market, start, end)
    if participant != "Total":
        d = d[d["Tipo de Contraparte"] == participant]

    flows = (
        d.groupby("Emisión", as_index=False)[col]
        .sum()
        .rename(columns={col: "Net Flow"})
    )

    out = liq.merge(flows, on="Emisión", how="left")
    out["Net Flow"] = out["Net Flow"].fillna(0.0)
    out["Bubble Size"] = pd.to_numeric(out["Outstanding"], errors="coerce").clip(lower=0)

    return out


def market_kpis(df: pd.DataFrame, market: str, end_date, window_days: int) -> pd.DataFrame:
    end = pd.to_datetime(end_date)
    start = end - pd.Timedelta(days=int(window_days))
    d = _market_total_rows(df, market, start, end)

    if d.empty:
        return pd.DataFrame([{
            "Average daily volume": np.nan,
            "Average turnover": np.nan,
            "Average ticket": np.nan,
            "Average trades": np.nan,
        }])

    daily = (
        d.groupby("Día", as_index=False)
        .agg(
            Volume=("Volumen", "sum"),
            Trades=("Total N Operaciones", "sum"),
            Ticket=("Ticket", "mean"),
            Turnover=("Turnover", "mean"),
        )
    )

    return pd.DataFrame([{
        "Average daily volume": daily["Volume"].mean(),
        "Average turnover": daily["Turnover"].mean(),
        "Average ticket": daily["Ticket"].mean(),
        "Average trades": daily["Trades"].mean(),
    }])
