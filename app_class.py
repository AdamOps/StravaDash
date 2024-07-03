import dash
from dash import Input, Output, State, ctx

from stravalib import Client
import datetime as dt
import requests

import pandas as pd
import json

from static_layout import *
from parameters import *
import functions as fun
import debug_functions as defun


class DashApp:
    def __init__(self, _client_id, _client_secret, _client_refresh):
        # Authentication details
        self.client_id = _client_id
        self.client_secret = _client_secret
        self.client_refresh = _client_refresh

        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self.expires_in = None
        self.already_authorised = False

        # Track the current state of the app
        self.logged_in = False

        # Strava data
        self.client = Client()
        self.athlete = None

        # Generate app instance
        self.app = dash.Dash(__name__,
                             external_stylesheets=[dbc.themes.FLATLY],
                             suppress_callback_exceptions=True)

        # Initial layout
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
                dcc.Store(id='already_authorised', data=False),
                dcc.Store(id='logged_in', storage_type='session', data=False),

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

        # Generate all callbacks
        self.addCallbacks()

    # Define methods here. The final method is the one generating all callbacks
    def setTokens(self, response, request_type) -> None:
        # Store the various bits of information into separate variables, for ease.
        # Some of the responses give the same structure, but Strava API is weird.
        self.access_token = response['access_token']
        self.refresh_token = response['refresh_token']
        self.already_authorised = True

        if request_type == "authorise":
            self.expires_at = dt.datetime.fromtimestamp(response['expires_at'], dt.timezone.utc)
            self.expires_in = (self.expires_at - dt.datetime.now(dt.timezone.utc)).total_seconds()
        elif request_type == "refresh":
            self.expires_at = response['expires_at']
            self.expires_in = response['expires_in']

    def genPolyLineList(self, base_list, fetch_data_types, id_list):
        if base_list is None:
            base_list = []
        if fetch_data_types is None:
            fetch_data_types = ['latlng']
        if len(id_list) == 0:
            print("Passed an empty id-list. Breaking out of the function and returning None")
            return None

        counter = 0
        for activity_id in id_list:
            counter += 1
            print("Making the map for activity # %d" % counter)
            activity_stream = fun.getStream(_client=self.client, _fetch_data_types=fetch_data_types,
                                            _activity_id=activity_id)
            stream_df = fun.storeStream(fetch_data_types, activity_stream)
            if stream_df.shape[0] != 0:
                streamPoly = fun.makePolyLine(stream_df)
                base_list.append(streamPoly)
                # distanceList.append(activity_df.loc[counter - 1, 'distance'])
        return base_list

    def addCallbacks(self):
        @self.app.callback(
            [
                Output('current_url', 'href', allow_duplicate=True)
            ],
            [
                Input('getOAUTH', 'n_clicks')
            ],
            [
                State('already_authorised', 'data'),

            ],
            prevent_initial_call=True, )
        def startOAUTH(n_clicks, already_authorised):
            if n_clicks is None or already_authorised:
                raise dash.exceptions.PreventUpdate

            # print("Processing OAUTH")
            authorise_url = self.client.authorization_url(
                client_id=self.client_id,
                redirect_uri='http://127.0.0.1:8080/',
                approval_prompt='auto',
                scope=['read_all', 'profile:read_all', 'activity:read_all']
            )

            # Need to implement a check for whether the access_token has expired and needs to be refreshed, which
            # shouldn't be all that complicated.
            return [authorise_url]

        @self.app.callback(
            [
                Output('page_content', 'children', allow_duplicate=True),
                Output('navbar_links', 'children'),
                Output('current_url', 'href'),
                Output('current_url', 'refresh'),
            ],
            [
                Input('init_load_timer', 'n_intervals'),
            ],
            [
                State('current_url', 'href'),
                State('logged_in', 'data'),
            ],
            prevent_initial_call=True,
        )
        def initialStateCheck(n_intervals, current_url, logged_in):
            print("Checking whether this nonsense is getting triggered")
            # Failsafe, to make sure there's no random initial call.
            # !! NB: The current code adds an HTML file with a map to the /assets/ folder, which triggers a
            # hot reload. Had to disable that when running the app instance !!
            trigger_id = ctx.triggered[0]['prop_id'].split(".")[0]
            if trigger_id is None or logged_in:
                print("Callback got triggered, but it ain't updating.")
                raise dash.exceptions.PreventUpdate

            # Look for the auth-code in the current URL
            if current_url is not None:
                code_start = current_url.find("code=")
            else:
                code_start = -1

            # If there is no code in the URL, and we don't already have an access/refresh token, then we need to
            # go through an OAUTH step
            if code_start == -1 and (self.access_token is None or self.refresh_token is None):
                return [
                    dbc.Container([
                        html.Br(),
                        html.P("Click the button below to authorise the dashboard to connect to your Strava page."),
                        dbc.Button("Go to OAUTH page", id="getOAUTH")
                    ]),
                    navbar_links_init,
                    dash.no_update,
                    dash.no_update
                ]

            # If we got this far, and there is an auth-code in the URL, but we have no access/refresh token, then
            # we must've been redirected to the Dash app after going through OAUTH. Let's fetch the tokens.
            if self.access_token is None:
                # If there is a code in the current URL, we snag it and use it to get an access token and such.
                code = current_url[code_start + 5:]
                code_end = code.find("&")
                code = code[0:code_end]

                # Get an access token and a refresh token. This will let us access all the athlete information.
                response = self.client.exchange_code_for_token(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    code=code
                )
                self.setTokens(response=response, request_type="authorise")
            elif self.expires_in <= 0:
                print("Access token has expired. Need to refresh it.")
                header = {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token,
                }
                response = requests.post('https://www.strava.com/api/v3/oauth/token', data=header).json()
                self.setTokens(response=response, request_type="refresh")

            return [
                dbc.Container([
                    html.Br(),
                    dbc.Button("Fetch athlete data", id="get_data")
                ]),
                navbar_links_logged_in,
                "run",
                False
            ]

        # Add a callback here that fetches athlete data and stores it somewhere.
        # Could perhaps still use a dcc.Store for it, though it may become too much. Local storage possible, perhaps?
        # Or yeet it onto Firebase? Would be nice if it doesn't have to retrieve the data anew each time.
        @self.app.callback(
            Output('page_content', 'children', allow_duplicate=True),
            Output('logged_in', 'data'),
            Input('get_data', 'n_clicks'),
            prevent_initial_call=True
        )
        def getData(n_clicks):
            if n_clicks is None:
                raise dash.exceptions.PreventUpdate

            # Fetch the athlete, in case we want to do cool things with it.
            self.athlete = self.client.get_athlete()

            # Get the gear, write the summary data to a JSON file and return a list of IDs (for a more detailed fetch)
            shoe_id_list = defun.writeShoeData(self.athlete)
            gear_list = []
            for gear_id in shoe_id_list:
                new_gear = self.client.get_gear(gear_id=gear_id)
                gear_list.append(new_gear.to_dict())

            # Optionally: Write all the gear info to a file
            with open("ref/gear_data.json", "w", encoding="utf-8") as file:
                json.dump(gear_list, file, ensure_ascii=False, indent=4)


            end_date = dt.datetime.now()
            start_date = dt.datetime.now() - dt.timedelta(weeks=4)

            # This code chunk fetches activities within from the start date till the end date.
            activities = self.client.get_activities(after=start_date, before=end_date, limit=50)
            activity_data = []
            for activity in activities:
                activity_dict = activity.to_dict()
                new_data = [activity_dict.get(x) for x in activity_cols]
                activity_data.append(new_data)

            # Optional function call to write the activity data into a JSON file, for reference.
            defun.writeActivityDict(activities)

            activity_df = pd.DataFrame(activity_data, columns=activity_cols)
            activity_df['distance'] = activity_df['distance'] / 1000
            activity_df.to_csv("results/activities.csv", sep=';', encoding='utf-8')
            activity_df = activity_df.loc[:, ~activity_df.columns.str.contains('^Unnamed')]

            # Split the activity dataframe up by activity type (Run, Bike, other)
            run_id_list = activity_df.loc[activity_df['type'] == 'Run']['id']
            ride_id_list = activity_df.loc[activity_df['type'] == 'Ride']['id']

            # Fetch the activity-streams (i.e. location coordinates and such)
            type_list = ['distance', 'time', 'latlng', 'altitude', 'heartrate']

            run_polyline_list = []
            ride_polyline_list = []

            run_polyline_list = self.genPolyLineList(base_list=run_polyline_list,
                                                     fetch_data_types=type_list,
                                                     id_list=run_id_list)
            ride_polyline_list = self.genPolyLineList(base_list=ride_polyline_list,
                                                      fetch_data_types=type_list,
                                                      id_list=ride_id_list)

            # Generate a map that displays medium-res polylines for all activities.
            # This part is Folium-based, and I'm not sure whether I like that.
            run_activity_map = fun.plotMap(run_polyline_list)
            try:
                run_activity_map.save('assets/run_example.html')
            except:
                print("run_activity_map is empty")

            ride_activity_map = fun.plotMap(ride_polyline_list)
            try:
                ride_activity_map.save('assets/ride_example.html')
            except:
                print("ride_activity_map is empty")

            # activityJSON = activity_df.to_json(orient='index')
            # parsed = json.loads(activityJSON)

            # Update the main page by showing a map with the fetched activities.
            return (html.Div([html.Iframe(src='assets/run_example.html', style={'height': '1000px', 'width': '100%'})]),
                    True)
            # raise dash.exceptions.PreventUpdate

        @self.app.callback(
            Output('page_content', 'children', allow_duplicate=True),
            Input('current_url', 'pathname'),
            State('logged_in', 'data'),
            prevent_initial_call=True
        )
        def navbarLinks(current_url, logged_in):
            trigger_id = ctx.triggered[0]['prop_id'].split(".")[0]
            if trigger_id is None or not logged_in:
                raise dash.exceptions.PreventUpdate

            print(f"current_url: {current_url}")

            if current_url == "/runs":
                return html.Div([
                    html.Iframe(src='assets/run_example.html', style={'height': '1000px', 'width': '100%'})
                ])
            elif current_url == "/rides":
                return html.Div([
                    html.Iframe(src='assets/ride_example.html', style={'height': '1000px', 'width': '100%'})
                ])
            elif current_url == "/gear":
                return html.Div([
                    html.P("Work in progress.")
                ])
            else:
                print("Invalid URL.")
                return dash.no_update

    def runApp(self):
        self.app.run_server(debug=True, port=8080, dev_tools_hot_reload=False)
