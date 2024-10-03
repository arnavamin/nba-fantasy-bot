from user import User
from player import Player

import requests

url = "https://api.balldontlie.io/v1/stats"

def fetch_stats(date, players_dict):
    ids = players_dict.keys()
    
    params = {
    "player_ids[]": ids,
    "start_date": date,
    "end_date": date
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
        # get ids and link data from ids to player ids
        for player in players_dict.values():
            player.points = 0
            player.fg2m = 0
            player.fg3m = 0
            player.ftm = 0
            player.rebounds = 0
            player.assists = 0
            player.blocks = 0
            player.steals = 0
            player.turnovers = 0
            player.fouls = 0

        if data['data'] == []:
            return True
        else:
            for player_data in data['data']:
                player = players_dict[player_data['player']['id']]
                player.points = player_data['pts']
                player.fg2m = player_data['fgm'] - player_data['fg3m']
                player.fg3m = player_data['fg3m']
                player.ftm = player_data['ftm']
                player.rebounds = player_data['reb']
                player.assists = player_data['ast']
                player.blocks = player_data['blk']
                player.steals = player_data['stl']
                player.turnovers = player_data['turnover']
                player.fouls = player_data['pf']
            return True
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return False