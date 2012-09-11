import logging
import json
import itertools
from functools import wraps
from random import shuffle, randint
from sockjs.tornado import SockJSConnection

from objects import poker_deck

logger = logging.getLogger(__name__)


def name_gen():
    name = ["Sa", "Cho", "Gabba", "Ee", "Su"][randint(0, 4)]
    name += ["n", "mmy", "die", "goid", "xi"][randint(0, 4)]
    return name


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
    def logit(self, *args, **kwargs):
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
    def action_wrapper(self, *args, **kwargs):
        if self.game_whose_turn != self:
            return self.invalid_action('not your turn')

        result = action(self, *args, **kwargs)
        if result is not False:
            next_player = self.game_turn.next()
            next_player.init_turn()
            logger.info("{0}'s turn".format(next_player))
            if next_player == self.game_starting_player:
                logger.info("round {0}".format(self.public_vars['round']))
                self.init_round()

        return result

    return action_wrapper


class GameConnection(SockJSConnection):
    name = "unnamed"

    public_vars = dict(
        max_players=1,
        state="waiting",
    )

    game_vars = dict(
        action_states={"waiting": ["join", "start"]},
        participants=set(),
        players=set(),
    )

    def __init__(self, session):
        self.name = name_gen()
        super(GameConnection, self).__init__(session)

    def __repr__(self):
        return self.name

    def on_open(self, info):
        self.game_vars['participants'].add(self)
        self.send(json.dumps(dict((p.name, p.info())
                                  for p in self.game_vars['players'])))

    def on_message(self, message):
        if "," in message:
            method, data_raw = message.split(",", 1)
            data = json.loads(data_raw)
        else:
            method = message
            data, data_raw = None, ""

        if not self.can_do(method):
            return self.invalid_action(method)

        action = "action_" + method

        try:
            if data_raw.startswith("["):
                result = getattr(self, action)(*data)
            elif data_raw.startswith("{"):
                result = getattr(self, action)(**data)
            elif data is not None:
                result = getattr(self, action)(data)
            else:
                result = getattr(self, action)()
        except (TypeError, AttributeError, ValueError) as e:
            logger.exception('Error caught: {0}'.format(e))
            return self.invalid_action(e)
        else:
            if result:
                logger.info(result)
                self.send("{0}".format(result))

    def on_close(self):
        self.player_disconnected()

    def info(self):
        return self.public_vars['state']

    def can_do(self, action):
        state = self.public_vars['state']
        return (state is "active"
            or action in self.game_vars['action_states'].get("any", [])
            or action in self.game_vars['action_states'].get(state, []))

    def invalid_action(self, action):
        self.send("Invailid action {0} by player {1}".format(
            action, self))
        return False

    def action_join(self):
        if len(self.game_vars['players']) >= self.public_vars['max_players']:
            return self.invalid_action("full_game")

        if self.public_vars['state'] == 'active':
            return self.invalid_action("game in progress")

        self.init_player()
        self.game_vars['players'].add(self)
        if len(self.game_vars['players']) == self.public_vars['max_players']:
            self.action_start()
        return "players: {0}, slots left: {1}".format(
            len(self.game_vars['players']),
            self.public_vars['max_players'] - len(self.game_vars['players']))

    def action_start(self):
        self.public_vars['state'] = "active"
        return self.init_game()

    def action_inspect(self, attr):
        return getattr(self, attr, None)

    def action_quit(self, player):
        self.game_vars['players'].remove(self)

    def player_disconnected(self):
        self.game_vars['players'].remove(self)
        self.game_vars['participants'].remove(self)

    def init_game(self):
        raise NotImplementedError

    def init_player(self):
        raise NotImplementedError


class TurnBasedGame(GameConnection):
    game_draw_pile = poker_deck()
    game_turn = object()
    game_whose_turn = object()
    game_starting_player = object()

    def __init__(self, *args, **kwargs):
        super(TurnBasedGame, self).__init__(*args, **kwargs)
        self.public_vars.update(max_players=4,
                                current_player='none',
                                round=0,
                                )

    def init_game(self):
        logger.info([id(p) for p in self.game_vars['players']])
        self.broadcast(self.game_vars['players'], "Game Started")
        self.game_turn = itertools.cycle(self.game_vars['players'])
        self.game_whose_turn = self.game_turn.next()
        self.game_starting_player = self.game_whose_turn
        self.public_vars['current_player'] = self.game_whose_turn.name
        self.game_draw_pile = poker_deck()

    @send
    def init_player(self):
        self.hand = []
        self.broadcast(self.game_vars['participants'],
                       "Player {0} Joined Game".format(self))

    @send
    def init_round(self):
        self.public_vars['round'] += 1

    @send
    def init_turn(self):
        self.game_whose_turn = self
        self.public_vars['current_player'] = self.name

    def shuffle(self):
        shuffle(self.game_draw_pile)

    def deal(self, num_cards='all', into=None, out_of=None):
        if into is None:
            into = self.game_vars['players']
        if out_of is None:
            out_of = self.game_draw_pile
        if num_cards == 'all':
            players = itertools.cycle(into)
            while out_of:
                players.next().draw(out_of=out_of)
        else:
            for _ in xrange(num_cards):
                for player in into:
                    player.draw(out_of=out_of)

    @send
    def draw(self, into=None, out_of=None):
        if out_of is None:
            out_of = self.game_draw_pile
        if not out_of:
            return False
        if into is None:
            into = self.hand
        into.append(self.game_draw_pile.pop())
        return True


CONTINUE_TURN = False
END_TURN = True


def max_under_21(a, b):
    if a >= b and a < 21:
        return a
    return b


def hand_value(cards):
    if not cards:
        return 0

    card = cards[0]
    if card['value'].isdigit():
        return int(card['value']) + hand_value(cards[1:])
    elif card['value'] in ['J', 'Q', 'K']:
        return 10 + hand_value(cards[1:])
    elif card['value'] == 'A':
        return max_under_21(11 + hand_value(cards[1:]),
                            1 + hand_value(cards[1:]))


turn_message = """Your turn
You have {0} coins
Your current bet is {1} coins"""


class BlackJack(TurnBasedGame):

    @send
    def init_game(self):
        super(BlackJack, self).init_game()
        self.public_vars.update(dealer_hand=[])
        self.deal_round()

    @send
    def init_player(self):
        super(BlackJack, self).init_player()
        self.hand_value = 0
        self.coins = 50
        self.bet = 5

    @send
    def init_round(self):
        super(BlackJack, self).init_round()
        while hand_value(self.public_vars['dealer_hand']) < 16:
            self.dealer_draw()

        dhv = hand_value(self.public_vars['dealer_hand'])
        self.broadcast(self.game_vars['players'], 'dealer got {0}'.format(dhv))
        for player in self.game_vars['players']:
            phv = hand_value(player.hand)
            if phv > 21 or (phv < dhv and dhv <= 21):
                player.coins -= player.bet
                player.send('you lose {0}'.format(player.bet))
            else:
                player.coins += player.bet
                player.send("you win {0}".format(player.bet))
            self.game_draw_pile += player.hand
            player.hand = []
            player.hand_value = 0

        self.deal_round()

    def init_turn(self):
        super(BlackJack, self).init_turn()
        self.hand_value = hand_value(self.hand)

    def deal_round(self):
        self.shuffle()
        self.deal(2)
        self.draw(into=self.public_vars['dealer_hand'])

    def dealer_draw(self):
        self.draw(into=self.public_vars['dealer_hand'])

    @turn_action
    @send
    def action_bet(self, amount):
        self.bet = amount
        return CONTINUE_TURN

    @turn_action
    @send
    def action_hit(self):
        self.draw()
        self.hand_value = hand_value(self.hand)
        if self.hand_value < 21:
            return CONTINUE_TURN
        return END_TURN

    @turn_action
    def action_stay(self):
        return END_TURN
