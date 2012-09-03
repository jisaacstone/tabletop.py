from random import shuffle, randint
from itertools import chain, product

class Item(object):
    def __init__(self):
        self.active = True

    def __nonzero__(self):
        return self.active


class Card(Item):
    def __init__(self, value, suit="default", facing="down"):
        self.value = value
        self.suit = suit
        self.facing = facing
        super(Card, self).__init__()

    def flip(self):
        self.facing = {"up": "down", "down": "up"}[self.facing]

    def __repr__(self):
        return "{0.value} of {0.suit}".format(self)

    def __eq__(self, other):
        return (type(other) is type(self)
                and other.value == self.value
                and other.suit == self.suit)

    def __ne__(self, other):    
        return not self.__eq__(other)


class Area(object):
    image = ""


class Stack(object):
    items = []


class State(object):
    states = []
    current_state = None


def cut(deck, depth=None):
    if depth is None:
        depth = randint(0, len(deck))
    for _ in xrange(depth):
        deck.append(deck.pop(0))         


def deal(deck, players, cards="all"):
    if cards == "all":
        cards = len(deck)
    for _ in xrange(cards):
        for player in players:
            player.hand.append(deck.pop(0))
            if not deck:
                return


def new_poker_deck(jokers=False):
    suits = ["hearts", "diamonds", "clubs", "spades"]
    values = map(str, range(2, 11)) + ["J", "Q", "K", "A"]
    deck = [Card(v, s) for v, s in product(values, suits)]
    if jokers:
        deck += [Card("Joker", "grey"), Card("Joker", "colorful")]
    shuffle(deck)
    return deck
