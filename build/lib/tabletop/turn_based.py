import itertools
from functools import wraps
from cards import poker_deck
from game import InvalidAction, PerformAction


CONTINUE_TURN = False
END_TURN = True


def turn_action(action):
    @wraps(action)
    def action_wrapper(game, player, *args, **kwargs):
        if game['whose_turn'] != player:
            raise InvalidAction('not your turn')

        result = action(game, player, *args, **kwargs)
        if result == 'end_turn':
            next_player = game['turn'].next()
            result = PerformAction('init_turn', player=next_player)

        return result

    return action_wrapper


def game():
    return dict(
        draw_pile=poker_deck(),
        round=0,
        max_players=4,
        current_player=None,
        players=[],
        status='waiting',
        public=['round', 'max_players', 'current_player', 'status']
        )


def init_game(game):
    game['turn'] = itertools.cycle(game['players'])
    game['whose_turn'] = game['turn'].next()
    game['starting_player'] = game['whose_turn']


def init_player(game, name):
    player = dict(
            game=game,
            hand=list(),
            name=name,
            public=['name'],
            )
    game['players'].append(player)
    return player


def init_round(game, player):
    game['round'] += 1


def init_turn(game, player):
    game['whose_turn'] = player
    game['current_player'] = player['name']
    if game['whose_turn'] == game['starting_player']:
        return PerformAction('init_round')


def action_start(game, player):
    if game['status'] != 'waiting':
        raise InvalidAction('cannot start game!')
    game['status'] = 'active'
