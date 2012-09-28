import logging
import json
import collections
from random import randint
from sockjs.tornado import SockJSConnection

logger = logging.getLogger(__name__)


class InvalidAction(Exception):
    pass


def name_gen():
    name = ["Sa", "Cho", "Gabba", "Ee", "Su", "Y"][randint(0, 4)]
    name += ["n", "mmy", "die", "goid", "xi", "g"][randint(0, 4)]
    return name


def perform_action(module, action, data):
    try:
        if isinstance(data, collections.Sequence):
            result = getattr(module, action)(*data)
        elif isinstance(data, collections.Mapping):
            result = getattr(module, action)(**data)
        elif data is not None:
            result = getattr(module, action)(data)
        else:
            result = getattr(module, action)()
    except (TypeError, AttributeError, ValueError) as e:
        logger.exception('Error caught: {0}'.format(e))
        raise InvalidAction(e)
    return result


class PlayerConnection(SockJSConnection):
    name = "unnamed"
    games = {}
    in_room = set()
    players = collections.defaultdict(dict)

    def __init__(self, session):
        self.name = name_gen()
        super(PlayerConnection, self).__init__(session)

    def __repr__(self):
        return self.name

    def on_open(self, info):
        self.in_room.add(self)

    def on_message(self, message):
        if "," in message:
            method, data_raw = message.split(",", 1)
            data = json.loads(data_raw)
        else:
            method = message
            data, data_raw = None, ""

        action = "action_" + method

        if method == 'join':
            return self.action_join(self)

        old_vars = self.copy_old_vars()
        try:
            perform_action(self.game_module, action, data)
        except InvalidAction as a:
            self.invalid_action(a)
        self.log_var_changes(old_vars)

    def on_close(self):
        self.player_disconnected()

    def info(self):
        return self.public_vars['state']

    def invalid_action(self, action):
        self.send("Invailid action {0} by player {1}".format(
            action, self))

    def action_join(self, game_type='blackjack', game_id=None):
        self.game_module = __import__(game_type)
        if game_id is None or game_id not in self.games:
            self.game = self.game_module.init_game()
            self.games[id(self.game)] = self.game
        else:
            self.game = self.games(game_id)

        self.vars = self.game_module.init_player(self.game)
        self.players[id(self.game)][id(self.vars)] = self

    def player_disconnected(self):
        pass

    def copy_old_vars(self):
        return {'game': dict((k, json.dumps(v))
                             for k, v in self.game),
                'player': dict((k, json.dumps(v))
                               for k, v in self.vars)}

    def log_var_changes(self, old_vars):
        for k in set(old_vars['game'].keys()).union(self.game.keys()):
            if old_vars['game'].get(k, None) != self.game.get(k, None):
                self.boadcast(self.players,
                              k + ',' + json.dumps(self.game.get(k, None)))

        for k in set(old_vars['player'].keys()).union(self.vars.keys()):
            if old_vars['player'].get(k, None) != self.vars.get(k, None):
                self.send(k + ',' + json.dumps(self.vars.get(k, None)))
