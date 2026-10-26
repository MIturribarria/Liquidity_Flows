# -*- coding: utf-8 -*-
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import html


# Dashboard autónomo: solo depende de data.py + pages_lt + Base_M.csv.
app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages_lt",
    external_stylesheets=[dbc.themes.SPACELAB],
    suppress_callback_exceptions=True,
    title="Liquidity & Flows Tracker",
)

server = app.server


def _sidebar():
    return dbc.Nav(
        [
            dbc.NavLink(
                html.Div(page["name"], className="ms-2"),
                href=page["relative_path"],
                active="exact",
            )
            for page in dash.page_registry.values()
        ],
        vertical=True,
        pills=True,
        class_name="text-muted",
    )


app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.Div(
                                "BBVA",
                                style={
                                    "fontSize": "28px",
                                    "fontWeight": "bold",
                                    "color": "#001391",
                                    "letterSpacing": "1px",
                                },
                            ),
                            html.Div(
                                "Markets Intelligence & Strategy Unit (MISU)",
                                style={
                                    "fontSize": "13px",
                                    "color": "#46536D",
                                },
                            ),
                        ],
                        style={"paddingTop": "10px"},
                    ),
                    width=3,
                ),
                dbc.Col(
                    html.H1(
                        "Liquidity & Flows Tracker",
                        style={
                            "fontSize": "34px",
                            "fontFamily": "Arial",
                            "fontWeight": "bold",
                            "color": "#001391",
                            "textAlign": "center",
                            "marginTop": "12px",
                        },
                    ),
                    width=9,
                ),
            ]
        ),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(_sidebar(), xs=12, sm=3, md=2, lg=2, xl=2, xxl=2),
                dbc.Col(
                    dash.page_container,
                    xs=12,
                    sm=9,
                    md=10,
                    lg=10,
                    xl=10,
                    xxl=10,
                ),
            ]
        ),
    ],
    fluid=True,
    style={"fontFamily": "Arial", "backgroundColor": "white"},
)


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8051)
