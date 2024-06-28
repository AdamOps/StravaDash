import dash
from dash import Input, Output, State, ctx, dcc

from stravalib import Client
import datetime as dt
import requests

import pandas as pd
import pathlib
import folium
import json
import random
from pprint import pprint

from static_layout import *
from parameters import *
import functions as fun


class DashApp:
    def __init__(self, _client_id, _client_secret, _client_refresh):
        self.client_id = _client_id
        self.client_secret = _client_secret
        self.client_refresh = _client_refresh

        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self.expires_in = None
        self.expires_timestamp = None

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
                dcc.Store(id='expires_at', storage_type='session'),
                dcc.Store(id='expires_in', storage_type='session'),
                dcc.Store(id='expires_timestamp', storage_type='session'),

                # This Div displays the actual page content. It's initially empty.
                # There are three options:
                # 1. We've opened the Dash app for the first time. It hasn't been authorised, so we have no access token
                #   and the URL contains no auth-code. We need to go through OAUTH first.
                # 2. We've been redirected here after the Strava OAUTH. There's no access token yet, but there's an
                #   auth-code in the URL, with which we can retrieve our access/refresh tokens.
                # 3. We've loaded an existing access/refresh token from the dcc.Store elements. We can check whether
                #   they're still valid (via the expires_at item in storage). If not, fetch an updated token. Otherwise,
                #   just use the loaded one as a valid one.
                #
                # Addendum: If a user wants to fetch an update, the app should check again whether the tokens are still
                # valid.
                html.Div(children=[], id='page_content'),
            ],
            id='app_layout',
        )

        self.addCallbacks()

    def addCallbacks(self):
        @self.app.callback(
            [
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
                Output('expires_at', 'data'),
                Output('expires_in', 'data'),
                Output('expires_timestamp', 'data'),
            ],
            [
                Input('init_load_timer', 'n_intervals'),
            ],
            [
                State('current_url', 'href'),
                State('access_token', 'data'),
                State('refresh_token', 'data'),
                State('expires_at', 'data'),
                State('expires_in', 'data'),
                State('expires_timestamp', 'data'),
            ],
            prevent_initial_call=True,
        )
        def ensureAccessToken(n_intervals, current_url,
                        access_token, refresh_token, expires_at, expires_in, expires_timestamp):
            trigger_id = ctx.triggered[0]['prop_id'].split(".")[0]
            if trigger_id is None:
                print("Initial load (that should've been skipped!!!)")
                raise dash.exceptions.PreventUpdate

            if access_token is not None:
                self.access_token = access_token
                self.refresh_token = refresh_token
                self.expires_at = expires_at
                self.expires_in = expires_in
                self.expires_timestamp = expires_timestamp

            # Look for the auth-code in the current URL
            code_start = current_url.find("code=")

            # If there is no code in the URL, and we don't already have an access/refresh token, then we need to
            # go through an OAUTH step
            if code_start == -1 and (self.access_token is None or self.refresh_token is None):
                return ([html.Div([
                    html.P("Click the button below to authorise the dashboard to connect to your Strava page."),
                    html.P("The access token will be stored in the browser session,"
                           " so that you only have to click this button once"),
                    html.P("If you ever see this page after authorising, it's either because you closed the browser"),
                    html.P("...or because I've been a poor programmer :("),
                    dbc.Button("Go to OAUTH page", id="getOAUTH")
                ])], dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update)

            # If we got this far, and there is an auth-code in the URL, but we have no access/refresh token, then
            # we must've been redirected to the Dash app after going through OAUTH. Let's fetch the tokens.
            if self.access_token is None:
                # If there is a code in the current URL, we snag it and use it to get an access token and such.
                code = current_url[code_start + 5:]
                code_end = code.find("&")
                code = code[0:code_end]

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
                self.expires_timestamp = dt.datetime.fromtimestamp(self.expires_at, dt.timezone.utc)
                self.expires_in = (self.expires_timestamp - dt.datetime.now(dt.timezone.utc)).total_seconds()

            print(f"Access token: {self.access_token}\n"
                  f"Refresh token: {self.refresh_token}\n"
                  f"Expires at: {self.expires_at}\n"
                  f"Expires in: {self.expires_in}\n"
                  f"Expires timestamp: {self.expires_timestamp}")

            if self.expires_in <= 0:
                print("Access token has expired. Need to refresh it.")
                header = {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token,
                }

                response = requests.post('https://www.strava.com/api/v3/oauth/token', data=header).json()
                self.access_token = response['access_token']
                self.refresh_token = response['refresh_token']
                self.expires_at = response['expires_at']
                self.expires_in = response['expires_in']
                self.expires_timestamp = dt.datetime.now() + dt.timedelta(seconds=self.expires_in)

            return ([html.P(f"Found an access token! It's {self.access_token}"),
                     dbc.Button("Fetch athlete data", id="get_data")],
                    self.access_token,
                    self.refresh_token,
                    self.expires_at,
                    self.expires_in,
                    self.expires_timestamp)

        # Add a callback here that fetches athlete data and stores it somewhere.
        # Could perhaps still use a dcc.Store for it, though it may become too much. Local storage possible, perhaps?
        # Or yeet it onto Firebase? Would be nice if it doesn't have to retrieve the data anew each time.
        @self.app.callback(
            Output('hidden_div', 'children'),
            Output('current_url', 'pathname'),
            Input('get_data', 'n_clicks'),
        )
        def getData(n_clicks):
            if n_clicks is None:
                raise dash.exceptions.PreventUpdate

            athlete = self.client.get_athlete()
            print(f"Athlete details:\n"
                  f"Name: {athlete.firstname} {athlete.lastname}\n"
                  f"Gender: {athlete.sex}\n"
                  f"City: {athlete.city}\n"
                  f"Country: {athlete.country}")

            start_date = "2024-01-01T00:00:00Z"
            activities = self.client.get_activities(after=start_date, limit=5)
            pprint(vars(activities))

            print("Fetched activities")
            activity_data = []
            for activity in activities:
                activity_dict = activity.to_dict()
                new_data = [activity_dict.get(x) for x in activity_cols]
                activity_data.append(new_data)

            activity_df = pd.DataFrame(activity_data, columns=activity_cols)
            activity_df['distance'] = activity_df['distance'] / 1000
            activity_df.to_csv("results/activities.csv", sep=';', encoding='utf-8')
            print("Written activities to file.")

            type_list = ['distance', 'time', 'latlng', 'altitude']

            activity_df = activity_df.loc[:, ~activity_df.columns.str.contains('^Unnamed')]

            counter = 0
            polyLineList = []
            distanceList = []
            for x in activity_df['id']:
                counter += 1
                print("Making the map for activity # %d" % counter)
                activityStream = fun.getStream(self.client, type_list, x)
                streamDF = fun.storeStream(type_list, activityStream)
                if streamDF.shape[0] != 0:
                    streamPoly = fun.makePolyLine(streamDF)
                    polyLineList.append(streamPoly)
                    distanceList.append(activity_df.loc[counter - 1, 'distance'])

            activityMap = fun.plotMap(polyLineList, 0, distanceList)
            indexPath = pathlib.Path(__file__).parent / "/templates/index.html"

            activityJSON = activity_df.to_json(orient='index')
            parsed = json.loads(activityJSON)

            # The callback function should end with updating the main page
            raise dash.exceptions.PreventUpdate



    def runApp(self):
        self.app.run_server(debug=True, port=8080)
