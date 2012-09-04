import logging
import json
import itertools
from functools import wraps
from random import shuffle, randint

from sockjs.tornado import SockJSConnection

from objects import new_poker_deck, Card

logger = logging.getLogger(__name__)


def name_gen():
    name = ["Sa", "Cho", "Gabba", "Ee", "Su"][randint(0, 4)]
    name += ["n", "mmy", "die", "goid", "xi"][randint(0, 4)]
    return name


def turn_action(action):
    @wraps(action)
    def action_wrapper(self, *args, **kwargs):
        if self.game_vars['whose_turn'] != self:
            return self.invalid_action('not your turn')

        result = action(self, *args, **kwargs)
        if result is not False:
            next_player = self.game_vars['turn'].next()
            next_player.init_turn()
            logger.info("{0}'s turn".format(next_player))
            if next_player == self.game_vars['starting_player']:
                logger.info("round {0}".format(self.game_vars['round']))
                self.init_round()

        return result

    return action_wrapper


class GameConnection(SockJSConnection):
    game_vars = dict(
        max_players=1,
        action_states={"waiting": ["join", "start"]},
        state="waiting",
    )
    participants = set()
    players = set()
    name = "unnamed"

    def __init__(self, session):
        self.name = name_gen()
        super(GameConnection, self).__init__(session)

    def __repr__(self):
        return self.name

    def on_open(self, info):
        self.participants.add(self)
        self.send(json.dumps(dict((p.name, p.info()) for p in self.players)))

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
        return self.game_vars['state']

    def can_do(self, action):
        state = self.game_vars['state']
        return (state is "active"
            or action in self.game_vars['action_states'].get("any", [])
            or action in self.game_vars['action_states'].get(state, []))

    def invalid_action(self, action):
        self.send("Invailid action {0} by player {1}".format(
            action, self))
        return False

    def action_join(self):
        if len(self.players) >= self.game_vars['max_players']:
            return self.invalid_action("full_game")

        if self.game_vars['state'] == 'active':
            return self.invalid_action("game in progress")

        self.init_player()
        self.players.add(self)
        if len(self.players) == self.game_vars['max_players']:
            self.action_start()
        return "players: {0}, slots left: {1}".format(
                len(self.players),
                self.game_vars['max_players'] - len(self.players))

    def action_start(self):
        self.game_vars['state'] = "active"
        return self.init_game()

    def action_inspect(self, attr):
        return getattr(self, attr, None)

    def action_quit(self, player):
        self.players.remove(self)

    def player_disconnected(self):
        self.players.remove(self)
        self.participants.remove(self)

    def init_game(self):
        raise NotImplementedError

    def init_player(self):
        raise NotImplementedError


class TurnBasedGame(GameConnection):
    draw_pile = new_poker_deck()

    def __init__(self, *args, **kwargs):
        super(TurnBasedGame, self).__init__(*args, **kwargs)
        new_vars = dict(max_players=4,
                        whose_turn=False,
                        turn=[],
                        starting_player=False,
                        round=0,
                        )
        self.game_vars.update(new_vars)

    def init_game(self):
        logger.info([id(p) for p in self.players])
        self.broadcast(self.players, "Game Started")
        self.game_vars['turn'] = itertools.cycle(self.players)
        self.game_vars['whose_turn'] = self.game_vars['turn'].next()
        self.game_vars['starting_player'] = self.game_vars['whose_turn']
        return self.game_vars['state']

    def init_player(self):
        logger.info("init player {0}".format(id(self)))
        self.hand = []
        self.broadcast(self.participants,
                       "Player {0} Joined Game".format(self))

    def init_round(self):
        self.game_vars['round'] += 1
        self.broadcast(self.participants,
                       "round {0}".format(self.game_vars['round']))

    def init_turn(self):
        self.broadcast(self.participants, "{0}'s turn.".format(self.name))
        self.game_vars['whose_turn'] = self

    def shuffle(self):
        shuffle(self.draw_pile)

    def deal(self, num_cards='all'):
        if num_cards == 'all':
            p = itertools.cycle(self.players)
            while self.draw_pile:
                p.next().give_card(self.draw_pile.pop())

        else:
            for _ in xrange(num_cards):
                for player in self.players:
                    if self.draw_pile:
                        player.give_card(self.draw_pile.pop())

    def draw(self):
        if not self.draw_pile:
            return "no cards"
        self.give_card(self.draw_pile.pop())

    def give_card(self, card):
        self.hand.append(card)
        self.send("got {0}".format(card))


class SimpleGame(TurnBasedGame):

    def init_player(self):
        self.played = None
        super(SimpleGame, self).init_player()

    @turn_action
    def action_play(self, value, suit):
        card = Card(value, suit)
        if not card in self.hand:
            return "you don't have a {0}".format(card)

        self.hand.remove(card)
        self.played = card
        if all(p.played for p in self.players):
            best = max(p.played for p in self.players)
            for player in self.players:
                if player.played == best:
                    player.send("you win!")
                else:
                    player.send('you lose')
                player.played = None


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
    if card.value.isdigit():
        return int(card.value) + hand_value(cards[1:])
    elif card.value in ['J', 'Q', 'K']:
        return 10 + hand_value(cards[1:])
    elif card.value == 'A':
        return max_under_21(11 + hand_value(cards[1:]),
                            1 + hand_value(cards[1:]))


turn_message = """Your turn
You have {0} coins
Your current bet is {1} coins"""


class BlackJack(TurnBasedGame):

    def init_game(self):
        super(BlackJack, self).init_game()
        self.deal(2)
        self.game_vars['dealer_hand'] = [self.draw_pile.pop()]

    def init_player(self):
        super(BlackJack, self).init_player()
        self.coins = 50
        self.bet = 5

    def init_round(self):
        super(BlackJack, self).init_round()
        while hand_value(self.game_vars['dealer_hand']) < 16:
            self.game_vars['dealer_hand'].append(self.draw_pile.pop())
            logger.info(self.game_vars['dealer_hand'])

        dhv = hand_value(self.game_vars['dealer_hand'])
        self.broadcast(self.players, 'dealer got {0}'.format(dhv))
        for player in self.players:
            phv = hand_value(player.hand)
            if phv > 21 or (phv < dhv and dhv <= 21):
                player.coins -= player.bet
                player.send('you lose {0}'.format(player.bet))
            else:
                player.coins += player.bet
                player.send("you win {0}".format(player.bet))
            self.draw_pile += player.hand
            player.hand = []

        self.shuffle
        self.deal(2)
        self.game_vars['dealer_hand'] = [self.draw_pile.pop()]

    def init_turn(self):
        super(BlackJack, self).init_turn()
        self.send(turn_message.format(self.coins, self.bet))

    @turn_action
    def action_bet(self, amount):
        self.bet = amount
        return CONTINUE_TURN

    @turn_action
    def action_hit(self):
        self.draw()
        return hand_value(self.hand) >= 21

    @turn_action
    def action_stay(self):
        return END_TURN
