from player import Player
from discord import Intents, Message, Embed, Interaction
from discord.ext import commands

# Bot setup
intents: Intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

class User:
    def __init__(self, name, team_name) -> None:
        self.name = name
        self.team_name = team_name
        self.players = {}
        self.roster = {'G': {}, 'F': {}, 'C': {}}
        self.positions = {'G': 0, 'F': 0, 'C': 0}
        self.record = {'Wins': 0, 'Losses': 0, 'Ties': 0}
        self.scores = {i:0 for i in range(1, 20)}

    def add_player(self, p):
        # add checking
        # roster includes starting 5 and 1 sub per position
        if p.position == 'G':
            if self.positions[p.position] < 4:
                self.roster['G'][p] = 'starter' if len(self.roster['G']) < 2 else 'reserve'
                self.positions[p.position] += 1
                self.players[(p.first_name + ' ' + p.last_name).lower()] = p
                return True
            else:
                return False
        elif p.position == 'F':
            if self.positions[p.position] < 4:
                self.roster['F'][p] = 'starter' if len(self.roster['F']) < 2 else 'reserve'
                self.positions[p.position] += 1
                self.players[(p.first_name + ' ' + p.last_name).lower()] = p
                return True
            else:
                return False
        elif p.position == 'C':
            if self.positions[p.position] < 2:
                self.roster['C'][p] = 'starter' if len(self.roster['C']) < 1 else 'reserve'
                self.positions[p.position] += 1
                self.players[(p.first_name + ' ' + p.last_name).lower()] = p
                return True
            else:
                return False

    def drop_player(self, p):
        pos = {'G': 0, 'F': 1, 'C': 2}
        player_pos = p.position
        
        first_name = p.first_name.lower()
        last_name = p.last_name.lower()

        del self.players[f'{first_name} {last_name}']
        self.positions[player_pos] -= 1

        if self.roster[player_pos][p] == 'starter':
            del self.roster[player_pos][p]
            # promote reserve to starter
            for player in self.roster[player_pos]:
                if self.roster[player_pos][player] == 'reserve':
                    self.roster[player_pos][player] = 'starter'
                    return True
            return True
        elif self.roster[player_pos][p] == 'reserve':
            del self.roster[player_pos][p]
            return True
        return False
    
    def get_players(self):
        starters = []
        for position in self.roster:
            for player in self.roster[position]:
                if self.roster[position][player] == 'starter':
                    starters.append(player)
        return list(self.players.values())