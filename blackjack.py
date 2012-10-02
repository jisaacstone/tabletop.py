import turn_based
import cards
from random import shuffle


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
    deal_round(game)
    init_turn(game, game['whose_turn'])


def init_player(game, name):
    player = turn_based.init_player(game, name)
    player.update(hand_value=0,
                  coins=50,
                  bet=5)
    player['public'] += ['coins', 'bet']
    return player


def init_round(game):
    turn_based.init_round(game)
    dealer_hand = game['dealer_hand']
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
        player['hand'] = []
        player['hand_value'] = 0

    deal_round(game)


def init_turn(game, player):
    turn_based.init_turn(game, player)
    player['hand_value'] = hand_value(player['hand'])


def deal_round(game):
    shuffle(game['draw_pile'])
    cards.deal(game=game, num_cards=2)
    cards.draw(out_of=game['draw_pile'], into=game['dealer_hand'])


@turn_based.turn_action
def action_bet(game, player, amount):
    player['bet'] = amount


@turn_based.turn_action
def action_hit(game, player):
    cards.draw(out_of=game['draw_pile'], into=player['hand'])
    player['hand_value'] = hand_value(player['hand'])
    if player['hand_value'] >= 21:
        return 'end_turn'


@turn_based.turn_action
def action_stay(game, player):
    return 'end_turn'


def action_start(game, player):
    turn_based.action_start(game, player)
    init_game(game)
