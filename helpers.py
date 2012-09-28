from functools import wraps
import logging


logger = logging.getLogger(__name__)


def json_serializable(obj):
    try:
        json.dumps(obj)
    except TypeError:
        return False
    return True


def get_vars(f, obj):
    return dict((a, json.dumps(getattr(obj, a)))
                for a in f.func_code.co_names
                if not a.startswith('game_')
                and a is not 'public_vars'
                and hasattr(obj, a)
                and json_serializable(getattr(obj, a)))


def get_public_vars(dct):
    return dict((a, json.dumps(dct[a]))
                for a in dct
                if json_serializable(dct[a]))


def send(f):
    '''Sends all changed class attributes to player.
    Sends all changed public_vars to all players.'''

    @wraps(f)
    def logit(player, *args, **kwargs):
        logger.info(f.func_code.co_names)
        old = get_vars(f, self)
        logger.info('old {0}'.format(old.items()))

        old_public_vars = get_public_vars(self.public_vars)
        logger.info('pub {0}'.format(old_public_vars.items()))

        result = f(self, *args, **kwargs)

        for attr, new_value in get_public_vars(self.public_vars).items():
            if new_value != old_public_vars.get(attr, None):
                logger.info('game_var ' + attr)
                self.broadcast(self.game_vars['participants'],
                               ','.join((attr, new_value)))

        for attr, new_value in get_vars(f, self).iteritems():
            if new_value != old.get(attr, None):
                logger.info('self ' + attr)
                self.send(','.join((attr, new_value)))

        return result
    return logit


def turn_action(action):
    @wraps(action)
    def action_wrapper(player, *args, **kwargs):
        game = player['game']
        if game.whose_turn != player:
            return player.invalid_action('not your turn')

        result = action(self, *args, **kwargs)
        if result is not False:
            next_player = game.turn.next()
            game.init_turn(next_player)
            logger.info("{0}'s turn".format(next_player))
            if next_player == game.starting_player:
                logger.info("round {0}".format(game.round))
                game.init_round()

        return result

    return action_wrapper
