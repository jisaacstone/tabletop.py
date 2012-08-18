from random import randint

def name_gen():
    name = ["Sa", "Cho", "Gabba", "Ee"][randint(0, 4)]
    name += ["n", "mmy", "die", "goid"][randint(0, 4)]
    return name


class Player(object):
    hand = []
    table = None

    def __init__(self, name=None):
        if name is None:
            name = name_gen()
        self.name = name

    def draw(self, deck):
        self.hand.append(deck.pop(0))

    def play(self, cards, destination=table):
        if not set(cards).issubset(hand):
            raise Exception("Card not in hand")

        for card in cards:
            destination.append(self.hand.pop(card))
