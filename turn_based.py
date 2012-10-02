import itertools
from functools import wraps
from cards import poker_deck
from game import InvalidAction


CONTINUE_TURN = False
END_TURN = True


def turn_action(action):
    @wraps(action)
    def action_wrapper(game, player, *args, **kwargs):
        if game['whose_turn'] != player:
            raise InvalidAction('not your turn')

        result = action(game, player, *args, **kwargs)
        if result == 'end_turn':
            context = action.func_globals
            next_player = game['turn'].next()
            context['init_turn'](game, next_player)
            if next_player == game['starting_player']:
                context['init_round'](game)

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


def init_round(game):
    game['round'] += 1


def init_turn(game, player):
    game['whose_turn'] = player
    game['current_player'] = player['name']


def action_start(game, player):
    if game['status'] != 'waiting':
        raise InvailidAction('cannot start game!')
    game['status'] = 'active'
