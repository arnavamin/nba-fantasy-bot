# score multipliers
FG2M_MULT = 2
FG3M_MULT = 3
FTM_MULT = 1
REBOUNDS_MULT = 1.2
ASSISTS_MULT = 1.5
BLOCKS_MULT = 2
STEALS_MULT = 2
TURNOVERS_MULT = -1
FOULS_MULT = -1

class Player:
    def __init__(self, id, first_name, last_name, team, position, jersey_number, height, weight, college, country) -> None:
        # player info
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.team = team
        self.position = position
        self.jersey_number = jersey_number
        self.height = height
        self.weight = weight
        self.college = college
        self.country = country
        self.owner = ''
        # stats
        self.points = 0
        self.fg2m = 0
        self.fg3m = 0
        self.ftm = 0
        self.rebounds = 0
        self.assists = 0
        self.blocks = 0
        self.steals = 0
        self.turnovers = 0
        self.fouls = 0
        self.score = {i:0 for i in range(1, 20)}
    def set_stats(self, points, fg2m, fg3m, ftm, rebounds, assists, blocks, steals, turnovers, fouls):
        self.points = points
        self.fg2m = fg2m
        self.fg3m = fg3m
        self.ftm = ftm
        self.rebounds = rebounds
        self.assists = assists
        self.blocks = blocks
        self.steals = steals
        self.turnovers = turnovers
        self.fouls = fouls

    def clear_stats(self):
        self.points, self.fg2m, self.fg3m, self.ftm, self.rebounds, self.assists, self.blocks, self.steals, self.turnovers, self.fouls = 0

    def get_stats(self):
        return self.points, self.fg2m, self.fg3m, self.ftm, self.rebounds, self.assists, self.blocks, self.steals, self.turnovers, self.fouls
    
    def calc_score(self):
        return round(sum([self.fg2m * FG2M_MULT, self.fg3m * FG3M_MULT, self.ftm * FTM_MULT, round(self.rebounds * REBOUNDS_MULT, 1), round(self.assists * ASSISTS_MULT, 1), self.blocks * BLOCKS_MULT, self.steals * STEALS_MULT, self.turnovers * TURNOVERS_MULT, self.fouls * FOULS_MULT]), 1)
    
    def set_score(self, week):
        self.score[week] += self.calc_score() # change to = and change date to now if you want to clear stats

    def __repr__(self) -> str:
        return f'{self.first_name} {self.last_name} #{self.jersey_number}\n{self.position}, {self.team}\n{self.height}, {self.weight} lbs\nEducation: {self.college}\nCountry: {self.country}'