from typing import Final
import os
import discord
from dotenv import load_dotenv
from discord import Intents, Embed
from discord.ext import commands, tasks
from discord.ui import View, Button
import pandas as pd
from random import shuffle
import asyncio
import pickle
import atexit
from datetime import datetime, timedelta
import itertools

from user import User
from create_player import create_player
from fetch_stats import fetch_stats

'''
----------------------------------------------------------------

BOT PREPROCESSING

----------------------------------------------------------------
'''
# Constants
DRAFT_ROUNDS = 5
TOTAL_WEEKS = 19

# Load csv for draft
cols = ['PLAYER_FIRST_NAME', 'PLAYER_LAST_NAME', 'POSITION', 'TEAM_CITY', 'TEAM_NAME']
df = pd.read_csv('./all_players.csv', usecols=cols)
df['FULL_NAME'] = (df['PLAYER_FIRST_NAME'].str.strip() + ' ' + df['PLAYER_LAST_NAME'].str.strip()).str.lower()


# Load token from env
load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')

# Bot setup
intents: Intents = Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Initialize variables
channel_id = None
is_draft = False
accounts = {}
users = []
current = 0
draft_rounds = {}
drafted_players = {}
season_matchups = {i:[] for i in range(1, TOTAL_WEEKS + 1)}
current_week = 1


# Save all user data before exit
def save_data():
    with open('user_data.pickle', 'wb') as f:
        pickle.dump((channel_id, accounts, users, draft_rounds, drafted_players, season_matchups, current_week), f)
    print('Data saved to user_data.pickle before exit.')

atexit.register(save_data)

'''
----------------------------------------------------------------

COMMANDS

----------------------------------------------------------------
'''

@bot.command(aliases=['default', 'channel', 'setchannel'])
async def setdefaultchannel(ctx):
    global channel_id
    channel_id = ctx.channel.id
    print('Default channel:', ctx.channel)
    await ctx.send(f'The default channel has been set to {ctx.channel.mention}')

@bot.command(aliases=['new', 'create'])
async def join(ctx, *, arg=''):
    global accounts
    if arg == '':
        await ctx.send('Please enter the command in the following format: `/join <team name>`')
        return
    if str(ctx.author) in accounts.keys():
        await ctx.send('You cannot have more than 2 teams!')
        return
    for user in accounts.values():
        if arg == user.team_name:
            await ctx.send('Team name already taken. Please try another name.')
            return
    new_user = User(str(ctx.author), arg)
    accounts[new_user.name] = new_user
    await ctx.send(f'Welcome {arg}!')

@bot.command(aliases=['delete', 'removeaccount'])
async def deleteaccount(ctx):
    global accounts
    global users
    global drafted_players
    global draft_rounds
    user = str(ctx.author)
    if user in accounts.keys():
        for player in accounts[user].players.values():
            del drafted_players[f'{player.first_name} {player.last_name}']
            player.owner = ''
            del player
        del accounts[user]
    if user in users:
        del draft_rounds[user]
        users.remove(user)
    await ctx.send('Successfully deleted your account. It\'s sad to see you leave!')

@bot.command(aliases=['pro', 'self', 'me', 'team', 'roster', 'lineup'])
async def profile(ctx):
    if str(ctx.author) not in accounts.keys():
        await ctx.send('You do not have a registered profile! Please join the fantasy league using `/join`.')
        return
    user = accounts[str(ctx.author)]
    embed = Embed(title=f'Your Lineup', description=f'{user.team_name}')
    embed.set_thumbnail(url=ctx.author.avatar.replace(size=64).url)
    embed.add_field(name='Starters', value="", inline=False)
    for position in user.roster:
        if len(user.roster[position]) > 0:
            for player in user.roster[position]:
                if user.roster[position][player] == 'starter':
                    embed.add_field(name='', value=f'{player.position}: {player.first_name} {player.last_name}', inline=False)
    embed.add_field(name='Reserves', value="", inline=False)
    for position in user.roster:
        if len(user.roster[position]) > 0:
            for player in user.roster[position]:
                if user.roster[position][player] == 'reserve':
                    embed.add_field(name='', value=f'{player.position}: {player.first_name} {player.last_name}', inline=False)
    await ctx.send(embed=embed)


@bot.command(aliases=['score'])
async def scores(ctx):
    if str(ctx.author) not in accounts.keys():
        await ctx.send('You do not have a registered profile! Please join the fantasy league using `/join`.')
        return
    user = accounts[str(ctx.author)]
    embed = Embed(title=f'Week {current_week} Scores', description=f'{user.team_name}')
    embed.set_thumbnail(url=ctx.author.avatar.replace(size=64).url)
    for position in user.roster:
        if len(user.roster[position]) > 0:
            for player in user.roster[position]:
                if user.roster[position][player] == 'starter':
                    embed.add_field(name=f'{player.first_name} {player.last_name}', value=player.score[current_week], inline=False)
    await ctx.send(embed=embed)


@bot.command()
async def changename(ctx, *, arg):
    global accounts
    for user in accounts.values():
        if arg == user.team_name:
            await ctx.send('Team name already taken. Please try another name.')
            return
    accounts[str(ctx.author)].team_name = arg
    await ctx.send(f'Successfully changed team name to {arg}!')
    


@bot.command(aliases=['r', 'enterdraft'])
async def enter(ctx):
    global is_draft
    global accounts
    if is_draft:
        await ctx.send('You cannot enter the draft once it has started.')
        return
    # Get the user who invoked the command
    user = ctx.author
    if str(user) in users:
        await ctx.send('You are already enrolled in the draft.')
        return
    if str(user) not in accounts.keys():
        await ctx.send('You cannot enroll in the draft without a team!')
        return
    users.append(str(user))
    await ctx.send(f'{user.mention} has entered the draft!')

@bot.command(aliases=['leave', 'leavedraft'])
async def exit(ctx):
    global is_draft
    if is_draft:
        await ctx.send('You cannot exit the draft once it has started.')
        return
    # Get the user who invoked the command
    user = ctx.author
    users.remove(user)
    await ctx.send(f'{user.mention} has been removed from the draft!')

@bot.command(aliases=['draftorder', 'dlist'])
async def draftlist(ctx):
    embed = Embed(title='Draft Participants')
    for i, user in enumerate(users):
        embed.add_field(name=f'{i+1}. {user}', value=f'{accounts[user].team_name}', inline=False)
    await ctx.send(embed=embed)

@bot.command(aliases=['start', 'sd'])
async def startdraft(ctx):
    global is_draft
    global users
    global current
    global draft_rounds

    is_draft = True

    # Randomize draft order
    shuffle(users)
    current = 0

    draft_rounds = {user: 0 for user in users}
    members = []  # Create an empty list to store members

    member = [member for member in ctx.guild.members if member.name == users[current]][0]
    await ctx.send(f'{member.mention}! It is your turn to draft!')


@bot.command(aliases=['d', 'pick'])
async def draft(ctx, *, arg=''):
    global current
    global draft_rounds
    global is_draft
    global drafted_players
    global season_matchups

    max_per_position = {'G': 4, 'F': 4, 'C': 2}


    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel
    
    if not is_draft:
        await ctx.send('You cannot draft before the draft has started!')
        return
    
    if arg == '':
        await ctx.send('Please enter the command in the following format: `/draft <player>`')
        return

    arg = arg.lower()
    user = str(ctx.author)
    
    if user != users[current]:
        await ctx.send('It is not your turn to draft!')
        return

    if arg in df['FULL_NAME'].values:
        index = df[(df['FULL_NAME'] == arg)].index[0]
        first_name = df.loc[index]['PLAYER_FIRST_NAME']
        last_name = df.loc[index]['PLAYER_LAST_NAME']
        player = create_player(first_name, last_name)

        if f'{player.first_name} {player.last_name}' in drafted_players.keys():
            await ctx.send(f'{player.first_name} {player.last_name} has already been drafted!')
            return
        
        if '-' in player.position:
            pos1 = player.position[0]
            pos2 = player.position[2]

            if accounts[user].positions[pos1] == max_per_position[pos1] and accounts[user].positions[pos2] < max_per_position[pos2]:
                player.position = pos2
            
            elif accounts[user].positions[pos1] < max_per_position[pos1] and accounts[user].positions[pos2] == max_per_position[pos2]:
                player.position = pos1

            elif accounts[user].positions[pos1] < max_per_position[pos1] and accounts[user].positions[pos2] < max_per_position[pos2]:
                await ctx.send(f'Please choose the position for this player. **{pos1}** or **{pos2}**?')
                try:
                    repsonse = await bot.wait_for('message', timeout=30.0, check=check)
                    chosen_position = repsonse.content.upper()
                    if chosen_position not in [pos1, pos2]:
                        await ctx.send(f'{player.first_name} {player.last_name} does not play in that postion. Please draft again.')
                        return
                    else:
                        player.position = chosen_position
                except asyncio.TimeoutError:
                    await ctx.send('You took too long to respond. Please draft again.')
                    return
            else:
                await ctx.send(f'You have already drafted the max number of players in both the **{pos1}** and **{pos2}** positions. Please try again!')
                return


        if accounts[user].add_player(player):
            await ctx.send(f'Successfully drafted {first_name} {last_name}!')
            player.owner = accounts[user]
            drafted_players[f'{player.first_name} {player.last_name}'] = player.owner
        else:
            await ctx.send('You have already drafted the max number of players in that position. Please try again!')
            return
        
        draft_rounds[user] += 1
        if all(rounds >= DRAFT_ROUNDS for rounds in draft_rounds.values()): # CHANGE DRAFT_ROUNDS TO INCREASE/DECREASE ROUNDS
            await ctx.send("The draft is complete!")
            is_draft = False
            set_matchups()
            return
        current = (current + 1) % len(users)
        next_user = [member for member in ctx.guild.members if member.name == users[current]][0]
        await ctx.send(f'{next_user.mention}! It is your turn to draft!')
    else:
        await ctx.send(f'Invalid player: {arg}')


@bot.command(aliases=['draftclass', 'class', 'drafted'])
async def draftedplayers(ctx):
    embed = Embed(title='Drafted Players')
    for i, player in enumerate(drafted_players.items()):
        embed.add_field(name=f'{i+1}. {player[0]}', value=f'{player[1].team_name}', inline=False)
    await ctx.send(embed=embed)



@bot.command(aliases=['promote', 'demote', 'change', 'switch'])
async def swap(ctx, *, arg=''):
    if arg == '':
        await ctx.send('Please enter the command in the following format: `/swap <player 1>, <player2>`')
        return
    if ',' not in arg:
        await ctx.send('Command not formatted correctly. Please separate players with a comma.')
        return

    positions = {'G': 0, 'F': 1, 'C': 2}
    arg1, arg2 = arg.split(',')
    arg1 = arg1.strip()
    arg2 = arg2.strip()
    user = accounts[str(ctx.author)]
    if arg1 in user.players and arg2 in user.players:
        p1 = user.players[arg1]
        p2 = user.players[arg2]

        if p1.position != p2.position:
            await ctx.send('Cannot swap players with different positions.')
            return
        
        if user.roster[p1.position][p1] == 'starter' and user.roster[p2.position][p2] == 'reserve':
            user.roster[p1.position][p1] = 'reserve'
            user.roster[p1.position][p2] = 'starter'
            await ctx.send(f'{p2.first_name} {p2.last_name} is now a starter and {p1.first_name} {p1.last_name} is now a reserve.')
            return
        elif user.roster[p1.position][p1] == 'reserve' and user.roster[p2.position][p2] == 'starter':
            user.roster[p1.position][p1] = 'starter'
            user.roster[positions[p1.position]][p2] = 'reserve'
            await ctx.send(f'{p1.first_name} {p1.last_name} is now a starter and {p2.first_name} {p2.last_name} is now a reserve.')
            return
        elif user.roster[p1.position][p1] == 'starter' and user.roster[p2.position][p2] == 'starter':
            await ctx.send(f'Both players are starters. There is no effect.')
            return
        elif user.roster[p1.position][p1] == 'reserve' and user.roster[p2.position][p2] == 'reserve':
            await ctx.send(f'Both players are reserves. There is no effect.')
            return
    else:
        await ctx.send('Could not find one or both of these players.')
        return
            
@bot.command(aliases=['cut', 'waive', 'nightnight'])
async def drop(ctx, *, arg=''):
    global accounts
    global users
    
    user = accounts[str(ctx.author)]

    if arg == '':
        await ctx.send('Please enter the command in the following format: `/drop <player>`')
        return

    arg = arg.lower()
    if arg not in df['FULL_NAME'].values:
        await ctx.send('Player not found!')
        return
    index = df[(df['FULL_NAME'] == arg)].index[0]
    first_name = df.loc[index]['PLAYER_FIRST_NAME']
    last_name = df.loc[index]['PLAYER_LAST_NAME']
    
    if arg not in user.players.keys():
        await ctx.send('You do not own that player!')
        return
    player = user.players[arg]
    if user.drop_player(player):
        player.owner = ''
        del player
        await ctx.send(f'Successfully dropped {first_name} {last_name}.')
        return
    else:
        del player
        await ctx.send(f'Could not drop {first_name} {last_name} from your roster. Please try again.')
        return

    
@bot.command(aliases=['freeagent', 'pickup'])
async def fa(ctx, *, arg=''):
    global accounts
    global is_draft
    max_per_position = {'G': 4, 'F': 4, 'C': 2}

    if is_draft:
        await ctx.send('Cannot sign players from free agency while the draft is in progress.')
        return

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel

    if arg == '':
        await ctx.send('Please enter the command in the following format: `/fa <player>`')
        return
    
    arg = arg.lower()
    user = str(ctx.author)
    if arg not in df['FULL_NAME'].values:
        await ctx.send('Player not found!')
        return
    
    index = df[(df['FULL_NAME'] == arg)].index[0]
    first_name = df.loc[index]['PLAYER_FIRST_NAME']
    last_name = df.loc[index]['PLAYER_LAST_NAME']
    player = create_player(first_name, last_name)

    taken_players = {}
    for account in accounts:
        taken_players.update(accounts[account].players)
    
    
    if arg in taken_players.keys():
        await ctx.send(f'{first_name} {last_name} is not a free agent!')
        return
        
    if '-' in player.position:
        pos1 = player.position[0]
        pos2 = player.position[2]

        if accounts[user].positions[pos1] == max_per_position[pos1] and accounts[user].positions[pos2] < max_per_position[pos2]:
            player.position = pos2
        
        elif accounts[user].positions[pos1] < max_per_position[pos1] and accounts[user].positions[pos2] == max_per_position[pos2]:
            player.position = pos1

        elif accounts[user].positions[pos1] < max_per_position[pos1] and accounts[user].positions[pos2] < max_per_position[pos2]:
            await ctx.send(f'Please choose the position for this player. **{pos1}** or **{pos2}**?')
            try:
                repsonse = await bot.wait_for('message', timeout=30.0, check=check)
                chosen_position = repsonse.content.upper()
                if chosen_position not in [pos1, pos2]:
                    await ctx.send(f'{player.first_name} {player.last_name} does not play in that postion. Please draft again.')
                    return
                else:
                    player.position = chosen_position
            except asyncio.TimeoutError:
                await ctx.send('You took too long to respond. Please draft again.')
                return
        else:
            await ctx.send(f'You already have the max number of players in both the **{pos1}** and **{pos2}** positions. Please try again!')
            return


    if accounts[user].add_player(player):
        await ctx.send(f'Successfully signed {first_name} {last_name} from free agency!')
        player.owner = accounts[user]
    else:
        await ctx.send(f'You already have the max number of players in that position. Please try again!')
        return

    
'''
----------------------------------------------------------------

DAILY STAT GATHERING

----------------------------------------------------------------
'''

@bot.command()
async def stats(ctx, *, arg=''):
    if str(ctx.author) not in accounts.keys():
        await ctx.send('You do not have a registered profile! Please join the fantasy league using `/join`.')
        return
    
    if arg == '':
        user = accounts[str(ctx.author)]
        embed = Embed(title=f'Week {current_week} Scores', description=f'{user.team_name}')
        embed.set_thumbnail(url=ctx.author.avatar.replace(size=64).url)
        for position in user.roster:
            if len(user.roster[position]) > 0:
                for player in user.roster[position]:
                    if user.roster[position][player] == 'starter':
                        embed.add_field(name=f'{player.first_name} {player.last_name}', value=round(player.score[current_week], 1), inline=False)
        await ctx.send(embed=embed)
        return
    user = accounts[str(ctx.author)]
    if arg in user.players.keys():
        player = user.players[arg]
        embed = Embed(title=f'{player.first_name} {player.last_name}\'s Stats for {datetime.now().strftime("%x")}', description='')
        embed.set_thumbnail(url=ctx.author.avatar.replace(size=64).url)
        player_stats = player.get_stats()
        for i, stat in enumerate(['Points', '2 Point FG', '3 Point FG', 'Free Throws Made', 'Rebounds', 'Assists', 'Blocks', 'Steals', 'Turnovers', 'Fouls']):
            embed.add_field(name=f'{stat}: {round(player_stats[i], 1)}', value='', inline=False)

        await ctx.send(embed=embed)
    else:
        await ctx.send(f'Cannot find that player in your roster.')

now = datetime(2024, 2, 6)

async def get_stats():
    global channel_id
    global users
    global accounts
    global current_week
    global now
    channel = bot.get_channel(channel_id)

    # date = datetime.now().strftime('%Y-%m-%d')
    date = now.strftime('%Y-%m-%d') # for testing

    players = []
    for user in accounts.values():
        players.extend(user.get_players())

    players_dict = {player.id: player for player in players}
    
    if fetch_stats(date, players_dict):
        print(f'Successfully retrieved stats for {len(players)} players.')

    for player in players_dict.values():
        player.set_score(current_week)

    await channel.send('Stats for today have been updated!')



# @tasks.loop(seconds=5) # replace parameter to hours=24
# async def update_stats():
#     global now
#     print('DAILY STAT DATE:', now)
#     print('update_stats is now active...')
#     # now = datetime.now()
#     # now = datetime(2024, 2, 18)
#     target_time = now.replace(hour=0, minute=0, second=0, microsecond=1) # replace to time when you want to schedule data fetch (default: 21:00)

#     if now > target_time:
#         target_time += timedelta(hours=24) # place with days=1
    

#     time_until_task = (target_time - now).total_seconds()
#     await asyncio.sleep(time_until_task)

#     await get_stats()
#     now += timedelta(days=1)
#     await asyncio.sleep(5) # replace with 24 * 3600 (1 day in seconds)
    

@tasks.loop(hours=24) # replace parameter to hours=24
async def update_stats():
    now = datetime.now()
    print('update_stats is now active...')
    target_time = now.replace(hour=23, minute=0, second=0, microsecond=0) # replace to time when you want to schedule data fetch (default: 21:00)

    if now > target_time:
        target_time += timedelta(hours=24) # place with days=1
    

    time_until_task = (target_time - now).total_seconds()
    await asyncio.sleep(time_until_task)

    await get_stats()
    await asyncio.sleep(24*3600) # replace with 24 * 3600 (1 day in seconds)


'''
----------------------------------------------------------------

WEEKLY MATCHUPS

----------------------------------------------------------------
'''

def create_embed(matchup, week_num, page):
    global season_matchups
    # print(matchup)
    # print(week_num)
    user1 = accounts[matchup[page][0]]
    user2 = accounts[matchup[page][1]]
    embed = Embed(title=f'Week {week_num} Matchups', description=f'{user1.team_name} vs. {user2.team_name}')

    for (pos1, players1), (pos2, players2) in zip(user1.roster.items(), user2.roster.items()):
        if len(user1.roster[pos1]) > 0 and len(user2.roster[pos2]) > 0:
            for player1, player2 in zip(user1.roster[pos1], user2.roster[pos2]):
                if user1.roster[pos1][player1] == 'starter' and user2.roster[pos2][player2] == 'starter':
                    embed.add_field(name=f'{player1.first_name} {player1.last_name}', value=f'{round(player1.score[week_num], 1)}', inline=True)
                    embed.add_field(name=f'{player2.first_name} {player2.last_name}', value=f'{round(player2.score[week_num], 1)}', inline=True)
                    embed.add_field(name='', value='', inline=False)

    return embed


class PaginationView(View):
    def __init__(self, pages):
        super().__init__()
        self.current_page = 0
        self.pages = pages

        # Add buttons to the view
        self.add_item(PreviousButton())
        self.add_item(NextButton())

    # Method to update the embed when buttons are clicked
    async def update_embed(self, interaction):
        embed = create_embed(self.pages, current_week, self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)

class NextButton(Button):
    def __init__(self):
        super().__init__(label="Next", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        # Cast self.view to PaginationView to access custom methods
        view: PaginationView = self.view
        # Increment the current page
        view.current_page = (view.current_page + 1) % len(view.pages)
        # Update the embed to the next page
        await view.update_embed(interaction)

class PreviousButton(Button):
    def __init__(self):
        super().__init__(label="Previous", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        # Cast self.view to PaginationView to access custom methods
        view: PaginationView = self.view
        # Decrement the current page
        view.current_page = (view.current_page - 1) % len(view.pages)
        # Update the embed to the previous page
        await view.update_embed(interaction)



def set_matchups():
    global users
    global season_matchups
    all_matchups = list(itertools.combinations(users, 2))
    used_matchups = set()
    used_players_per_week = {week: set() for week in range(1, TOTAL_WEEKS + 1)}

    def get_next_matchups(used, all_matchups):
        unused = [match for match in all_matchups if match not in used]

        if not unused:
            used.clear()
            unused = all_matchups[:]


        shuffle(unused)
        return unused
    
    for week in range(1, TOTAL_WEEKS+1): # total weeks in regular season
        # Restart matchups if all are used and season is still ongoing
        if len(used_matchups) == len(all_matchups):
            used_matchups.clear()
        next_matchups = get_next_matchups(used_matchups, all_matchups)

        week_matchups = []
        for matchup in next_matchups:
            user1, user2 = matchup
            
            if user1 not in used_players_per_week[week] and user2 not in used_players_per_week[week]:
                week_matchups.append(matchup)  # Add valid matchup
                used_players_per_week[week].add(user1)  # Mark users as used this week
                used_players_per_week[week].add(user2)  # Mark users as used this week
                used_matchups.add(matchup)  # Add to used matchups

            # Stop if we have reached half the number of users
            if len(week_matchups) == len(users) // 2:
                break

        season_matchups[week].extend(week_matchups)

async def matchups():
    # function will update scores for each matchup
    global channel_id
    global current_week
    global season_matchups
    global accounts
    channel = bot.get_channel(channel_id)

    content_list = season_matchups[current_week]
    embed = create_embed(content_list, current_week, 0)

    await channel.send(embed=embed, view=PaginationView(content_list))

@bot.command(aliases=['show'])
async def showmatchups(ctx):
    # function will update scores for each matchup
    global current_week
    global season_matchups

    content_list = season_matchups[current_week]
    embed = create_embed(content_list, current_week, 0)

    await ctx.send(embed=embed, view=PaginationView(content_list))


def determine_winner(week):
    global season_matchups

    matchups = season_matchups[week]
    winners = []
    for matchup in matchups:
        user1 = accounts[matchup[0]]
        user2 = accounts[matchup[1]]
        u1_score = 0
        u2_score = 0

        for (pos1, players1), (pos2, players2) in zip(user1.roster.items(), user2.roster.items()):
            if len(user1.roster[pos1]) > 0 and len(user2.roster[pos2]) > 0:
                for player1, player2 in zip(user1.roster[pos1], user2.roster[pos2]):
                    if user1.roster[pos1][player1] == 'starter' and user2.roster[pos2][player2] == 'starter':
                        u1_score += player1.score[week]
                        u2_score += player2.score[week]
        user1.scores[week] = u1_score
        user2.scores[week] = u2_score
        if u1_score > u2_score:
            user1.record['Wins'] += 1
            user2.record['Losses'] += 1
            winners.append(user1)
        elif u2_score > u1_score:
            user2.record['Wins'] += 1
            user1.record['Losses'] += 1
            winners.append(user2)
        else:
            user1.record['Ties'] += 1
            user2.record['Ties'] += 1
            winners.append('Tie')
    return winners

async def show_winners(winners, week):
    global season_matchups
    global channel_id
    channel = bot.get_channel(channel_id)

    matchups = season_matchups[week]
    embed = Embed(title=f'Week {week} Winners')
    for matchup, winner in zip(matchups, winners):
        user1 = accounts[matchup[0]]
        user2 = accounts[matchup[1]]
        embed.add_field(name=f'{user1.name} vs. {user2.name}', value=f'Winner: {winner if type(winner) == str else winner.name  + " (" + str(winner.record["Wins"]) + "-" + str(winner.record["Losses"]) + "-" + str(winner.record["Ties"]) + ")"}', inline=False)
    
    await channel.send(embed=embed)


# @tasks.loop(seconds=40)
# async def weekly_matchups():
#     global now
#     global current_week
#     global season_matchups
#     if current_week > TOTAL_WEEKS:
#         winners = determine_winner(current_week - 1)
#         await show_winners(winners, current_week - 1)
#         await stop_tasks()
#         return
#     # print('setting matchups')
#     # set_matchups()
#     # return
#     # season_matchups = {i:[] for i in range(1, TOTAL_WEEKS + 1)}
#     print('WEEKLY MATCHUPS DATE:', now)
#     print(current_week)
#     print('weekly_matchups is now active...')
#     if current_week > 1:
#         winners = determine_winner(current_week - 1)
#         await show_winners(winners, current_week - 1)
    
#     # now = datetime.now()
#     now = datetime(2024, 2, 6)
#     target_time = now.replace(hour=0, minute=0, second=0, microsecond=0)

#     if now > target_time:
#         target_time += timedelta(seconds=(60*60*24*7)+4)
    

#     time_until_task = (target_time - now).total_seconds()
#     await asyncio.sleep(time_until_task)

#     await matchups()
#     await asyncio.sleep(40)
#     current_week += 1


@tasks.loop(hours=24*7)
async def weekly_matchups():
    global current_week
    if current_week > TOTAL_WEEKS:
        winners = determine_winner(current_week - 1)
        await show_winners(winners, current_week - 1)
        await stop_tasks()
        return
    now = datetime.now()
    print('weekly_matchups is now active...')
    if current_week > 1:
        winners = determine_winner(current_week - 1)
        show_winners(winners, current_week - 1)

    target_time = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if now > target_time:
        target_time += timedelta(weeks=1)
    

    time_until_task = (target_time - now).total_seconds()
    await asyncio.sleep(time_until_task)

    await matchups()

    await asyncio.sleep(24 * 7 * 3600)
    current_week += 1



# Wait for regular season start
async def wait_until_season_start():
    global season_matchups
    # Define the target date
    target_date = datetime(2024, 10, 22) # season start is 2024, 10, 22
    
    while True:
        now = datetime.now()
        # If the current date is past the target date, start the loops
        if now >= target_date and season_matchups[1] != []:
            print(f"Target date reached: {target_date}")
            weekly_matchups.start()  # Start the weekly matchups loop
            update_stats.start()     # Start the update stats loop
            break
        # Check every hour (3600 seconds)
        await asyncio.sleep(3600)


async def stop_tasks():
    print('tasks stopped!')
    weekly_matchups.stop()  # Stop the weekly matchups loop
    update_stats.stop() 
    await announce_winner()


# Announce winner of fantasy league
async def announce_winner():
    global accounts
    global channel_id

    channel = bot.get_channel(channel_id)

    records = {}
    max_wins = -1
    max_ties = -1
    winners = []

    
    for user in accounts.values():
        records[user] = user.record

    for player, stats in records.items():
        wins = stats['Wins']
        ties = stats['Ties']

        # If this player has more wins, they become the only winner
        if wins > max_wins or (wins == max_wins and ties > max_ties):
            winners = [player]  # Reset winners list with current player
            max_wins = wins
            max_ties = ties
        # If this player has the same wins and ties as the current max, add them to the list
        elif wins == max_wins and ties == max_ties:
            winners.append(player)

    if len(winners) == 1:
        await channel.send(f'The winner of the fantasy league is {winners[0].name}! Congratulations!')
    else:
        await channel.send(f'The fantasy league winners are {", ".join([winner.name for winner in winners])}! Congratulations!')


# Handling Bot start up
@bot.event
async def on_ready() -> None:
    global accounts
    global users
    global draft_rounds
    global drafted_players
    global channel_id
    global season_matchups
    global current_week

    print(f'{bot.user} is now running!')
    # Load data from pickle file

    if os.path.exists('user_data.pickle') and os.path.getsize('user_data.pickle') > 0:
        print('Loaded data from user_data.pickle')
        with open('user_data.pickle', 'rb') as f:
            channel_id, accounts, users, draft_rounds, drafted_players, season_matchups, current_week = pickle.load(f)
            print()
            print('Channel ID:', channel_id)
            print('Users:', users)
            print('Accounts:', accounts)
            print('Draft Rounds:', draft_rounds)
            print('Drafted Players', drafted_players)
            print('Season Matchups', season_matchups)
            print('Current Week:', current_week)
            print()
    if channel_id is None:
        for guild in bot.guilds:
            first_channel = next((channel for channel in guild.text_channels if channel.permissions_for(guild.me).send_messages), None)
            if first_channel:
                await first_channel.send('No default channel is set. Please use `/setdefaultchannel` in the desired channel to set it.')
                channel_id = first_channel.id
                print(f'channel ID set to first channel: {channel_id}')
                break

    bot.loop.create_task(wait_until_season_start())
        
        

# Main entry point
def main() -> None:
    bot.run(TOKEN)

if __name__ == '__main__':
    main()
