from riotwatcher import RiotWatcher
from IPython.display import display, HTML
from IPython.display import clear_output
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot

import plotly.graph_objs as go
import numpy as np
import pandas as pd
import urllib3
import time

init_notebook_mode(connected=True)

class Tratamiento:

    df_datos = None
    df_player_data = None
    df_games_list = None
    df_participant_identities = None
    df_teams = None
    df_participants = None
    df_games_data = None
    df_champions = None
    player_id = None
    
    def get_timestamp_gameid(self,GameID):
        return self.df_games_list[self.df_games_list['gameId'] == GameID].reset_index().loc[0,'timestamp']

    def load_data(self, Dir):
        self.df_datos = pd.ExcelFile(Dir) 
        self.df_player_data = pd.read_excel(self.df_datos, 'player_data')
        self.df_games_list = pd.read_excel(self.df_datos, 'games_list')
        self.df_participant_identities = pd.read_excel(self.df_datos,'participant_identities')
        self.df_teams = pd.read_excel(self.df_datos, 'teams')
        self.df_participants = pd.read_excel(self.df_datos, 'participants')
        self.df_games_data = pd.read_excel(self.df_datos, 'games_data')
        self.player_id = self.df_player_data['accountId'][0]
        self.df_champions = pd.read_csv('champs.csv', index_col=0)

    def __init__(self, Dir):
        self.load_data(Dir)
        self.df_participants['timestamp'] = self.df_participants['gameId'].apply(lambda row: self.get_timestamp_gameid(row))

    def get_kda_champion(self, ChampId):
        partidas = self.df_participants[self.df_participants['championId'] == ChampId]
        partidas = partidas[partidas['participant_account_id'] == self.player_id]
        partidas = pd.DataFrame([partidas['assists'].sum(), partidas['deaths'].sum(), partidas['kills'].sum()]).T
        kda = (partidas.iloc[0,0] + partidas.iloc[0,2]) / partidas.iloc[0,1]
        return round(kda, 2)

    def get_champ_name_by_id(self, ChampId):
        return self.df_champions[str(ChampId)]['key']

    
    def add_champ_name(self, Dataframe):
        Dataframe['ChampName'] = Dataframe['championId'].apply(lambda row: self.get_champ_name_by_id(row)) 
        return Dataframe

    def get_worst_champs(self):
        games = self.df_participants[self.df_participants['participant_account_id'] == self.player_id]
        games = games.reset_index(drop=True)
        lost_games = games[games['win'] == False]
        champions = pd.DataFrame(lost_games['championId'])
        champions = champions.groupby(['championId']).size().reset_index(name='perdidas')
        champions = champions.sort_values('perdidas', ascending=False)
        champions = self.add_champ_name(champions)
        champions = champions.reset_index(drop=True)
        return champions
    
    def get_best_champs(self):
        games = self.df_participants[self.df_participants['participant_account_id'] == self.player_id]
        games = games.reset_index(drop=True)
        won_games = games[games['win'] == True]
        champions = pd.DataFrame(won_games['championId'])
        champions = champions.groupby(['championId']).size().reset_index(name='ganadas')
        champions = champions.sort_values('ganadas', ascending=False)
        champions = self.add_champ_name(champions)
        champions = champions.reset_index(drop=True)
        return champions

    def get_win_loss_games(self):
        winners = pd.DataFrame()
        winners['teamId'] = self.df_teams['teamId']
        winners['gameId'] = self.df_teams['gameId']
        winners = winners.reset_index(drop=True)
        player_game = self.df_participants[self.df_participants['participant_account_id'] == self.player_id]
        player_game = player_game.reset_index(drop=True)
        wins = len(player_game[player_game['win'] == True])
        losses = len(player_game[player_game['win'] == False])
        return wins, losses

    def get_most_loss_against_champ(self, BeginDate=None, EndDate=None):
        champions = self.df_champions.T
        del champions['name']
        del champions['title']
        champions = champions.reset_index(drop=True)
        player_game = self.df_participants[self.df_participants['participant_account_id'] == self.player_id].reset_index(drop=True)
        losses_games = player_game[player_game['win'] == False]

        if BeginDate != None and EndDate != None:
            losses_games = player_game[player_game['timestamp'] == False]

        losses_games = pd.DataFrame([losses_games['gameId'], losses_games['teamId']]).T.reset_index(drop=True)
        champions['derrotas'] = 0
        for i, row in enumerate(losses_games.index): 
            partida = losses_games['gameId'][i]
            team_propio = losses_games['teamId'][i]
            jugadores_partida = self.df_participants[self.df_participants['gameId'] == partida]
            contrincantes = jugadores_partida[jugadores_partida['teamId'] != team_propio].reset_index(drop=True)
            for j in range(0, len(contrincantes)):
                id_champion_enemy = contrincantes['championId'][j]
                champions.loc[champions['id'] == str(id_champion_enemy), 'derrotas'] +=1
        champions = champions.sort_values('derrotas', ascending=False).reset_index(drop=True)
        return champions

    def GetChampsWinRate(self):
        worst_champs = self.get_worst_champs()
        best_champs = self.get_best_champs()
        best_champs['perdidas'] = -1
        best_champs['%'] = -1
        for i, row in enumerate(best_champs.index):
            fila = worst_champs[worst_champs['championId'] == best_champs['championId'][i]].reset_index(drop=True)
            if(len(fila.index) != 0):
                perdidas = fila['perdidas'][0]
            else:
                perdidas = 0
            best_champs['perdidas'][i] = perdidas
        best_champs['%'] = round(best_champs['ganadas'] * 100 / (best_champs['ganadas'] + best_champs['perdidas']), 1)
        best_champs['kda'] = best_champs['championId'].apply(lambda row: self.get_kda_champion(row))
        return best_champs