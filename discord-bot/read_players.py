import pandas as pd

cols = ['PLAYER_FIRST_NAME', 'PLAYER_LAST_NAME', 'POSITION', 'TEAM_CITY', 'TEAM_NAME']
df = pd.read_csv('./all_players.csv', usecols=cols)

df['Full_Name'] = (df['PLAYER_FIRST_NAME'].str.strip() + ' ' + df['PLAYER_LAST_NAME'].str.strip())
df['Full_Name_Lower'] = (df['PLAYER_FIRST_NAME'].str.strip() + ' ' + df['PLAYER_LAST_NAME'].str.strip()).str.lower()
df['TEAM'] = df['TEAM_CITY'].str.strip() + ' ' + df['TEAM_NAME'].str.strip()

print(df[(df['Full_Name_Lower'] == 'lebron james')].index[0])
print(df.loc[267]['PLAYER_FIRST_NAME'], df.loc[267]['PLAYER_LAST_NAME'])
