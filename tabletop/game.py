import logging
import json
import collections
from random import randint
from sockjs.tornado import SockJSConnection

logger = logging.getLogger(__name__)


empty_game = dict(game=dict(public=[]),
                  player=dict(public=[]),
                  players=dict())


def new_room(game):
    return dict(game=game, players=dict(), in_room=set())


def json_serializable(obj):
    try:
        json.dumps(obj)
    except TypeError:
        return False
    else:
        return True


def game_vars_to_json(game):
    return dict((k, json.dumps(game[k]))
                for k in game['public'])


def player_vars_to_json(player):
    return dict((k, json.dumps(v))
                for k, v in player.items()
                if k not in player['public'] + ['game']
                and json_serializable(v))


def all_players_json(players):
    return dict(((id(p), k), json.dumps(p[k]))
                for p in players
                for k in p['public'])


def name_gen():
    name = ["Sa", "Cho", "Gabba", "Ee", "Su", "Y"][randint(0, 4)]
    name += ["n", "mmy", "die", "goid", "xi", "g"][randint(0, 4)]
    return name


def makelog(connection_instance):
    def log():
        connection_instance.log_var_changes(
                connection_instance.old_vars,
                connection_instance.vars)
        connection_instance.old_vars = connection_instance.copy_vars(
                connection_instance.vars)

    return log


class InvalidAction(Exception):
    pass


class PerformAction(object):
    def __init__(self, action, player=None, data=None):
        self.kwargs = dict(action=action, player=player, data=data)


class PlayerConnection(SockJSConnection):
    name = "unnamed"
    rooms = {}
    in_lobby = set()
    old_vars = empty_game

    def __init__(self, session):
        self.name = name_gen()
        super(PlayerConnection, self).__init__(session)

    def __repr__(self):
        return self.name

    def on_open(self, info):
        self.in_lobby.add(self)
        self.send(json.dumps(self.rooms.keys()))

    def on_message(self, message):
        if "," in message:
            method, data_raw = message.split(",", 1)
            logger.info(data_raw)
            data = json.loads(data_raw)
        else:
            method = message
            data, data_raw = {}, ""

        action = "action_" + method

        if method == 'join':
            return self.action_join(**data)
        if not hasattr(self, 'game_module'):
            return self.invalid_action('join a game first')
        if self.game['status'] != 'active' and method != 'start':
            return self.invalid_action('game not sarted yet')

        try:
            self.perform_action(action, data)
        except InvalidAction as a:
            self.invalid_action(a)

    def on_close(self):
        self.player_disconnected()

    def invalid_action(self, action):
        self.send("error,Invailid action {0} by player {1}".format(
            action, self))

    def perform_action(self, action, data=None, player=None, module=None):
        if module is None:
            module = self.game_module
        if player is None:
            player = self.vars

        self.old_vars = self.copy_vars(player)
        try:
            if isinstance(data, collections.Mapping):
                result = getattr(module,
                                 action)(self.game, player, **data)
            elif isinstance(data, collections.Sequence):
                result = getattr(module,
                                 action)(self.game, player, *data)
            elif data:
                result = getattr(module,
                                 action)(self.game, player, data)
            else:
                result = getattr(module,
                                 action)(self.game, player)
        except (TypeError, AttributeError, ValueError) as e:
            logger.exception('Error caught: {0}'.format(e))
            raise InvalidAction(e)

        self.log_var_changes(self.old_vars, player)
        if result:
            if isinstance(result, PerformAction):
                logger.info('perform action {0}'.format(result.kwargs))
                self.perform_action(**result.kwargs)

    def action_join(self, game_type='blackjack', game_id=0, player_id=0):
        self.game_module = __import__(game_type)
        if game_id is 0 or game_id not in self.rooms:
            self.game = self.game_module.game()
            self.room = new_room(self.game)
            self.rooms[id(self.game)] = self.room
            self.broadcast(self.in_lobby, 'new_room,{0}'.format(id(self.game)))
        else:
            self.room = self.rooms[game_id]
            self.game = self.room['game']

        self.in_lobby.discard(self)
        self.room['in_room'].add(self)
        if player_id is 0:
            self.vars = self.game_module.init_player(self.game, self.name)
            self.vars['log'] = makelog(self)
            self.room['players'][id(self.vars)] = self
        self.log_var_changes(empty_game, self.vars)

    def player_disconnected(self):
        pass

    def copy_vars(self, player):
        return {'game': game_vars_to_json(self.game),
                'player': player_vars_to_json(player),
                'players': all_players_json(p.vars
                                for p in self.room['players'].values())}

    def log_var_changes(self, old_vars, player):
        new_vars = self.copy_vars(player)
        game = set(old_vars['game']) | set(new_vars['game'])
        player = set(old_vars['player']) | set(new_vars['player'])
        players = set(old_vars['players']) | set(new_vars['players'])

        for k in game:
            if (old_vars['game'].get(k, None)
                    != new_vars['game'].get(k, None)):
                self.broadcast(self.room['in_room'],
                        'update,' + json.dumps({'var_type': 'game',
                            'key': k,
                            'value': self.game.get(k, None)}))

        for k in players:
            if (old_vars['players'].get(k, None)
                    != new_vars['players'].get(k, None)):
                player_id, key = k
                value = self.room['players'][player_id].vars.get(key, None)
                self.broadcast(self.room['in_room'],
                    'update,' + json.dumps({'var_type': 'player',
                        'player': player_id,
                        'key': key,
                        'value': value}))

        for k in player:
            if (old_vars['player'].get(k, None)
                    != new_vars['player'].get(k, None)):
                self.send('update,' + json.dumps({'var_type': 'private',
                    'key': k,
                    'value': self.vars.get(k, None)}))
