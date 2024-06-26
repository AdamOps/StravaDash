import dash

from dash import Input, Output, State, ctx, dcc

from stravalib import Client
import webbrowser

from static_layout import *


class DashApp:
    def __init__(self, _client_id, _client_secret, _client_refresh):
        self.client_id = _client_id
        self.client_secret = _client_secret
        self.client_refresh = _client_refresh

        self.access_token = None
        self.refresh_token = None
        self.expires_at = None

        self.client = Client()

        self.app = dash.Dash(__name__,
                             external_stylesheets=[dbc.themes.FLATLY],
                             suppress_callback_exceptions=True)

        self.app.layout = html.Div(
            [
                navbar,
                html.Div(id='hidden_div'),
                dcc.Interval(id='init_load_timer', n_intervals=0, max_intervals=1, interval=100),
                dcc.Location(id='current_url'),
                dcc.Store(id='access_token', storage_type='session'),
                dcc.Store(id='refresh_token', storage_type='session'),

                # This Div displays the actual page content. It's initially empty
                # If the init_load callback finds a cookie or an auth code in the URL, it gives the option to fetch
                # updates via the Strava API.
                # If the callback finds nothing, it generates a button that takes the user to an OAUTH page.
                html.Div(children=[], id='page_content'),
            ],
            id='app_layout',
        )

        self.addCallbacks()

    def addCallbacks(self):
        @self.app.callback(
            [
                # Output('hidden_div', 'children')
                Output('current_url', 'href')
            ],
            [
                Input('getOAUTH', 'n_clicks')
            ],
            prevent_initial_call=True, )
        def startOAUTH(n_clicks):
            if n_clicks is None:
                raise dash.exceptions.PreventUpdate

            # print("Processing OAUTH")
            authorise_url = self.client.authorization_url(
                client_id=self.client_id,
                redirect_uri='http://127.0.0.1:8080/',
                approval_prompt='auto',
                scope=['read_all', 'profile:read_all', 'activity:read_all']
            )

            # Open up the URL within the same tab. After pressing the OAUTH approval button, the Dash app will be
            # reloaded. It'll then retrieve the auth-code, fetch an access/refresh token and store those in the session.
            # Next time the Dash app is opened up, it'll simply fetch those tokens from memory instead of going through
            # this process again.
            # Need to implement a check for whether the access_token has expired and needs to be refreshed, which
            # shouldn't be all that complicated.
            return [authorise_url]

        @self.app.callback(
            [
                Output('page_content', 'children'),
                Output('access_token', 'data'),
                Output('refresh_token', 'data'),
            ],
            [
                Input('init_load_timer', 'n_intervals'),
            ],
            [
                State('current_url', 'href'),
                State('access_token', 'data'),
                State('refresh_token', 'data'),
            ],
            prevent_initial_call=True,
        )
        def checkCookie(n_intervals, current_url, access_token, refresh_token):
            trigger_id = ctx.triggered[0]['prop_id'].split(".")[0]
            if trigger_id is None:
                print("Initial load (that should've been skipped!!!)")
                raise dash.exceptions.PreventUpdate

            if access_token is None:
                print(f'No access/refresh token cookie found. Access token in the Store component is {access_token}')
                print(f"Access token in the class instance variable is {self.access_token}")
            else:
                print(f"Returned the auth code found in the cookie: {access_token}")
                self.access_token = access_token
                self.refresh_token = refresh_token

            print(current_url)
            code_start = current_url.find("code=")

            # If there is no code in the URL, then OAUTH failed (or it was never loaded)
            if code_start == -1 and self.access_token is None:
                print("Access token not found in neither the URL nor in a cookie.")
                return ([html.Div([
                    html.P("Click the button below to authorise the dashboard to connect to your Strava page."),
                    html.P(
                        "The access token will be stored as a cookie, so that you only have to click this button once"),
                    html.P("If you ever see this page after authorising, it's because I'm a poor programmer :("),
                    dbc.Button("Go to OAUTH page", id="getOAUTH")
                ])], dash.no_update, dash.no_update)

            if self.access_token is None:
                # If there is a code in the current URL, we snag it and use it to get an access token and such.
                code = current_url[code_start + 5:]
                code_end = code.find("&")
                code = code[0:code_end]

                print(f"Retrieved authorisation code: {code}")

                # Get an access token and a refresh token. This'll let us access all the athlete information.
                token_response = self.client.exchange_code_for_token(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    code=code
                )

                # Store the various bits of information into separate variables, for ease.
                self.access_token = token_response['access_token']
                self.refresh_token = token_response['refresh_token']
                self.expires_at = token_response['expires_at']
            print(f"Access token: {self.access_token}\n"
                  f"Refresh token: {self.refresh_token}\n"
                  f"Expires at: {self.expires_at}")

            return ([html.P(f"Found an access token! It's {self.access_token}")], self.access_token, self.refresh_token)

    def runApp(self):
        self.app.run_server(debug=True, port=8080)
