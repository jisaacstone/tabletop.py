from helpers import turn_action
import turn_based
import cards
from random import shuffle
from turn_based import CONTINUE_TURN, END_TURN


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


def game():
    g = turn_based.game()
    g.update(max_players=8,
             name='blackjack',
             dealer_hand=[])
    g['public'] += ['dealer_hand']
    return g


def init_game(game):
    turn_based.init_game(game)
    deal_round(game['players'])


def init_player(player):
    turn_based.init_player(player)
    player.update(hand_value=0,
                  coins=50,
                  bet=5)
    player['public'] += ['coins', 'bet']


def init_round(game):
    turn_based.init_round(game)
    dealer_hand = game['public']['dealer_hand']
    while hand_value(dealer_hand) < 16:
        cards.draw(out_of=game['draw_pile'], into=dealer_hand)

    dhv = hand_value(dealer_hand)

    for player in game['players']:
        phv = hand_value(player['hand'])
        if phv > 21 or (phv < dhv and dhv <= 21):
            player['coins'] -= player['bet']
        else:
            player['coins'] += player['bet']
        game['draw_pile'] += player['hand']
        player.hand = []
        player.hand_value = 0

    deal_round(game)


def init_turn(player):
    turn_based.init_turn(player)
    player['hand_value'] = hand_value(player['hand'])


def deal_round(game):
    shuffle(game['draw_pile'])
    cards.deal(out_of=game['draw_pile'], into=game['players'], amount=2)
    cards.draw(out_of=game['draw_pile'], into=game['dealer_hand'])


@turn_action
def action_bet(player, amount):
    player['bet'] = amount
    return CONTINUE_TURN


@turn_action
def action_hit(player):
    game = player['game']
    cards.draw(out_of=game['draw_pile'], into=player['hand'])
    player['hand_value'] = hand_value(player['hand'])
    if player['hand_value'] < 21:
        return CONTINUE_TURN
    return END_TURN


@turn_action
def action_stay(player):
    return END_TURN
