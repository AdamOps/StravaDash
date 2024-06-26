import dash
import dash_bootstrap_components as dbc

from dash import html, Input, Output, State, dcc, ctx
from flask import make_response, request

from stravalib import Client
import webbrowser


class DashApp:
    def __init__(self, _client_id, _client_secret, _client_refresh):
        self.client_id = _client_id
        self.client_secret = _client_secret
        self.client_refresh = _client_refresh

        self.client = Client()

        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

        self.app.layout = html.Div([
            html.Div(id='hidden_div'),
            dcc.Interval(id='init_load', n_intervals=0, max_intervals=1, interval=100),
            html.P("Not much happening here."),
            dbc.Button("Fetch data", id="get_data"),
            dcc.Location(id='current_url')
        ],
            id='page_content')

        self.addCallbacks()

    def addCallbacks(self):
        @self.app.callback(
            [
                Output('hidden_div', 'children')
            ],
            [
                Input('get_data', 'n_clicks')
            ],
            prevent_initial_call=True,
        )
        def startOAUTH(n_clicks):
            if n_clicks is None:
                raise dash.exceptions.PreventUpdate

            # print("Processing OAUTH")
            authorize_url = self.client.authorization_url(
                client_id=self.client_id,
                redirect_uri='http://127.0.0.1:8080/callback',
                approval_prompt='auto',
                scope=['read_all', 'profile:read_all', 'activity:read_all']
            )

            # Open new tab with the OAUTH page
            webbrowser.open(authorize_url, new=0)

            raise dash.exceptions.PreventUpdate

        @self.app.callback(
            [
                Output('page_content', 'children')
            ],
            [
                Input('init_load', 'n_intervals'),
            ],
            [
                State('current_url', 'href')
            ],
            prevent_initial_call=True
        )
        def getData(n_intervals, current_url):
            trigger_id = ctx.triggered[0]['prop_id'].split(".")[0]
            if trigger_id is None:
                raise dash.exceptions.PreventUpdate

            print(current_url)
            code_start = current_url.find("code=")

            # If there is no code in the URL, then OAUTH failed (or it was never loaded)
            if code_start == -1:
                raise dash.exceptions.PreventUpdate

            # If there is a code in the current URL, we snag it and use it to get an access token and such.
            code = current_url[code_start+5:]
            code_end = code.find("&")
            code = code[0:code_end]

            print(f"Retrieved authorisation code: {code}")

            # Get an access token and a refresh token. This'll let us access all the athlete information.
            token_response = self.client.exchange_code_for_token(
                client_id=self.client_id,
                client_secret=self.client_secret,
                code=code
            )

            access_token = token_response['access_token']
            refresh_token = token_response['refresh_token']
            expires_at = token_response['expires_at']

            print(f"Access token: {access_token}\n Refresh token: {refresh_token}\n Expires at: {expires_at}")

            raise dash.exceptions.PreventUpdate

    def runApp(self):
        self.app.run_server(debug=True, port=8080)
