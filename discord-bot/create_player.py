from user import User
from player import Player

import requests

url = "https://api.balldontlie.io/v1/players"

def create_player(first, last):
    params = {
    "first_name": first,
    "last_name": last
    }

    headers = {
        "Authorization": "0705fe86-f151-442a-99da-6c5dfdadea02"  # Replace with your API key if needed
    }

    # Send a GET request to the API
    response = requests.get(url, params=params, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        # get data
        id = data['data'][0]['id']
        first_name = data['data'][0]['first_name']
        last_name = data['data'][0]['last_name']
        team = data['data'][0]['team']['full_name']
        position = data['data'][0]['position']
        jersey_number = data['data'][0]['jersey_number']
        height = data['data'][0]['height']
        weight = data['data'][0]['weight']
        college = data['data'][0]['college']
        country = data['data'][0]['country']

        return Player(id, first_name, last_name, team, position, jersey_number, height, weight, college, country)
    else:
        print(f"Error: {response.status_code} - {response.text}")