import dash_bootstrap_components as dbc
from dash import html, dcc

# Navigation bar, containing links to various versions of the model
navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.Col([
                html.A(
                    dbc.Col(
                        [
                            # Insert logo here
                        ],
                    ),
                    href="https://127.0.0.1:8080/",
                    style={"textDecoration": "none",
                           'align': 'left'},
                ),
            ],
                width=5,
            ),
            dbc.Col([
                dbc.Nav([],
                        vertical=False,
                        pills=True,
                        justified=False,
                        id='navbar_links',
                        ),
            ],
                width=7,
            ),
        ],
        # className="flex-grow-1"
    ),
    color="primary",
    dark=True,
    sticky="top",
    id="navbar",
)

navbar_links_init = [
    dbc.NavLink("Log in", href='login', active='exact')
]


navbar_links_logged_in = [
    dbc.NavLink("Runs", href='runs', active='exact'),
    dbc.NavLink("Bike rides", href='rides', active='exact'),
    dbc.NavLink("Gear", href='gear', active='exact')
]