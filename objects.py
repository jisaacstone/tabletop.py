from random import shuffle
from itertools import product


def card(facing='down'):
    return dict(type='card', facing=facing)


def poker_card(value, suit=None):
    c = card()
    c.update(dict(value=value, suit=suit))
    return c


poker_suits = ["hearts", "diamonds", "clubs", "spades"]
poker_values = map(str, range(2, 11)) + ["J", "Q", "K", "A"]


def poker_deck(jokers=False):
    deck = [poker_card(v, s) for v, s in product(poker_values, poker_suits)]
    if jokers:
        deck += [card("Joker", "grey"), card("Joker", "colorful")]
    shuffle(deck)
    return deck
