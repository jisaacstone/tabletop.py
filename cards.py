from random import shuffle
import itertools


def card(facing='down'):
    return dict(facing=facing)


def poker_card(value, suit=None):
    c = card()
    c.update(dict(value=value, suit=suit))
    return c


poker_suits = ["hearts", "diamonds", "clubs", "spades"]
poker_values = map(str, range(2, 11)) + ["J", "Q", "K", "A"]


def poker_deck(jokers=False):
    deck = [poker_card(v, s)
            for v, s in itertools.product(poker_values, poker_suits)]
    if jokers:
        deck += [card("Joker", "grey"), card("Joker", "colorful")]
    shuffle(deck)
    return deck


def deal(game=None, num_cards='all', into=None, out_of=None):
    if game:
        if into is None:
            into = [p['hand'] for p in game['players']]
        if out_of is None:
            out_of = game['draw_pile']
    if num_cards == 'all':
        players = itertools.cycle(into)
        while out_of:
            draw(into=players.next(), out_of=out_of)
    else:
        for _ in xrange(num_cards):
            for player in into:
                draw(into=player, out_of=out_of)


def draw(into=None, out_of=None):
    if not out_of:
        return False
    into.append(out_of.pop())
    return True


CONTINUE_TURN = False
END_TURN = True
