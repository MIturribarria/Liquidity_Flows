# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from pages_lt.ui_utils import BBVA_BLUE, BBVA_GREY, BBVA_RED, empty_fig, apply_layout
from pages_lt.holdings_utils import (
    HOLDINGS_DAILY,
    INSTRUMENTS,
    SUMMARY_PARTICIPANTS,
    DETAIL_PARTICIPANTS,
    PARTICIPANT_COLORS,
    participants_for_breakdown,
    flow_order_for_breakdown,
    monthly_base,
    monthly_flows,
    participant_holdings_frame,
    holdings_history,
)

CORE_INSTRUMENTS = ["Cetes", "Udibonos", "Bondes D/F/G", "MBonos"]
HEATMAP_METRICS = {
    "flow": "Flujo acumulado (USD bn)",
    "share": "Cambio en participación (pp)",
}


def _last_two_month_rows(as_of, horizon_months: int):
    mb = monthly_base(as_of)
    if mb.empty:
        return mb, mb

    mb = mb.sort_values("Fecha").copy()
    current = mb.tail(1)
    current_period = current["Fecha"].iloc[0].to_period("M")
    target_period = current_period - int(horizon_months)
    previous = mb[mb["Fecha"].dt.to_period("M") <= target_period].tail(1)

    if previous.empty:
        previous = mb.head(1)
    return current, previous


def ownership_change_table(
    as_of,
    horizon_months: int = 12,
    breakdown: str = "summary",
) -> pd.DataFrame:
    """Cross-section by participant and instrument.

    Returns current share, share change, holdings change and accumulated monthly
    flow for the chosen horizon. Total is intentionally excluded from the
    columns because the heatmap is most useful at instrument level.
    """
    current_rows, previous_rows = _last_two_month_rows(as_of, horizon_months)
    if current_rows.empty or previous_rows.empty:
        return pd.DataFrame()

    participants = participants_for_breakdown(breakdown)
    records = []

    for inst in INSTRUMENTS:
        cur = participant_holdings_frame(current_rows, inst, total_mode="display")
        prev = participant_holdings_frame(previous_rows, inst, total_mode="display")
        flows = monthly_flows(inst, as_of=as_of, total_mode="display", breakdown=breakdown)

        cur_total = pd.to_numeric(cur["Total circulation"], errors="coerce").iloc[0]
        prev_total = pd.to_numeric(prev["Total circulation"], errors="coerce").iloc[0]

        for p in participants:
            cur_h = pd.to_numeric(cur[p], errors="coerce").iloc[0]
            prev_h = pd.to_numeric(prev[p], errors="coerce").iloc[0]
            cur_share = cur_h / cur_total * 100.0 if pd.notna(cur_total) and cur_total != 0 else np.nan
            prev_share = prev_h / prev_total * 100.0 if pd.notna(prev_total) and prev_total != 0 else np.nan

            fp = (
                flows[flows["Participant"] == p]
                .sort_values("Date")
                .tail(int(horizon_months))["Monthly Flow USD bn"]
            )

            records.append({
                "Instrument": inst,
                "Participant": p,
                "Current Share (%)": cur_share,
                "Change Share (pp)": cur_share - prev_share if pd.notna(cur_share) and pd.notna(prev_share) else np.nan,
                "Current Holdings MXN bn": cur_h / 1000.0 if pd.notna(cur_h) else np.nan,
                "Holdings Change MXN bn": (cur_h - prev_h) / 1000.0 if pd.notna(cur_h) and pd.notna(prev_h) else np.nan,
                "Flow USD bn": fp.sum(min_count=1),
                "Current Circulation MXN bn": cur_total / 1000.0 if pd.notna(cur_total) else np.nan,
                "Circulation Change MXN bn": (cur_total - prev_total) / 1000.0 if pd.notna(cur_total) and pd.notna(prev_total) else np.nan,
                "Current Date": current_rows["Fecha"].iloc[0],
                "Comparison Date": previous_rows["Fecha"].iloc[0],
            })

    return pd.DataFrame(records)


def current_vs_history(
    instrument: str,
    as_of,
    lookback_years: int = 5,
    breakdown: str = "summary",
) -> pd.DataFrame:
    months = max(12, int(lookback_years) * 12)
    hist = holdings_history(
        instrument,
        as_of=as_of,
        months=months,
        total_mode="display",
        breakdown=breakdown,
    )
    if hist.empty:
        return pd.DataFrame()

    hist = hist.sort_values("Date")
    rows = []
    for p in participants_for_breakdown(breakdown):
        s = hist.loc[hist["Participant"] == p, "Share (%)"].dropna()
        if s.empty:
            continue
        current = float(s.iloc[-1])
        percentile = float((s <= current).mean() * 100.0)
        rows.append({
            "Participant": p,
            "Current (%)": current,
            "Min (%)": float(s.min()),
            "Median (%)": float(s.median()),
            "Max (%)": float(s.max()),
            "Percentile": percentile,
            "Observations": int(s.size),
        })
    return pd.DataFrame(rows)


def hhi_history(
    instrument: str,
    as_of,
    lookback_years: int = 5,
) -> pd.DataFrame:
    """HHI on the five report groups, in the conventional 0-10,000 scale."""
    hist = holdings_history(
        instrument,
        as_of=as_of,
        months=max(12, int(lookback_years) * 12),
        total_mode="display",
        breakdown="summary",
    )
    if hist.empty:
        return pd.DataFrame(columns=["Date", "HHI"])

    piv = hist.pivot_table(index="Date", columns="Participant", values="Share (%)", aggfunc="last")
    piv = piv.reindex(columns=SUMMARY_PARTICIPANTS)
    hhi = (piv.pow(2)).sum(axis=1, min_count=1)
    return hhi.rename("HHI").reset_index().sort_values("Date")


def issuance_absorption(
    instrument: str,
    as_of,
    horizon_months: int = 12,
    breakdown: str = "summary",
) -> pd.DataFrame:
    current_rows, previous_rows = _last_two_month_rows(as_of, horizon_months)
    if current_rows.empty or previous_rows.empty:
        return pd.DataFrame()

    cur = participant_holdings_frame(current_rows, instrument, total_mode="display")
    prev = participant_holdings_frame(previous_rows, instrument, total_mode="display")
    cur_total = pd.to_numeric(cur["Total circulation"], errors="coerce").iloc[0]
    prev_total = pd.to_numeric(prev["Total circulation"], errors="coerce").iloc[0]
    delta_circ = (cur_total - prev_total) / 1000.0

    rows = []
    for p in participants_for_breakdown(breakdown):
        cur_h = pd.to_numeric(cur[p], errors="coerce").iloc[0]
        prev_h = pd.to_numeric(prev[p], errors="coerce").iloc[0]
        delta_h = (cur_h - prev_h) / 1000.0
        rows.append({
            "Participant": p,
            "Holdings Change MXN bn": delta_h,
            "Circulation Change MXN bn": delta_circ,
            "Absorption (%)": delta_h / delta_circ * 100.0 if pd.notna(delta_circ) and abs(delta_circ) > 1e-12 else np.nan,
            "Current Date": current_rows["Fecha"].iloc[0],
            "Comparison Date": previous_rows["Fecha"].iloc[0],
        })
    return pd.DataFrame(rows)


def asset_allocation(participant: str, as_of) -> pd.DataFrame:
    """Snapshot de distribución de cartera a una fecha."""
    mb = monthly_base(as_of)
    if mb.empty:
        return pd.DataFrame()
    row = mb.tail(1)

    records = []
    for inst in CORE_INSTRUMENTS:
        h = participant_holdings_frame(row, inst, total_mode="display")
        value = pd.to_numeric(h[participant], errors="coerce").iloc[0] / 1000.0
        records.append({"Instrument": inst, "Holdings MXN bn": value})

    out = pd.DataFrame(records)
    total = out["Holdings MXN bn"].sum(min_count=1)
    out["Portfolio Share (%)"] = out["Holdings MXN bn"] / total * 100.0 if pd.notna(total) and total != 0 else np.nan
    out["Participant"] = participant
    return out


def asset_allocation_history(participant: str, start_date, end_date) -> pd.DataFrame:
    """Historia mensual del asset allocation entre Cetes/Udibonos/Bondes/MBonos.

    Devuelve un formato largo con participación (%) y monto (MXN bn) por fecha e
    instrumento. El denominador es la suma de los cuatro instrumentos comparables
    para el inversionista seleccionado en cada mes.
    """
    mb = monthly_base(end_date)
    if mb.empty:
        return pd.DataFrame(columns=[
            "Date", "Instrument", "Holdings MXN bn", "Portfolio Share (%)", "Participant"
        ])

    start = pd.to_datetime(start_date) if start_date is not None else mb["Fecha"].min()
    end = pd.to_datetime(end_date) if end_date is not None else mb["Fecha"].max()
    mb = mb[(mb["Fecha"] >= start) & (mb["Fecha"] <= end)].copy()
    if mb.empty:
        return pd.DataFrame(columns=[
            "Date", "Instrument", "Holdings MXN bn", "Portfolio Share (%)", "Participant"
        ])

    wide = pd.DataFrame({"Date": pd.to_datetime(mb["Fecha"]).values})
    for inst in CORE_INSTRUMENTS:
        h = participant_holdings_frame(mb, inst, total_mode="display")
        wide[inst] = pd.to_numeric(h[participant], errors="coerce").to_numpy() / 1000.0

    wide["Portfolio Total MXN bn"] = wide[CORE_INSTRUMENTS].sum(axis=1, min_count=1)

    frames = []
    for inst in CORE_INSTRUMENTS:
        tmp = pd.DataFrame({
            "Date": wide["Date"],
            "Instrument": inst,
            "Holdings MXN bn": wide[inst],
            "Portfolio Total MXN bn": wide["Portfolio Total MXN bn"],
        })
        tmp["Portfolio Share (%)"] = np.where(
            tmp["Portfolio Total MXN bn"].notna() & (tmp["Portfolio Total MXN bn"].abs() > 1e-12),
            tmp["Holdings MXN bn"] / tmp["Portfolio Total MXN bn"] * 100.0,
            np.nan,
        )
        tmp["Participant"] = participant
        frames.append(tmp)

    return pd.concat(frames, ignore_index=True).sort_values(["Date", "Instrument"]).reset_index(drop=True)


def positioning_kpis(
    instrument: str,
    as_of,
    horizon_months: int = 12,
    breakdown: str = "summary",
):
    changes = ownership_change_table(as_of, horizon_months, breakdown)
    if changes.empty:
        return {
            "foreign_share": np.nan,
            "hhi": np.nan,
            "buyer": "-",
            "buyer_value": np.nan,
            "seller": "-",
            "seller_value": np.nan,
        }

    sub = changes[changes["Instrument"] == instrument].copy()
    foreign = sub.loc[sub["Participant"] == "Inversionistas extranjeros", "Current Share (%)"]
    hhi = hhi_history(instrument, as_of, lookback_years=1)
    hhi_value = hhi["HHI"].iloc[-1] if not hhi.empty else np.nan

    valid = sub.dropna(subset=["Flow USD bn"])
    buyer_row = valid.loc[valid["Flow USD bn"].idxmax()] if not valid.empty else None
    seller_row = valid.loc[valid["Flow USD bn"].idxmin()] if not valid.empty else None
    if buyer_row is not None and buyer_row["Flow USD bn"] <= 0:
        buyer_row = None
    if seller_row is not None and seller_row["Flow USD bn"] >= 0:
        seller_row = None

    return {
        "foreign_share": foreign.iloc[0] if not foreign.empty else np.nan,
        "hhi": hhi_value,
        "buyer": buyer_row["Participant"] if buyer_row is not None else "-",
        "buyer_value": buyer_row["Flow USD bn"] if buyer_row is not None else np.nan,
        "seller": seller_row["Participant"] if seller_row is not None else "-",
        "seller_value": seller_row["Flow USD bn"] if seller_row is not None else np.nan,
    }


# -----------------------------------------------------------------------------
# Figures
# -----------------------------------------------------------------------------

def position_range_fig(data: pd.DataFrame, instrument: str, lookback_years: int):
    title = f"{instrument} | Posición actual vs rango histórico ({lookback_years}A)"
    if data is None or data.empty:
        return empty_fig(title)

    order = data["Participant"].tolist()[::-1]
    fig = go.Figure()

    for _, r in data.iterrows():
        fig.add_trace(go.Scatter(
            x=[r["Min (%)"], r["Max (%)"]],
            y=[r["Participant"], r["Participant"]],
            mode="lines",
            line=dict(color="#C7CDD3", width=5),
            showlegend=False,
            hoverinfo="skip",
        ))

    fig.add_trace(go.Scatter(
        x=data["Median (%)"],
        y=data["Participant"],
        mode="markers",
        marker=dict(symbol="diamond", size=9, color="#46536D"),
        name="Mediana",
        customdata=data["Percentile"],
        hovertemplate="%{y}<br>Mediana: %{x:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=data["Current (%)"],
        y=data["Participant"],
        mode="markers+text",
        marker=dict(symbol="circle", size=12, color=BBVA_BLUE),
        text=data["Percentile"].map(lambda x: f"P{x:.0f}"),
        textposition="middle right",
        name="Actual",
        hovertemplate="%{y}<br>Actual: %{x:.1f}%<br>Percentil: %{text}<extra></extra>",
    ))

    fig = apply_layout(fig, title, "", "Participación (%)")
    fig.update_yaxes(categoryorder="array", categoryarray=order)
    fig.update_layout(height=max(420, 46 * len(data) + 180), margin=dict(l=210, r=70, t=85, b=75))
    return fig


def flow_ownership_scatter_fig(data: pd.DataFrame, instrument: str, horizon_months: int):
    title = f"{instrument} | Flow x Ownership ({horizon_months}M)"
    q = data[data["Instrument"] == instrument].dropna(subset=["Current Share (%)", "Flow USD bn"]).copy() if data is not None else pd.DataFrame()
    if q.empty:
        return empty_fig(title)

    median_share = q["Current Share (%)"].median()
    sizes = pd.to_numeric(q["Current Holdings MXN bn"], errors="coerce").clip(lower=0)
    max_size = sizes.max()
    marker_sizes = 14 + (sizes / max_size * 26 if pd.notna(max_size) and max_size > 0 else 0)

    fig = go.Figure(go.Scatter(
        x=q["Current Share (%)"],
        y=q["Flow USD bn"],
        mode="markers+text",
        text=q["Participant"],
        textposition="top center",
        marker=dict(
            size=marker_sizes,
            color=[PARTICIPANT_COLORS.get(x, BBVA_BLUE) for x in q["Participant"]],
            opacity=0.88,
            line=dict(color="white", width=1),
        ),
        customdata=np.column_stack([q["Current Holdings MXN bn"], q["Change Share (pp)"]]),
        hovertemplate=(
            "%{text}<br>Share actual: %{x:.1f}%<br>Flujo: %{y:,.2f} USD bn"
            "<br>Tenencias: %{customdata[0]:,.1f} MXN bn"
            "<br>Cambio share: %{customdata[1]:+.2f} pp<extra></extra>"
        ),
    ))
    fig.add_hline(y=0, line_color="#46536D", line_dash="dot")
    fig.add_vline(x=median_share, line_color="#A5B3BF", line_dash="dot")
    fig = apply_layout(fig, title, "Flujo acumulado (USD bn)", "Participación actual (%)")
    fig.update_layout(showlegend=False, height=470, margin=dict(l=65, r=40, t=85, b=70))
    return fig


def ownership_change_heatmap_fig(data: pd.DataFrame, metric: str, breakdown: str = "summary"):
    col = "Flow USD bn" if metric == "flow" else "Change Share (pp)"
    title = "Heatmap inversionista x instrumento | " + HEATMAP_METRICS.get(metric, col)
    if data is None or data.empty:
        return empty_fig(title)

    participants = flow_order_for_breakdown(breakdown)
    piv = data.pivot_table(index="Participant", columns="Instrument", values=col, aggfunc="sum")
    piv = piv.reindex(index=participants, columns=CORE_INSTRUMENTS)

    # Siempre conservamos el flujo en USD bn como customdata para que el hover
    # muestre el monto aun cuando el color represente cambio en participación.
    flow_piv = data.pivot_table(
        index="Participant", columns="Instrument", values="Flow USD bn", aggfunc="sum"
    ).reindex(index=participants, columns=CORE_INSTRUMENTS)

    z = piv.to_numpy(dtype=float)
    flow_values = flow_piv.to_numpy(dtype=float)
    finite = np.abs(z[np.isfinite(z)])
    zmax = float(finite.max()) if finite.size else 1.0
    if zmax == 0:
        zmax = 1.0

    text = np.where(np.isfinite(z), np.vectorize(lambda x: f"{x:+.2f}")(z), "")

    if metric == "flow":
        hover = (
            "Inversionista: %{y}<br>"
            "Instrumento: %{x}<br>"
            "Flujo acumulado: %{z:+.2f} USD bn<extra></extra>"
        )
    else:
        hover = (
            "Inversionista: %{y}<br>"
            "Instrumento: %{x}<br>"
            "Cambio en participación: %{z:+.2f} pp<br>"
            "Flujo acumulado: %{customdata:+.2f} USD bn<extra></extra>"
        )

    fig = go.Figure(go.Heatmap(
        z=z,
        x=piv.columns.tolist(),
        y=piv.index.tolist(),
        zmid=0,
        zmin=-zmax,
        zmax=zmax,
        colorscale=[[0, "#B00028"], [0.5, "#FFFFFF"], [1, "#2DCCCD"]],
        text=text,
        texttemplate="%{text}",
        customdata=flow_values,
        hovertemplate=hover,
        colorbar=dict(title="USD bn" if metric == "flow" else "pp"),
    ))
    fig = apply_layout(fig, title, "", "")
    fig.update_layout(height=max(430, 38 * len(participants) + 170), margin=dict(l=205 if breakdown == "detail" else 165, r=65, t=85, b=65))
    return fig


def hhi_history_fig(data: pd.DataFrame, instrument: str):
    title = f"{instrument} | Concentración de tenedores (HHI)"
    if data is None or data.empty:
        return empty_fig(title)

    fig = go.Figure(go.Scatter(
        x=data["Date"], y=data["HHI"], mode="lines",
        line=dict(color=BBVA_BLUE, width=2.5),
        hovertemplate="%{x|%b-%Y}<br>HHI: %{y:,.0f}<extra></extra>",
    ))
    fig = apply_layout(fig, title, "HHI (0-10,000)", "")
    fig.update_layout(showlegend=False, height=430, margin=dict(l=70, r=35, t=85, b=75))
    return fig


def issuance_absorption_fig(data: pd.DataFrame, instrument: str, horizon_months: int, breakdown: str = "summary"):
    if data is None or data.empty:
        return empty_fig(f"{instrument} | Absorción del cambio en circulación")

    delta_circ = pd.to_numeric(data["Circulation Change MXN bn"], errors="coerce").dropna()
    delta_label = delta_circ.iloc[0] if not delta_circ.empty else np.nan
    title = f"{instrument} | Absorción del cambio en circulación ({horizon_months}M)"

    order = flow_order_for_breakdown(breakdown)
    q = data.copy()
    q["Participant"] = pd.Categorical(q["Participant"], categories=order, ordered=True)
    q = q.sort_values("Participant")

    fig = go.Figure(go.Bar(
        x=q["Holdings Change MXN bn"],
        y=q["Participant"],
        orientation="h",
        marker_color=[PARTICIPANT_COLORS.get(str(x), BBVA_BLUE) for x in q["Participant"]],
        text=q["Holdings Change MXN bn"].map(lambda x: f"{x:+,.1f}" if pd.notna(x) else ""),
        textposition="outside",
        cliponaxis=False,
        customdata=q["Absorption (%)"],
        hovertemplate=(
            "%{y}<br>Cambio tenencias: %{x:+,.1f} MXN bn"
            "<br>Absorción: %{customdata:+.1f}%<extra></extra>"
        ),
    ))
    fig.add_vline(x=0, line_color="#46536D")
    fig = apply_layout(fig, title, "", "Cambio en tenencias (MXN bn)")
    fig.update_yaxes(categoryorder="array", categoryarray=order[::-1])
    fig.add_annotation(
        x=1, y=1.10, xref="paper", yref="paper", showarrow=False,
        text=f"Δ circulación: {delta_label:+,.1f} MXN bn" if pd.notna(delta_label) else "Δ circulación: n.d.",
        xanchor="right", font=dict(size=11, color=BBVA_GREY),
    )
    fig.update_layout(showlegend=False, height=max(420, 38 * len(order) + 170), margin=dict(l=210 if breakdown == "detail" else 165, r=70, t=95, b=70))
    return fig


def asset_allocation_fig(data: pd.DataFrame, participant: str):
    """Snapshot 100% stacked del asset allocation."""
    title = f"{participant} | Distribución de cartera por instrumento"
    if data is None or data.empty:
        return empty_fig(title)

    fig = go.Figure()
    colors = {
        "Cetes": "#85C8FF",
        "Udibonos": "#2DCCCD",
        "Bondes D/F/G": "#8F7AE5",
        "MBonos": "#001391",
    }
    for _, r in data.iterrows():
        fig.add_trace(go.Bar(
            x=[r["Portfolio Share (%)"]],
            y=[participant],
            orientation="h",
            name=r["Instrument"],
            marker_color=colors.get(r["Instrument"], BBVA_BLUE),
            text=[f"{r['Portfolio Share (%)']:.1f}%" if pd.notna(r["Portfolio Share (%)"]) and r["Portfolio Share (%)"] >= 3 else ""],
            textposition="inside",
            customdata=[[r["Holdings MXN bn"]]],
            hovertemplate=f"{r['Instrument']}<br>Participación: %{{x:.1f}}%<br>Tenencias: %{{customdata[0]:,.1f}} MXN bn<extra></extra>",
        ))
    fig.update_layout(barmode="stack")
    fig = apply_layout(fig, title, "", "Participación de la cartera (%)")
    fig.update_xaxes(range=[0, 100])
    fig.update_layout(height=330, legend=dict(orientation="h", y=-0.22, x=0), margin=dict(l=180, r=35, t=85, b=100))
    return fig


def asset_allocation_history_fig(data: pd.DataFrame, participant: str):
    """Evolución mensual 100% stacked del asset allocation."""
    title = f"{participant} | Evolución histórica de distribución de cartera"
    if data is None or data.empty:
        return empty_fig(title)

    colors = {
        "Cetes": "#85C8FF",
        "Udibonos": "#2DCCCD",
        "Bondes D/F/G": "#8F7AE5",
        "MBonos": "#001391",
    }
    fig = go.Figure()
    for inst in CORE_INSTRUMENTS:
        q = data[data["Instrument"] == inst].sort_values("Date")
        if q.empty:
            continue
        fig.add_trace(go.Scatter(
            x=q["Date"],
            y=q["Portfolio Share (%)"],
            mode="lines",
            stackgroup="allocation",
            name=inst,
            line=dict(color=colors.get(inst, BBVA_BLUE), width=1.2),
            customdata=q[["Holdings MXN bn"]].to_numpy(),
            hovertemplate=(
                f"{inst}<br>"
                "%{x|%b-%Y}<br>"
                "Participación: %{y:.1f}%<br>"
                "Tenencias: %{customdata[0]:,.1f} MXN bn<extra></extra>"
            ),
        ))

    fig = apply_layout(fig, title, "Participación de la cartera (%)", "")
    fig.update_yaxes(range=[0, 100], dtick=10)
    fig.update_layout(
        hovermode="x unified",
        height=430,
        legend=dict(orientation="h", y=-0.20, x=0),
        margin=dict(l=70, r=35, t=85, b=100),
    )
    return fig
