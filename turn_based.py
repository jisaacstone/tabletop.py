from cards import poker_deck
import itertools


def game():
    return dict(
        draw_pile=poker_deck(),
        round=0,
        max_players=4,
        current_palyer=None,
        players=[],
        public=['round', 'max_players', 'current_player']
        )


def init_game(game):
    game['turn'] = itertools.cycle(game['players'])
    game['whose_turn'] = game['turn'].next()
    game['starting_player'] = game['whose_turn']
    game['current_player'] = game['whose_turn']['name']


def init_player(game):
    player = dict(
            hand=list(),
            )
    game['players'].append(player)
    return player


def init_round(game):
    game['round'] += 1


def init_turn(player):
    player['game']['whose_turn'] = player
    player['game']['current_player'] = player['name']
