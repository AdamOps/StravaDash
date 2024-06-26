import os
from dotenv import load_dotenv

import requests
import urllib3
import webbrowser

import pandas as pd
from pandas import json_normalize
from flask import request
from stravalib import Client


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv('../.env')

CLIENT_ID: int = os.getenv('CLIENT_ID')
CLIENT_SECRET: str = os.getenv('CLIENT_SECRET')
REFRESH_TOKEN: str = os.getenv('REFRESH_TOKEN')

request_url = "https://www.strava.com/oauth/token"
activities_url = "https://www.strava.com/api/v3/athlete/activities"
auth_url = "https://www.strava.com/oauth/authorize"

payload = {
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'refresh_token': REFRESH_TOKEN,
    'grant_type': 'refresh_token',
    'f': 'json'
}

payload_auth = {
    'client_id': CLIENT_ID,
    'redirect_uri': 'localhost',
    'response_type': 'code',
    'approval_prompt': 'auto',
    'scope': 'read',
}

res = requests.post(request_url, data=payload, verify=False)
access_token = res.json()['access_token']

res2 = requests.post(auth_url, data=payload_auth, verify=False)

print(res.json())
print(res2)
# print(access_token)


data = {
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'code': 'ReplaceWithCode',
    'grant_type': 'authorization_code',
}

response = requests.post('https://www.strava.com/api/v3/oauth/token', data=data)

print(response)

exit ()

header = {'Authorization': 'Bearer ' + str(access_token)}

data = []
page_index = 1
new_results = True

while new_results:
    print(f"Fetching results from page {page_index}")
    fetch_strava = requests.get(
        activities_url,
        headers=header,
        params={'per_page': 200, 'page': page_index}
    ).json()

    print(fetch_strava)

    new_results = fetch_strava
    data.extend(fetch_strava)
    page_index += 1
    if page_index >= 3:
        new_results = False

flattened_data = json_normalize(data)
dataframe = pd.DataFrame(flattened_data)

dataframe.to_excel("results/strava_data.xlsx")

exit()


# client = Client()
# auth_url = client.authorization_url(
#     client_id=CLIENT_ID,
#     redirect_uri='http://127.0.0.1:5000/authorization',
#     approval_prompt='auto',
#     scope=['read_all', 'profile:read_all', 'activity:read_all']
# )
#
# print(f"auth_url: {auth_url}")

#
# token_response = client.exchange_code_for_token(client_id=CLIENT_ID,
#                                                 client_secret=CLIENT_SECRET,
#                                                 code=CODE)
#
# access_token = token_response['access_token']
# refresh_token = token_response['refresh_token']
#
# specific_client = Client(access_token=STORED_ACCESS_TOKEN)
# current_athlete = client.get_athlete()
