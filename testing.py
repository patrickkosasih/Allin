"""
testing.py

A module for early testing and basic interface to the poker game before the GUI is implemented.
"""
import random
import time

from rules.basic import *
from rules.game_flow import *

# Comment the imports below unless you want to run the server request test.
import app
from online.client.client_comms import ClientComms


class LegacyTestingGame(PokerGame):
    def __init__(self, n_players: int):
        super().__init__()

        if n_players >= 2:
            self.auto_start_game(n_players)

    def auto_start_game(self, n_players):
        self.players = [Player(self, f"Player {i + 1}", 1000) for i in range(n_players)]
        self.start_game()
        self.hand.start_hand()


"""
==============
String formats
==============
"""
PLAYER_STATE_FORMAT = ("{turn_arrow: <3}{name: <15}{pocket_cards: <10}${chips: <10}{ranking: <18} "
                       "{action: <25} {action_extras}")


"""
=======================
Output helper functions
=======================
"""
def print_state(game: PokerGame):
    """
    Prints the state of the current game/hand:

    1. Player states:
        a. An arrow (->) for the current turn player
        b. Player name
        c. Pocket cards
        d. Chips
        e. Dealer, small blinds, big blinds (on preflop round); or
           Current hand ranking (after the flop)
        f. Player action

    2. Pot
    3. Community cards
    """

    for player in game.hand.players:  # player: PlayerHand
        is_preflop = bool(not game.hand.community_cards)
        preflop_role = ""
        ranking = HandRanking.TYPE_STR[player.hand_ranking.ranking_type].capitalize() if not is_preflop else "n/a"

        if is_preflop:
            # If the current round is still the preflop round then determine the D, SB, and BB
            players = game.hand.players

            if player is players[game.dealer]:
                preflop_role = "D"
            elif player is players[game.hand.blinds[0]]:
                preflop_role = "SB"
            elif player is players[game.hand.blinds[1]]:
                preflop_role = "BB"

        match player.pot_eligibility:
            case -1:
                pot_eligibility_text = ""
            case 0:
                pot_eligibility_text = "Main pot"
            case 1:
                pot_eligibility_text = "Main pot + Side pot 1"
            case _:
                pot_eligibility_text = f"Main pot + Side pots 1-{player.pot_eligibility}"

        print(PLAYER_STATE_FORMAT.format(
            turn_arrow="-> " if player is game.hand.get_current_player() else "",
            name=player.player_data.name,
            pocket_cards=card_list_str(player.pocket_cards),
            chips=f"{player.player_data.chips:,}",
            ranking=ranking if not is_preflop else preflop_role,
            action=f"{player.last_action.capitalize()} {f'${player.amount_to_call:,}' if player.amount_to_call > 0 else ''}",
            action_extras=pot_eligibility_text,
        ))

    print_below(game)


def print_below(game: PokerGame):
    print(f"\nCommunity cards: {card_list_str(game.hand.community_cards)}")

    round_pot_text = f"Current round pot: ${game.hand.current_round_bets:,}  ->  "
    print(f"{round_pot_text}Main pot: ${game.hand.pots[0]:,}")

    side_pot_space = len(round_pot_text)
    for i, side_pot in enumerate(game.hand.pots[1:]):
        print(f"{" " * side_pot_space}Side pot {i + 1}: ${side_pot:,}")


def print_winner(game: PokerGame):
    """
    Print the winner(s) of the hand when a hand ends by showdown or everyone folding.
    """
    for player in game.hand.players:
        player: PlayerHand

        win = any(player in x for x in game.hand.winners)

        new_chips = player.player_data.chips
        old_chips = new_chips - player.winnings

        ranking = HandRanking.TYPE_STR[player.hand_ranking.ranking_type].capitalize()

        if win:
            winner_text = f"WINNER!"

            if len(game.hand.pots) > 1:
                # if player.first_pot_won == player.pot_eligibility:
                #     winner_text = f"Side Pot {player.pot_eligibility} Winner!"
                # else:
                #     winner_text = f"Side pots {player.first_pot_won}-{player.pot_eligibility} Winner!"
                if min(player.pots_won) == 0 and max(player.pots_won) == len(game.hand.pots) - 1:
                    pass
                elif len(player.pots_won) == 1:
                    winner_text += f" Pot {player.pots_won[0]}"
                else:
                    winner_text += f" Pots {min(player.pots_won)} to {max(player.pots_won)}"

        elif player.folded:
            winner_text = "Folded"

        else:
            winner_text = ""

        reward_text = f"+${player.winnings:,} -> ${new_chips:,}" if win else ""

        print(PLAYER_STATE_FORMAT.format(
            turn_arrow="-> " if win else "",
            name=player.player_data.name,
            pocket_cards=card_list_str(player.pocket_cards),
            chips=f"{old_chips:,}",
            ranking=ranking,
            action=winner_text,
            action_extras=reward_text,
        ))

    print_below(game)


def card_list_str(cards: list[Card]) -> str:
    """
    Returns a readable string format for a list of cards.
    e.g. "J♠ 10♣ 7♣ 6♥ A♦"
    """
    return " ".join([card_str(card) for card in cards])


"""
=====================
Run on main functions
=====================
"""
def standard_io_poker():
    """
    Run a text based poker game using the console's basic input and output.

    To play, type in the actions of each player (not case-sensitive). Actions can be the following:
    1. Fold
    2. Check
    3. Call
    4. Bet <bet amount>
    5. Raise <new bet amount>

    Note that check and call does the same thing; and bet and raise also does the same thing.
    """

    game = LegacyTestingGame(8)

    # Side pot testing stuff
    # for i, x in enumerate(game.players):
    #     x.chips += 100 * i
    for i, x in enumerate(game.players):
        x.chips += 100 * (i // 2)
    # for i, x in enumerate(game.players):
    #     x.chips += 100 * (i // 2) + (i % 2 * 25)
    # for i, x in enumerate(game.players):
    #     x.chips += 500 * i
    # game.dealer += 3

    while True:
        print("\n" + "=" * 110 + "\n")

        if game.hand.winners:
            print_winner(game)
            print()
            game.new_hand()

            if len(game.players) < 2:
                thing = "||{:^60}||"
                print(thing.format("=" * 60))
                print(thing.format(f"VICTORY FOR {game.players[0].name.upper()} GRAAAAAAAAHHHHHHHHHHHHH"))
                print(thing.format(f"{game.players[0].name} is the last one standing with ${game.players[0].chips:,}!"))
                print(thing.format("=" * 60))
                break

            else:
                input("Press enter to start next hand. ")
                game.hand.start_hand()
                continue

        print_state(game)
        print()

        if game.hand.skip_next_rounds:
            input("Press enter to continue. ")
            game.hand.next_round()
            continue

        player_name = game.hand.get_current_player().player_data.name  # Name of the current turn player
        action = input(f"What will {player_name} do? ")
        # action = "all in"

        action = action.upper().split()
        # The input is uppercased and then split into a list.

        new_amount = 0  # New amount for betting/raising
        # action = ["CALL"]

        try:
            if action[0] == "QUIT":
                break

            elif action[0] in ("BET", "RAISE"):
                if len(action) < 2:
                    print("Specify a betting amount.")
                    continue

                new_amount = int(action[1])

            elif action == ["ALL", "IN"] or action[0] in ("ALL-IN", "ALLIN"):
                action, new_amount = ["BET"], 99999999999999999999

            action_code = Actions.__dict__[action[0]]
            game.hand.action(action_code, new_amount)

            if game.hand.round_finished:
                game.hand.next_round()
                game.hand.start_new_round()

        except (IndexError, KeyError):
            print("Invalid input.")

        except ValueError as e:
            print("Invalid betting amount:", e)


def hand_ranking_test(n_tests=10, repeat_until=0):
    deck = generate_deck()
    table_format = "{pocket: <20}{community: <20}{ranking_type: <20}{ranked_cards: <20}{kickers: <20}" \
                   "{tiebreaker_score: <20}{exec_time}"

    print(table_format.format(pocket="Pocket cards",
                              community="Community cards",
                              ranking_type="Ranking type",
                              ranked_cards = "Ranked cards",
                              kickers="Kickers",
                              tiebreaker_score="Tiebreaker score",
                              exec_time="Execution time"))

    # for i in range(tests):
    i = 0
    while True:
        i += 1

        cards = [deck[x] for x in random.sample(range(52), 7)]
        t = time.perf_counter()
        ranking = HandRanking(cards)
        t = time.perf_counter() - t

        print(table_format.format(pocket=card_list_str(cards[:2]),
                                  community=card_list_str(cards[2:]),
                                  ranking_type=HandRanking.TYPE_STR[ranking.ranking_type].capitalize(),
                                  ranked_cards=card_list_str(ranking.ranked_cards),
                                  kickers=card_list_str(ranking.kickers),
                                  tiebreaker_score=ranking.tiebreaker_score,
                                  exec_time=f"{t * 1E6: .5} μs"))

        if ranking.ranking_type == repeat_until or (i >= n_tests and repeat_until == 0):
            break

    print("Repeats:", i)


def server_request_test():
    ClientComms.connect(threaded=False)

    while True:
        message = input("> ")
        req_iter = iter(ClientComms.send_request(message))

        while True:
            try:
                next(req_iter)
            except StopIteration as e:
                print(e.value)
                break


def attributes_thingy():
    def print_dict(d: dict):
        for k, v in d.items():
            print("{:30} {}".format(k, v))

    game = PokerGame()
    game.players = [Player(game, "aaa", 727), Player(game, "bbb", 69)]

    hand = Hand(game)
    player = Player(game, "aaa", 727)
    player_hand = PlayerHand(hand, player)

    print("\nPokerGame attributes:\n")
    print_dict(vars(game))

    print("\nHand attributes:\n")
    print_dict(vars(hand))

    print("\nPlayer attributes:\n")
    print_dict(vars(player))

    print("\nPlayerHand attributes:\n")
    print_dict(vars(player_hand))


if __name__ == "__main__":
    # standard_io_poker()
    # server_request_test()
    attributes_thingy()
    # hand_ranking_test(repeat_until=HandRanking.ROYAL_FLUSH)
    # hand_ranking_test(n_tests=25)
