import logging
import json
import collections
from random import randint
from sockjs.tornado import SockJSConnection

logger = logging.getLogger(__name__)


empty_game = dict(game=dict(public=[]),
                  player=dict(public=[]))


def new_room(game):
    return dict(game=game, players=set(), in_room=set())


class InvalidAction(Exception):
    pass


def name_gen():
    name = ["Sa", "Cho", "Gabba", "Ee", "Su", "Y"][randint(0, 4)]
    name += ["n", "mmy", "die", "goid", "xi", "g"][randint(0, 4)]
    return name


class PlayerConnection(SockJSConnection):
    name = "unnamed"
    rooms = {}
    in_lobby = set()

    def __init__(self, session):
        self.name = name_gen()
        super(PlayerConnection, self).__init__(session)

    def __repr__(self):
        return self.name

    def on_open(self, info):
        self.in_lobby.add(self)

    def on_message(self, message):
        if "," in message:
            method, data_raw = message.split(",", 1)
            logger.info(data_raw)
            data = json.loads(data_raw)
        else:
            method = message
            data, data_raw = None, ""

        action = "action_" + method

        if method == 'join':
            return self.action_join()
        if not hasattr(self, 'game_module'):
            return self.invalid_action('join a game first')

        old_vars = self.copy_old_vars()
        try:
            self.perform_action(action, data)
        except InvalidAction as a:
            self.invalid_action(a)
        self.log_var_changes(old_vars)

    def on_close(self):
        self.player_disconnected()

    def invalid_action(self, action):
        self.send("Invailid action {0} by player {1}".format(
            action, self))

    def perform_action(self, action, data, module=None):
        if module is None:
            module = self.game_module
        try:
            if isinstance(data, collections.Sequence):
                result = getattr(module,
                                 action)(self.game, self.vars, *data)
            elif isinstance(data, collections.Mapping):
                result = getattr(module,
                                 action)(self.game, self.vars, **data)
            elif data is not None:
                result = getattr(module,
                                 action)(self.game, self.vars, data)
            else:
                result = getattr(module,
                                 action)(self.game, self.vars)
        except (TypeError, AttributeError, ValueError) as e:
            logger.exception('Error caught: {0}'.format(e))
            raise InvalidAction(e)
        return result

    def action_join(self, game_type='blackjack', game_id=None, player_id=None):
        self.game_module = __import__(game_type)
        if game_id is None or game_id not in self.rooms:
            self.game = self.game_module.game()
            self.room = new_room(self.game)
            self.rooms[id(self.game)] = self.room
        else:
            self.room = self.rooms[game_id]
            self.game = self.room['game']

        self.in_lobby.discard(self)
        self.room['in_room'].add(self)
        if player_id is None:
            self.vars = self.game_module.init_player(self.game, self.name)
            self.room['players'].add(self)
        self.log_var_changes(empty_game)

    def player_disconnected(self):
        pass

    def copy_old_vars(self):
        return {'game': dict((k, json.dumps(self.game[k]))
                             for k in self.game['public']),
                'player': dict((k, json.dumps(v))
                               for k, v in self.vars.items()
                               if k not in ('game', ))}

    def log_var_changes(self, old_vars):
        game = (set(old_vars['game'])
                | set(self.game['public']))
        public = set(self.vars['public'])
        private = (set(old_vars['player'].keys())
                   | set(self.vars.keys())
                   - public
                   - set(['public', 'game']))

        for k in game:
            if (old_vars['game'].get(k, None)
                    != json.dumps(self.game.get(k, None))):
                print old_vars['game'].get(k, None), self.game.get(k, None)
                self.broadcast(self.room['in_room'],
                        json.dumps({'var_type': 'game',
                            'key': k,
                            'value': self.game.get(k, None)}))
        for k in public:
            if (old_vars['player'].get(k, None)
                    != json.dumps(self.vars.get(k, None))):
                self.broadcast(self.room['in_room'],
                        json.dumps({'var_type': 'player',
                            'player': id(self.vars),
                            'key': k,
                            'value': self.vars.get(k, None)}))

        for k in private:
            if (old_vars['player'].get(k, None)
                    != json.dumps(self.vars.get(k, None))):
                self.send(json.dumps({'var_type': 'private',
                    'key': k,
                    'value': self.vars.get(k, None)}))
