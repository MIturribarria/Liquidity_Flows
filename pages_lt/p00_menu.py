# -*- coding: utf-8 -*-
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import html

from pages_lt.ui_utils import BBVA_BLUE, BBVA_NAVY, BBVA_GREY, card, page_title


dash.register_page(
    __name__,
    path="/",
    name="Menu | Indice del Dashboard",
    order=-1,
)

SOURCE_TRADING_URL = (
    "https://www.banxico.org.mx/IndicadoresGraficos/actions/contenidoPortal/"
    "mercadosFin/61/113?menu=225&seccion=1600&locale=es"
)
SOURCE_HOLDINGS_URL = "https://www.banxico.org.mx/mercados/valores-gubernamentales-secto.html"


def _source_box(title, description, url, badge_text):
    return html.Div(
        [
            dbc.Badge(
                badge_text,
                color="primary",
                pill=True,
                style={"marginBottom": "8px"},
            ),
            html.H4(
                title,
                style={"color": BBVA_NAVY, "fontWeight": "bold", "marginBottom": "6px"},
            ),
            html.Div(
                description,
                style={"fontSize": "12px", "color": BBVA_GREY, "lineHeight": "1.5"},
            ),
            html.A(
                "Abrir fuente", href=url, target="_blank",
                style={"display": "inline-block", "marginTop": "10px", "fontSize": "12px",
                       "fontWeight": "bold", "color": BBVA_BLUE, "textDecoration": "none"},
            ) if url else None,
        ],
        style={
            "backgroundColor": "#F7F8F8",
            "borderLeft": f"4px solid {BBVA_BLUE}",
            "borderRadius": "8px",
            "padding": "14px 16px",
            "marginBottom": "14px",
        },
    )


def _page_card(number, title, description, path, badge=None):
    top = [
        html.Div(
            str(number),
            style={
                "minWidth": "30px",
                "height": "30px",
                "borderRadius": "50%",
                "backgroundColor": BBVA_BLUE,
                "color": "white",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "fontWeight": "bold",
                "fontSize": "12px",
                "marginRight": "10px",
            },
        ),
        html.Div(
            [
                html.Div(
                    title,
                    style={"fontWeight": "bold", "color": BBVA_NAVY, "fontSize": "14px"},
                ),
                html.Div(
                    description,
                    style={"fontSize": "11px", "color": BBVA_GREY, "marginTop": "3px", "lineHeight": "1.4"},
                ),
            ],
            style={"flex": "1"},
        ),
    ]

    if badge:
        top.append(
            dbc.Badge(
                badge,
                color="info",
                pill=True,
                style={"alignSelf": "flex-start", "marginLeft": "8px"},
            )
        )

    return html.A(
        card(
            [html.Div(top, style={"display": "flex", "alignItems": "flex-start"})],
            style={
                "height": "100%",
                "transition": "box-shadow 0.15s ease",
                "padding": "14px",
            },
        ),
        href=path,
        style={"textDecoration": "none", "color": "inherit", "height": "100%", "display": "block"},
    )


SECTION_1 = [
    (
        1,
        "Overview | Liquidity & Flows",
        "Vista consolidada de liquidez, Liquidity Score, momentum, heatmaps y flujos por inversionista.",
        "/liquidity-overview",
        None,
    ),
    (
        2,
        "MBono Liquidity Tracker",
        "Volumen, ticket, turnover, rangos históricos y participación por inversionista para MBonos.",
        "/mbono-liquidity",
        None,
    ),
    (
        3,
        "Udibono Liquidity Tracker",
        "Volumen, ticket, turnover, rangos históricos y participación por inversionista para Udibonos.",
        "/udibono-liquidity",
        None,
    ),
    (
        4,
        "MBono Net Purchases",
        "Compras netas por bono, agregación mensual/anual y acumulados para MBonos.",
        "/mbono-net-purchases",
        None,
    ),
    (
        5,
        "IRS | Liquidity Tracker",
        "Liquidez del mercado de swaps: volumen, participación IRS, inversionistas y distribución por plazo.",
        "/irs-liquidity-tracker",
        "Swaps",
    ),
    (
        6,
        "Udibono Net Purchases",
        "Compras netas por bono, agregación mensual/anual y acumulados para Udibonos.",
        "/udibono-net-purchases",
        None,
    ),
]

SECTION_2 = [
    (7, "Tenencias de Valores Gubernamentales",
     "Distribución sectorial, participación y evolución histórica de las tenencias por instrumento.",
     "/government-holdings", None),
    (8, "Flujos de Valores Gubernamentales",
     "Cambios de tenencia a 1/3/6/12 meses, evolución histórica y suma del periodo seleccionado.",
     "/government-holdings-flows", None),
    (9, "Flujos Acumulados por Inversionista",
     "Comparación de años, promedio seleccionado y flujos netos anuales por inversionista e instrumento.",
     "/accumulated-holdings-flows", None),
    (10, "Positioning & Ownership Overview",
     "Posicionamiento relativo, concentración HHI, Flow x Ownership, cambios de participación, absorción de oferta y asset allocation.",
     "/positioning-ownership-overview", "Analítica de posicionamiento"),
]

SECTION_3 = [
    (11, "IIF Flows",
     "Flujos de portafolio de mercados emergentes: tracker agregado, perfiles acumulados por país y análisis regional.",
     "/iif-flows", "Emerging Markets"),
]

SECTION_4 = [
    (12, "Comparación Flujos vs Net Purchases",
     "Página final de reconciliación: contrasta el cambio de tenencias sectorizadas con Net Purchases en MBonos y Udibonos.",
     "/flow-comparison", "Cruce de ambas bases"),
]



def _section(title, subtitle, source_box, pages):
    rows = []
    for i in range(0, len(pages), 2):
        cols = [dbc.Col(_page_card(*p), width=6, style={"marginBottom": "12px"}) for p in pages[i:i+2]]
        rows.append(dbc.Row(cols, class_name="g-3"))

    return html.Div(
        [
            html.H3(title, style={"color": BBVA_BLUE, "fontWeight": "bold", "marginBottom": "4px"}),
            html.Div(subtitle, style={"color": BBVA_GREY, "fontSize": "12px", "marginBottom": "12px"}),
            source_box,
            *rows,
        ],
        style={"marginBottom": "28px"},
    )


layout = html.Div(
    [
        page_title(
            "Menu | Indice del Dashboard",
            "Mapa de navegación y fuentes de información utilizadas en cada bloque del dashboard de liquidez y posicionamiento en valores gubernamentales.",
        ),
        _section(
            "1. Liquidez, volumen operado y Net Purchases",
            "Estas páginas utilizan bases de Banxico de actividad de mercado: volumen operado de títulos en moneda nacional y UDIS para bonos, y volumen operado de derivados para IRS/swaps.",
            _source_box(
                "Banxico - Actividad de mercado: bonos e IRS",
                "Fuente para métricas de actividad de mercado, volumen, turnover, ticket, Net Purchases y la nueva página IRS | Liquidity Tracker.",
                SOURCE_TRADING_URL,
                "Fuente 1",
            ),
            SECTION_1,
        ),
        _section(
            "2. Tenencias sectorizadas y posicionamiento",
            "Estas páginas utilizan la base de Banxico de tenencias sectorizadas de valores gubernamentales. La página de comparación cruza esta información con la base de volumen operado/Net Purchases del bloque anterior.",
            _source_box(
                "Banxico - Valores gubernamentales: tenencia sectorizada",
                "Fuente para composición de tenedores, cambios de tenencia, flujos aproximados, acumulados y análisis de posicionamiento por sector inversionista.",
                SOURCE_HOLDINGS_URL,
                "Fuente 2",
            ),
            SECTION_2,
        ),
        _section(
            "3. IIF Emerging Markets Flows",
            "Base mensual del Institute of International Finance (IIF) para flujos de portafolio de mercados emergentes, con información agregada, regional y por país.",
            _source_box(
                "Institute of International Finance (IIF) - Monthly EM Portfolio Flows",
                "Fuente para el tracker de flujos agregados, descomposición China / EM ex-China, flujos regionales y perfiles acumulados por país.",
                None,
                "Fuente 3",
            ),
            SECTION_3,
        ),
        _section(
            "4. Comparación de fuentes",
            "Cruce diagnóstico entre cambios de tenencias sectorizadas y Net Purchases para el universo comparable.",
            _source_box(
                "Banxico - Cruce de bases",
                "Combina las dos fuentes de Banxico utilizadas en los bloques 1 y 2. La comparación sirve para dirección, magnitud y co-movimiento, no para exigir igualdad exacta.",
                None,
                "Cruce",
            ),
            SECTION_4,
        ),
        html.Div(
            [
                html.Strong("Nota metodológica: ", style={"color": BBVA_BLUE}),
                html.Span(
                    "En las páginas basadas en tenencias, los 'flujos' se aproximan a partir del cambio mensual de tenencias convertido a USD con el USDMXN promedio mensual. "
                    "Por ello deben interpretarse como cambios de posición/tenencia y no como una medición directa de transacciones."
                ),
            ],
            style={
                "fontSize": "11px",
                "color": BBVA_GREY,
                "borderTop": "1px solid #E2E6EA",
                "paddingTop": "10px",
                "marginTop": "6px",
                "marginBottom": "20px",
            },
        ),
    ],
    style={"fontFamily": "Arial"},
)
