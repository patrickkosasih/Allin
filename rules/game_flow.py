"""
rules/game_flow.py

The module that controls the flow of a poker game. This module contains classes and methods that handle the flow of a
poker game, so that every player action follows the rules of Texas Hold'em poker.
"""
from dataclasses import dataclass
from typing import Optional

from rules.basic import *


class Actions:
    FOLD = 0
    CHECK = 1
    CALL = 1
    BET = 2
    RAISE = 2


class ActionResult:
    """
    The `ActionResult` class contains return codes for the `Hand.action` method.
    """
    SUCCESS = 0
    LESS_THAN_MIN_BET = 1
    LESS_THAN_MIN_RAISE = 2
    ROUND_ALREADY_ENDED = 3
    HAND_ALREADY_ENDED = 4
    HAND_NOT_STARTED_YET = 5


@dataclass
class GameEvent:
    """
    A game event is used to pass information from an ongoing game/hand to the `Player.receive_event` method and the
    `PokerGame.on_event` method.

    The information can then be used to update the GUI, call the action method of a bot, and more.
    """

    # Event codes
    DEFAULT_ACTION = 0
    NEW_HAND = 1
    START_HAND = 2
    ROUND_FINISH = 3
    NEW_ROUND = 4
    START_NEW_ROUND = 5
    SKIP_ROUND = 6
    SHOWDOWN = 7
    RESET_HAND = 8
    RESET_PLAYERS = 9

    # Class fields
    code: int
    prev_player: int = -1
    next_player: int = -1
    message: str = ""
    bet_amount: int = 0


class Player:
    """
    The `Player` class is the player controller class for a single player. Also referred to as a player data.
    An instance of this class can be a real player that can control their actions, or even a bot.

    Some methods of this class are empty and can be altered in a subclass of `Player` for an interface to actions on the
    game.
    """

    def __init__(self, game: "PokerGame", name: str, chips: int):
        self.game: "PokerGame" = game
        self.player_hand: Optional["PlayerHand"] = None
        self.leave_next_hand: bool = False

        self.name: str = name
        self.chips: int = chips
        self.player_number: int = -2  # -2: Not assigned to any PokerGame

    def action(self, action_type: int, new_amount=0) -> GameEvent or None:
        """
        Calls the `self.game.hand.action()` method along with its arguments, but only if it's currently this player's
        turn and the hand is not over.

        :return: An `ActionResult` object; `None` if it's not this player's turn.
        """
        if self.game.hand.get_current_player().player_data is self and not self.game.hand.winners:
            action_result = self.game.hand.action(action_type, new_amount)
            return action_result
        else:
            return None

    # Hook method: Can be overridden by subclasses as an interface.
    def receive_event(self, game_event: GameEvent):
        """
        A hook method that is called every time any player makes an action.
        """
        pass


class PlayerHand:
    """
    The `PlayerHand` class contains attributes that a player has for the current hand.

    The main difference between `Player` and this class is that the attributes of this class is only relevant on
    the current hand, such as the pocket cards of a player. Once the hand is over, the `Hand` and `PlayerHand` objects
    are disposed of.
    """

    def __init__(self, hand: "Hand", player_data: Player):
        self.hand: "Hand" = hand
        self.player_data: "Player" = player_data

        self.player_data.player_hand = self
        """
        When creating a `PlayerHand` object, the player hand attribute of the player data gets updated; creating a
        circular reference between the two.
        """

        self.pocket_cards = []
        self.hand_ranking = HandRanking()

        self.current_round_spent = 0  # The amount of chips spent on the current betting round
        self.last_action = ""  # A string representing the action the player previously made.
        self.pot_eligibility = -1  # An integer representing which pots are the player eligible to participate in.
                                   # -1: Eligible for all pots.
                                   # Not -1: Eligible only for pots 0 until that number.

        self.winnings: int = 0  # The amount of chips this player won on the current round.
        self.pots_won: list[int] = []

        self.folded: bool = False
        self.called: bool = False
        self.all_in: bool = False

    def call_bet(self, amount_to_call: int, blinds=False) -> int:
        """
        Pay an amount of chips to call (match the bet of other players) or bet/raise.
        IMPORTANT NOTE: This method can only be called by the `Hand.action` method.

        :param amount_to_call: The total amount to call on that round.
        :param blinds: If set to True, then `called` will not be set to True. Used on the start of a hand where the
        two players with the blinds must bet an amount of chips but still must call/check later.

        :return: The player's new bet amount.
        """
        extra_amount_to_call = amount_to_call - self.current_round_spent  # How much chips to pay to call/raise

        if extra_amount_to_call >= self.player_data.chips:
            """
            ALL IN
            """
            self.all_in = True

            extra_amount_to_call = self.player_data.chips
            amount_to_call = extra_amount_to_call + self.current_round_spent

        self.player_data.chips -= extra_amount_to_call
        self.hand.current_round_bets += extra_amount_to_call
        self.current_round_spent = amount_to_call

        if not blinds:
            self.called = True

        return amount_to_call


class Hand:
    """
    The `Hand` class handles one hand of a poker game, where betting rounds are started, players do actions, community
    cards are revealed, winners are decided, etc.

    After a hand ends, the old hand is deleted and another hand starts, but the game `PokerGame` is still the same.
    """

    def __init__(self, game: "PokerGame"):
        """
        Initialize the fields of a hand, notably the `PlayerHand` objects and their pocket cards. After initializing the
        hand, the `start_hand` is separately called to start the hand.

        :param game: The parent `PokerGame` object
        """

        if len(game.players) < 2:
            raise ValueError("there must be at least 2 players to start a hand")

        self.game = game
        self.players = [PlayerHand(hand=self, player_data=player) for player in game.players]
        # A list of `PlayerHand` instances based on the `PlayerData` list of the `PokerGame`.
        self.winners: list[list[int]] = []
        # A list of sublists of the player numbers of players who have won the hand. Each sublist contains the winner(s)
        # of their respective pot. When there are no side pots, there is only one sublist.

        self.pots: list[int] = [0]
        self.current_round_bets: int = 0
        self.amount_to_call: int = self.game.sb_amount * 2  # The amount to spend for a player to make a call on this round.

        self.community_cards: list[Card] = []
        self.deck: list[Card] = generate_deck()

        self.current_turn: int = self.get_next_turn(n=1, turn=self.game.dealer)\
                                 if len(self.players) > 2 else self.game.dealer
        self.blinds: tuple[int, int] = (self.current_turn, self.get_next_turn(1))

        self.round_finished: bool = False
        self.hand_started: bool = False
        self.skip_next_rounds: bool = False

        self.deal_cards()

    def deal_cards(self):
        """
        Deal two pocket cards to each player.
        """
        n_dealed_cards = len(self.players) * 2

        dealed_cards = self.deck[:n_dealed_cards]
        self.deck = self.deck[n_dealed_cards:]

        for i, player in enumerate(self.players):
            player.pocket_cards = dealed_cards[i * 2: i * 2 + 2]

    def start_hand(self):
        """
        Start the current hand. Should only be called ONCE on the start of a hand.
        """

        self.hand_started = True

        """
        Player turn initialization and blinds
        """
        self.action(Actions.BET, self.game.sb_amount, blinds=True)
        self.action(Actions.BET, self.game.sb_amount * 2, blinds=True)

    def action(self, action_type: int, new_amount=0, blinds=False) -> int:
        """
        Do an action for the current turn player. There are 3 types of actions:
        1. Fold
        2. Check/call
        3. Bet/raise

        :param action_type: Determines the type of action using an integer value from the constants of the `Actions`
        class (0-2).

        :param new_amount: The amount of chips to bet. Only used when the action type is to bet/raise.

        :param blinds: Used for automatically betting the small and big blinds on the beginning of a hand.

        :return: An action result integer code.
        """

        """
        Validation
        """
        if type(action_type) is not int:
            raise TypeError("action type must be an int")
        elif action_type not in range(3):
            raise ValueError(f"action type must be 0, 1, or 2 (got: {action_type})")
        elif self.round_finished:
            return ActionResult.ROUND_ALREADY_ENDED
        elif self.winners:
            return ActionResult.HAND_ALREADY_ENDED
        elif not self.hand_started:
            return ActionResult.HAND_NOT_STARTED_YET

        player: PlayerHand = self.get_current_player()

        action_broadcast = GameEvent(code=GameEvent.DEFAULT_ACTION if not blinds else GameEvent.START_HAND,
                                     prev_player=self.current_turn,
                                     next_player=self.get_next_turn(),
                                     message="")

        """
        Do the action
        """
        if new_amount >= player.player_data.chips + player.current_round_spent:
            new_amount = player.player_data.chips + player.current_round_spent

            if new_amount <= self.amount_to_call:
                # If a player uses the raise button to call an all in.
                action_type = Actions.CALL

        # region Do the action
        match action_type:
            case Actions.FOLD:   # Fold
                player.folded = True
                action_broadcast.message = "fold"
                action_broadcast.bet_amount = player.current_round_spent

                # If everyone except one player folds, then that player wins.
                if sum(not player.folded for player in self.players) == 1:
                    self.showdown()

            case Actions.CALL:   # Check/call
                # Set action text
                if self.amount_to_call > 0:
                    action_broadcast.message = "call"
                else:
                    action_broadcast.message = "check"

                extra_amount_to_call = player.call_bet(self.amount_to_call)
                player.called = True
                action_broadcast.bet_amount = extra_amount_to_call

            case Actions.RAISE:  # Bet/raise
                if new_amount >= player.player_data.chips + player.current_round_spent:
                    new_amount = player.player_data.chips + player.current_round_spent  # ALL IN

                elif blinds:
                    pass  # Bypass the min bet/raise restrictions on blinds.

                elif new_amount < self.get_min_bet():
                    return ActionResult.LESS_THAN_MIN_BET

                elif new_amount < self.get_min_raise():
                    return ActionResult.LESS_THAN_MIN_RAISE

                # Everyone except the betting/raising player must call again
                for x in self.players:
                    x.called = False

                # Set action text
                if self.amount_to_call > 0 and not blinds:
                    action_broadcast.message = "raise"
                else:
                    action_broadcast.message = "bet"

                extra_amount_to_call = player.call_bet(new_amount, blinds)
                self.amount_to_call = max(self.amount_to_call, extra_amount_to_call)

                action_broadcast.bet_amount = player.current_round_spent
        # endregion

        if player.all_in:
            action_broadcast.message = "all in"

        player.last_action = action_broadcast.message

        """
        After the action
        
        1. If everyone who hasn't folded has called or is all in, then the hand advances to the next betting round.
           Advancing to the next betting round is done separately by calling the `start_new_round` method
        2. Otherwise, cycle the current turn to the next player.
        """
        if all(player.called or player.all_in for player in self.players if not player.folded):
            action_broadcast.code = GameEvent.ROUND_FINISH
            action_broadcast.next_player = -1
            self.round_finished = True

        else:
            self.current_turn = self.get_next_turn()

        """
        Broadcast the game event
        """
        self.broadcast(action_broadcast)

        return ActionResult.SUCCESS

    def next_round(self):
        """
        Advance to the next betting round by resetting the previous round, transferring the current round bets to the
        pot(s), and then revealing the next community card.
        """

        """
        Error checking stuff.
        """
        if self.winners:
            return

        assert sum(x.current_round_spent for x in self.players) == self.current_round_bets, "bet amount sums must match"

        prev_total_pot = sum(self.pots)
        prev_round_bets = self.current_round_bets

        """
        Create new side pot(s) when a player(s) goes all in.
        """
        all_in_players = sorted((x for x in self.players if x.all_in and x.current_round_spent > 0),
                                key=lambda x: x.current_round_spent)
        # List of players that went all in on the last round, sorted by their bet amount.

        for all_in_player in all_in_players:
            """
            For each player that went all in on the last round, a new side pot is created, and that player is set to be
            eligible for only up until the pot before the newly created pot.
            
            Players who are all in for the same amount are counted as one and share the same pot eligibility.
            
            Every player then gives the same amount of chips to each last pot that an all in player is eligible for,
            which is the bet amount of that all in player.
            """
            if all_in_player.current_round_spent <= 0:
                all_in_player.pot_eligibility = len(self.pots) - 2
                continue

            transfer_amount = all_in_player.current_round_spent  # The amount of chips to be transferred to the pot per player.

            for player in self.players:
                if player.current_round_spent <= 0:
                    continue

                # If bet amount < transfer amount, just transfer what's left.
                # This only happens when the player has folded.
                current_transfer = min(transfer_amount, player.current_round_spent)

                # Transfer the chips: Current round spent -> Currently open pot.
                # `current_round_pot` must always be the sum of the bet amounts of all players.
                player.current_round_spent -= current_transfer
                self.current_round_bets -= current_transfer
                self.pots[-1] += current_transfer

            all_in_player.pot_eligibility = len(self.pots) - 1
            self.pots.append(0)  # Create a new side pot.

        """
        When a side pot only has one player participating, then that side pot is removed and the contents are given back
        to said player.
        """
        max_eligibility = max((x.pot_eligibility if x.pot_eligibility != -1 else len(self.pots) - 1)
                              for x in self.players if not x.folded)

        last_pot_players = [x for x in self.players if not x.folded and
                            (x.pot_eligibility >= max_eligibility or x.pot_eligibility == -1)]

        if len(last_pot_players) == 1:
            refund_player = last_pot_players[0]

            if refund_player.all_in:
                # Pot with the refund player -> Refund player's chips
                refund = self.pots.pop(refund_player.pot_eligibility)
                refund_player.all_in = False
                refund_player.pot_eligibility = -1
            else:
                # Refund player's bet amount -> Refund player's chips
                refund = refund_player.current_round_spent
                refund_player.current_round_spent = 0
                self.current_round_bets = 0

            refund_player.player_data.chips += refund

            prev_round_bets -= refund

        """
        Transfer the chips to the currently open pot.
        When new side pot(s) have just been created, transfer the remaining chips that hasn't been distributed yet.
        """
        self.pots[-1] += self.current_round_bets
        assert prev_total_pot + prev_round_bets == sum(self.pots), "something went wrong while distributing the bets"

        """
        Reset fields
        """
        self.amount_to_call = 0
        self.current_round_bets = 0
        self.current_turn = self.get_next_turn(1, turn=self.game.dealer)
        self.round_finished = False

        """
        Reveal community cards or showdown
        """
        if len(self.community_cards) < 5:
            draw_n_cards = 3 if len(self.community_cards) == 0 else 1
            for _ in range(draw_n_cards):
                self.community_cards.append(self.deck.pop(0))
        else:
            self.showdown()
            return

        """
        Reset player hands
        """
        for player in self.players:
            player.hand_ranking = HandRanking(self.community_cards + player.pocket_cards)
            player.current_round_spent = 0
            player.last_action = "folded" if player.folded else ("all in" if player.all_in else "")
            player.called = False

        """
        Broadcast game event
        """
        if sum(not player.all_in for player in self.players if not player.folded) <= 1:
            # If the number of people who haven't folded and aren't all-in is 1 or less, then the next betting round
            # is skipped.
            self.skip_next_rounds = True
            self.broadcast(GameEvent(GameEvent.SKIP_ROUND, -1, -1, ""))

        else:
            # Broadcast round event
            self.broadcast(GameEvent(GameEvent.NEW_ROUND, -1, -1, ""))

    def start_new_round(self):
        """
        Start the new betting round by broadcasting the "start round" game event to all players. This function
        should be only called after calling the `next_round` method.
        """

        if not self.skip_next_rounds and not self.winners:
            self.round_finished = False
            self.broadcast(GameEvent(GameEvent.START_NEW_ROUND, -1, self.current_turn, ""))

    def showdown(self):
        """
        Decide the winner of the current hand with a showdown.
        Can also be used when there is only 1 player left who hasn't folded.
        """

        """
        If everyone except one player folds.
        """
        if sum(not player.folded for player in self.players) == 1:
            winner: PlayerHand = next(player for player in self.players if not player.folded)

            winner.winnings = sum(self.pots) + self.current_round_bets
            winner.player_data.chips += winner.winnings
            winner.pots_won = [0]
            self.winners = [[winner.player_data.player_number]]

            self.broadcast(GameEvent(GameEvent.SHOWDOWN, -1, -1, ""))
            return

        """
        Remove empty side pots.
        If a player has a pot eligibility of -1 then that player is eligible for all pots.
        """
        if self.pots[-1] == 0:
            self.pots.pop(-1)

        for player in self.players:
            if player.pot_eligibility == -1:
                player.pot_eligibility = len(self.pots) - 1

        """
        Group every player (who are not folded) based on their pot eligibility.
        """
        eligibility_group = [[] for _ in range(len(self.pots))]
        for player in self.players:
            if not player.folded:
                eligibility_group[player.pot_eligibility].append(player)

        """
        Figure out the winners of each pot.
        
        When there are multiple pots, each pot would have a different set of players that are eligible for that pot.
        
        So for every pot starting from the last, player(s) who has a pot eligibility of that pot is added to the
        set of players eligible for that pot.
        
        But instead of adding all the newly eligible players, the algorithm only adds players who have a higher or
        equal hand ranking overall score to the `current_pot_winners` list, similar to the "find max number"
        algorithm.
        """
        self.winners: list[list[int]] = [[] for _ in self.pots]
        current_pot_winners = []

        win_score = 0
        for pot_number, new_pot_participants in list(enumerate(eligibility_group))[::-1]:
            for player in new_pot_participants:
                player: PlayerHand

                score = player.hand_ranking.overall_score

                if score > win_score:
                    win_score = score
                    current_pot_winners = []

                if score >= win_score:
                    current_pot_winners.append(player.player_data.player_number)

            self.winners[pot_number] = current_pot_winners.copy()

        """
        Give the chips to the winner(s).
        """
        for pot_number, pot_winners in enumerate(self.winners):
            prize = self.pots[pot_number] // len(pot_winners)

            for winner_number in pot_winners:
                winner: PlayerHand = self.players[winner_number]

                winner.pots_won.append(pot_number)
                winner.winnings += prize
                winner.player_data.chips += prize

        """
        Broadcast
        """
        self.broadcast(GameEvent(GameEvent.SHOWDOWN, -1, -1, ""))

    def broadcast(self, broadcast: GameEvent) -> None:
        """
        Broadcast a `GameEvent` to all `Player` objects by calling their `receive_event` methods.
        """
        self.game.broadcast(broadcast)

    def get_next_turn(self, n=1, turn=-1) -> int:
        """
        Returns the player index after `n` turns of the current player turn.
        Players who have folded or are all-in are skipped.

        e.g. n = 2: returns the player index after 2 turns

        The `turn` argument may be passed in. If the `turn` argument is not passed in then this function uses the
        `self.current_turn` attribute.

        :param n: Number of turns after the specified turn
        :param turn: The current turn. If the argument is not passed in then the `self.current_turn` attribute is used.

        :return: The player index after `n` turns.
        """
        turn = self.current_turn if turn < 0 else turn

        if sum(not player.folded for player in self.players) <= 1 or \
            all(player.all_in for player in self.players if not player.folded):
            return turn

        while True:
            turn = (turn + 1) % len(self.players)
            if not (self.players[turn].all_in or self.players[turn].folded):
                n -= 1
                if n <= 0:
                    break

        return turn

    def get_current_player(self) -> PlayerHand:
        return self.players[self.current_turn]

    def get_min_bet(self):
        return 2 * self.game.sb_amount

    def get_min_raise(self):
        return 2 * self.amount_to_call


class PokerGame:
    """
    The `PokerGame` class handles an ongoing poker game with multiple players. Throughout an ongoing game, there may be
    several hands, but the `PokerGame` is still the same.
    """

    def __init__(self):
        self.players: list[Player] = []
        self.dealer: int = 0  # The index of `self.players` who becomes the dealer of the current hand.

        self.sb_amount: int = 25  # Small blinds amount. Big blinds = 2 * Small blinds.

        self.game_in_progress: bool = False
        self.ready_for_next_hand: bool = False

        self.hand: Optional[Hand] = None

    def start_game(self):
        self.prepare_next_hand(cycle_dealer=False)
        self.new_hand()

    def new_hand(self):
        """
        Start a new hand. Players who are out of chips are removed, and the dealer is cycled to the next player.

        :return: True if a new hand is started; False otherwise, due to insufficient player count.
        """
        if not self.ready_for_next_hand:
            self.prepare_next_hand()
        self.ready_for_next_hand = False

        if len(self.players) >= 2:
            self.hand = Hand(self)
            self.broadcast(GameEvent(GameEvent.NEW_HAND))
            self.game_in_progress = True
            return True
        else:
            self.game_in_progress = False
            return False

    def prepare_next_hand(self, cycle_dealer=True) -> None:
        """
        Reset the hand and prepare for the next hand: cycle the dealer, check the players' amount of chips, and remove
        any players that are bankrupt.

        :param cycle_dealer: Defaults to True. If set to True then the dealer is cycled to the next player.
        """
        self.ready_for_next_hand = True

        """
        Mark bankrupt players as leaving next hand
        """
        for player in self.players:
            if player.chips <= 0:
                player.player_number = -2
                player.leave_next_hand = True

        """
        Cycle dealer
        """
        if cycle_dealer:
            while True:
                self.dealer = (self.dealer + 1) % len(self.players)
                if self.players[self.dealer].chips > 0:
                    break

            self.dealer -= sum(x.leave_next_hand for x in self.players[:self.dealer])

        """
        Remove players who are leaving
        """
        self.players = [player for player in self.players if not player.leave_next_hand]

        """
        Update player numbers
        """
        for i, player in enumerate(self.players):
            player.player_number = i

    def on_event(self, event):
        """
        A hook method that is called everytime a game event is broadcasted.
        """
        pass

    def broadcast(self, broadcast: GameEvent) -> None:
        """
        Broadcast a `GameEvent` to all `Player` objects and the `PokerGame` self by calling their `receive_event` and
        `on_event` methods.
        """
        self.on_event(broadcast)

        for player in self.players:
            player.receive_event(broadcast)
