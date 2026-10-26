# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go

BBVA_BLUE='#001391'; BBVA_NAVY='#072146'; BBVA_LIGHT_BLUE='#85C8FF'; BBVA_AQUA='#2DCCCD'; BBVA_GREEN='#88E783'; BBVA_GREY='#46536D'; BBVA_MID_GREY='#A5B3BF'; BBVA_ORANGE='#F7893B'; BBVA_BG='#F7F8F8'
IRS_COL='Sobre dos tasas de interés en la misma moneda (IRS)'
TOTAL_SWAPS_COL='Contratos de Intercambio (Swaps)'
LOCAL_COL='Contrapartes residentes en México'
FOREIGN_COL='Contrapartes residentes en el Extranjero'

TENOR_SPECS=[
 ('0-1Y', ['De 1 a 7 días','De 8 días a 31 días','De 32 días a 92 días','De 93 días a 184 días','De 185 días a 366 días']),
 ('2-4Y', ['De 367 días a 731 días','De 732 días a 1,096 días','De 1,097 días a 1,461 días']),
 ('5-7Y', ['De 1,462 días a 1,827 días','De 1,828 días a 2,557 días']),
 ('8-10Y',['De 2,558 días a 3,653 días']),
 ('+10Y', ['De 3,654 días a 5,479 días','De 5,480 días a 7,305 días','Más de 7,306 días']),
]
TENOR_COLORS={'0-1Y':BBVA_BLUE,'2-4Y':BBVA_LIGHT_BLUE,'5-7Y':BBVA_AQUA,'8-10Y':BBVA_GREEN,'+10Y':BBVA_MID_GREY}


def find_irs_csv(data_dir: str|Path, explicit: str|Path|None=None)->Path:
    if explicit:
        p=Path(explicit).expanduser()
        if not p.exists(): raise FileNotFoundError(f'IRS CSV not found: {p}')
        return p
    root=Path(data_dir).expanduser()
    for name in ['IRS_volumen.csv','IRS_volumen(1).csv']:
        p=root/name
        if p.exists(): return p
    hits=sorted(root.glob('IRS_volumen*.csv'))
    if not hits: raise FileNotFoundError(f'No IRS_volumen*.csv found in: {root}')
    return hits[0]


def detect_irs_suspicious_dates(df: pd.DataFrame, spike_multiple: float = 12.0) -> pd.DataFrame:
    """Flag isolated, implausibly large daily TOTAL swaps observations.

    A flag is a *possible typo*, not proof. Conservative gates:
      (i) >= 12x centered local 21-observation median;
      (ii) > MXN 500,000 million, and above the local period's normal range;
      (iii) both immediate neighbours < 20% of the spike (an isolated day).
    Only days satisfying ALL conditions are masked in analytical data. No
    interpolation or invented transactions are introduced. The source CSV
    is never modified. Raw and flagged values are recorded for audit.
    """
    col = TOTAL_SWAPS_COL
    x = pd.to_numeric(df[col], errors='coerce').astype(float)
    loc = x.rolling(21, center=True, min_periods=7).median()
    before = x.shift(1)
    after = x.shift(-1)
    ratio = x / loc.replace(0, np.nan)
    flag = (
        (x > 500_000) & (ratio >= float(spike_multiple)) &
        before.notna() & after.notna() &
        (before < x * 0.20) & (after < x * 0.20)
    ).fillna(False)
    return pd.DataFrame({
        'Fecha': df['Fecha'].loc[flag].to_numpy(),
        'Raw total swaps (MXN mn)': x.loc[flag].to_numpy(),
        'Local median (MXN mn)': loc.loc[flag].to_numpy(),
        'Ratio vs local median': ratio.loc[flag].to_numpy(),
        'Treatment': 'Excluded from cleaned analytics; original CSV preserved',
    })


def load_irs_csv(path: str | Path, clean_outliers: bool = True) -> pd.DataFrame:
    """Read the original source and conservatively mask isolated extreme spikes.

    Default cleaned figures and XLSX downloads share this exact loader.
    Identified dates are listed in ``df.attrs['qc_events']`` and in the
    ``IRS QC Flag`` column for transparent auditing.
    """
    d = pd.read_csv(path, low_memory=False, encoding='utf-8-sig')
    raw_dates = d['Fecha'].astype('string').str.strip()
    dates_iso = pd.to_datetime(raw_dates, format='%Y-%m-%d', errors='coerce')
    dates_dmy = pd.to_datetime(raw_dates, format='%d/%m/%Y', errors='coerce')
    d['Fecha'] = dates_iso.fillna(dates_dmy)
    bad_dates = d['Fecha'].isna() & raw_dates.notna() & raw_dates.ne('')
    if bad_dates.any():
        raise ValueError('IRS Fecha unrecognised: ' + str(raw_dates[bad_dates].head(5).tolist()))
    d = d.dropna(subset=['Fecha']).sort_values('Fecha').reset_index(drop=True)
    for c in d.columns:
        if c != 'Fecha':
            d[c] = pd.to_numeric(d[c], errors='coerce')
    flagged = detect_irs_suspicious_dates(d)
    d['IRS QC Flag'] = d['Fecha'].isin(flagged['Fecha']).astype(bool)
    if clean_outliers and not flagged.empty:
        # The row's aggregate, breakdown and tenor components describe the
        # same day's market. Mask all together to preserve internal identity.
        numeric_cols = [c for c in d.select_dtypes(include=[np.number]).columns]
        d.loc[d['IRS QC Flag'], numeric_cols] = np.nan
    d.attrs['qc_events'] = flagged
    d.attrs['source_path'] = str(Path(path).resolve())
    d.attrs['quality_method'] = 'Isolated >12x rolling median, >500000 MXN mn, two normal neighbours; excluded not interpolated'
    return d


def quality_events(d: pd.DataFrame) -> pd.DataFrame:
    """Quality-control audit log retained by ``load_irs_csv``."""
    return d.attrs.get('qc_events', pd.DataFrame()).copy()


def _style(fig,title,ytitle='',xtitle='',height=380):
    fig.update_layout(title=dict(text=title,x=.01,xanchor='left',font=dict(size=15,color=BBVA_NAVY)),height=height,paper_bgcolor='white',plot_bgcolor='white',font=dict(family='Arial',size=11,color=BBVA_GREY),margin=dict(l=70,r=30,t=58,b=70),legend=dict(orientation='h',yanchor='top',y=-.18,x=0),hovermode='x unified')
    fig.update_xaxes(title=xtitle,showgrid=False,linecolor='#A5B3BF',ticks='outside')
    fig.update_yaxes(title=ytitle,gridcolor='#E8EAED',zerolinecolor='#A5B3BF')
    return fig


def rolling_volume_fig(d, sma=30, history_years=5):
    q=d.copy(); cutoff=q.Fecha.max()-pd.DateOffset(years=history_years); q=q[q.Fecha>=cutoff]
    fig=go.Figure()
    for col,name,color,width in [(TOTAL_SWAPS_COL,'Total swaps',BBVA_LIGHT_BLUE,2),(IRS_COL,'IRS',BBVA_BLUE,2.8)]:
        y=q[col].rolling(sma,min_periods=max(3,sma//3)).mean()
        fig.add_trace(go.Scatter(x=q.Fecha,y=y,mode='lines',name=name,line=dict(color=color,width=width)))
    return _style(fig,f'Swaps | Average traded volume | {sma}D SMA','MXN mn','',390)


def investor_volume_history_fig(d,sma=30,history_years=5):
    q=d.copy(); q=q[q.Fecha>=q.Fecha.max()-pd.DateOffset(years=history_years)]
    fig=go.Figure()
    for col,name,color in [(LOCAL_COL,'Local',BBVA_LIGHT_BLUE),(FOREIGN_COL,'Foreign',BBVA_BLUE)]:
        fig.add_trace(go.Scatter(x=q.Fecha,y=q[col].rolling(sma,min_periods=max(3,sma//3)).mean(),mode='lines',name=name,line=dict(color=color,width=2.4)))
    return _style(fig,f'Swaps | Average traded volume by investor | {sma}D SMA','MXN mn','',390)


def annual_summary(d):
    q=d.copy(); q['Year']=q.Fecha.dt.year
    a=q.groupby('Year')[[TOTAL_SWAPS_COL,IRS_COL,LOCAL_COL,FOREIGN_COL]].mean().reset_index()
    a['Other swaps']=(a[TOTAL_SWAPS_COL]-a[IRS_COL]).clip(lower=0)
    a['IRS share (%)']=np.where(a[TOTAL_SWAPS_COL]>0,a[IRS_COL]/a[TOTAL_SWAPS_COL]*100,np.nan)
    denom=a[LOCAL_COL]+a[FOREIGN_COL]
    a['Local share (%)']=np.where(denom>0,a[LOCAL_COL]/denom*100,np.nan)
    a['Foreign share (%)']=np.where(denom>0,a[FOREIGN_COL]/denom*100,np.nan)
    return a


def annual_instrument_share_fig(d, years=16):
    a=annual_summary(d).tail(years)
    fig=go.Figure()
    fig.add_bar(x=a.Year.astype(str),y=a['IRS share (%)'],name='IRS',marker_color=BBVA_BLUE,text=a['IRS share (%)'].map(lambda x:f'{x:.0f}%'),textposition='inside')
    fig.add_bar(x=a.Year.astype(str),y=100-a['IRS share (%)'],name='Other swaps',marker_color=BBVA_LIGHT_BLUE,text=(100-a['IRS share (%)']).map(lambda x:f'{x:.0f}%'),textposition='inside')
    fig.update_layout(barmode='stack',uniformtext_minsize=8,uniformtext_mode='hide')
    fig=_style(fig,'Swaps | Share of total traded volume by instrument (%)','%','Year',390); fig.update_yaxes(range=[0,100],dtick=20)
    return fig


def annual_investor_share_fig(d, years=16):
    a=annual_summary(d).tail(years)
    fig=go.Figure()
    fig.add_bar(x=a.Year.astype(str),y=a['Foreign share (%)'],name='Foreign',marker_color=BBVA_BLUE,text=a['Foreign share (%)'].map(lambda x:f'{x:.0f}%'),textposition='inside')
    fig.add_bar(x=a.Year.astype(str),y=a['Local share (%)'],name='Local',marker_color=BBVA_LIGHT_BLUE,text=a['Local share (%)'].map(lambda x:f'{x:.0f}%'),textposition='inside')
    fig.update_layout(barmode='stack',uniformtext_minsize=8,uniformtext_mode='hide')
    fig=_style(fig,'Swaps | Share of total traded volume by investor (%)','%','Year',390); fig.update_yaxes(range=[0,100],dtick=20)
    return fig


def _tenor_columns(d):
    out={}
    for label,parts in TENOR_SPECS:
        cols=[]
        for c in d.columns:
            if not (c.startswith('Mercados organizados ') or c.startswith('Mercados extrabursátiles ')): continue
            if any(c.endswith(p) for p in parts): cols.append(c)
        out[label]=cols
    return out


def tenor_daily(d):
    cols=_tenor_columns(d); out=pd.DataFrame({'Fecha':d.Fecha})
    for label,cs in cols.items(): out[label]=d[cs].sum(axis=1,min_count=1) if cs else np.nan
    return out


def annual_tenor(d, last_years=5):
    t=tenor_daily(d); t['Year']=t.Fecha.dt.year
    a=t.groupby('Year')[[x[0] for x in TENOR_SPECS]].mean().reset_index().tail(last_years)
    return a


def annual_tenor_volume_fig(d,last_years=5):
    a=annual_tenor(d,last_years)
    fig=go.Figure()
    for lab,_ in TENOR_SPECS: fig.add_bar(x=a.Year.astype(str),y=a[lab],name=lab,marker_color=TENOR_COLORS[lab])
    fig.update_layout(barmode='stack')
    return _style(fig,'IRS | Average traded volume by tenor (MXN mn)','MXN mn','Year',390)


def annual_tenor_share_fig(d,last_years=5):
    a=annual_tenor(d,last_years); labs=[x[0] for x in TENOR_SPECS]; den=a[labs].sum(axis=1)
    fig=go.Figure()
    for lab in labs:
        v=np.where(den>0,a[lab]/den*100,np.nan)
        fig.add_bar(x=a.Year.astype(str),y=v,name=lab,marker_color=TENOR_COLORS[lab],text=[f'{x:.0f}%' if pd.notna(x) and x>=5 else '' for x in v],textposition='inside')
    fig.update_layout(barmode='stack',uniformtext_minsize=8,uniformtext_mode='hide')
    fig=_style(fig,'IRS | Distribution of average traded volume by tenor (%)','%','Year',390); fig.update_yaxes(range=[0,100],dtick=20)
    return fig


def current_tenor_fig(d,window=30):
    t=tenor_daily(d); end=t.Fecha.max(); q=t[t.Fecha>end-pd.Timedelta(days=window)]; labs=[x[0] for x in TENOR_SPECS]; vals=q[labs].mean()
    fig=go.Figure(go.Bar(x=labs,y=vals.values,marker_color=[TENOR_COLORS[x] for x in labs],text=[f'{v:,.0f}' for v in vals],textposition='outside'))
    return _style(fig,f'IRS | Current tenor profile | last {window} days','MXN mn','Tenor',350)


def tenor_heatmap_fig(d,years=10):
    a=annual_tenor(d,years); labs=[x[0] for x in TENOR_SPECS]; den=a[labs].sum(axis=1); z=np.array([np.where(den>0,a[x]/den*100,np.nan) for x in labs])
    fig=go.Figure(go.Heatmap(z=z,x=a.Year.astype(str),y=labs,colorscale=[[0,'#F7F8F8'],[.5,BBVA_LIGHT_BLUE],[1,BBVA_BLUE]],text=np.vectorize(lambda x:'' if np.isnan(x) else f'{x:.0f}%')(z),texttemplate='%{text}',colorbar=dict(title='%')))
    return _style(fig,'IRS | Tenor mix heatmap (%)','%','Year',350)


def kpis(d,window=30):
    q=d[d.Fecha>d.Fecha.max()-pd.Timedelta(days=window)]
    total=q[TOTAL_SWAPS_COL].mean(); irs=q[IRS_COL].mean(); foreign=q[FOREIGN_COL].mean(); local=q[LOCAL_COL].mean()
    t=tenor_daily(q); labs=[x[0] for x in TENOR_SPECS]; tv=t[labs].mean(); short=tv.get('0-1Y',np.nan)/tv.sum()*100 if tv.sum() else np.nan
    return {'as_of':d.Fecha.max(),'avg_total':total,'avg_irs':irs,'irs_share':irs/total*100 if total else np.nan,'foreign_share':foreign/(foreign+local)*100 if foreign+local else np.nan,'short_share':short}
