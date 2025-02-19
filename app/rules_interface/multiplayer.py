"""
app/rules_interface/multiplayer.py

The multiplayer module is used to interface multiplayer games from the screen to the inputs to the client comms to the
server.

A key concept of the multiplayer module is that the rule engine subclasses of this module would have most their original
functionality of their parent classes disabled, because most of the calculations are done on the server side, and the
job of these classes is only to interface the server-side game to the player's screen.
"""
from online.client.client_comms import ClientComms
from online.data.game_sync import GameSyncEvent, load_attrs, GAME_SYNC
from online.data.packets import Packet, PacketTypes
from app.rules_interface.interface import InterfaceGame
from rules.basic import HandRanking
from rules.game_flow import GameEvent, Player, Hand, Actions, PlayerHand


class MultiplayerHand(Hand):
    def __init__(self, game: "MultiplayerGame"):
        super().__init__(game)
        self.game: MultiplayerGame
        self.deck = []

        self.client_player_hand: PlayerHand or None = self.game.client_player.player_hand

    def deal_cards(self):
        """
        Run on a NEW_HAND event.

        In multiplayer games, the deck and other players' pocket cards are kept secret on the server side.
        """
        pass

    def start_hand(self):
        self.hand_started = True

    def next_round(self):
        """
        Run on a NEXT_ROUND event.
        """

        """
        Reset fields
        """
        self.amount_to_call = 0
        self.current_round_bets = 0
        self.current_turn = self.get_next_turn(1, turn=self.game.dealer)
        self.round_finished = False

        """
        Reset player hands
        """
        if self.client_player_hand:
            self.client_player_hand.hand_ranking = HandRanking(self.community_cards + self.client_player_hand.pocket_cards)

        for player in self.players:
            player.current_round_spent = 0
            player.last_action = "folded" if player.folded else ("all in" if player.all_in else "")
            player.called = False


class MultiplayerGame(InterfaceGame):
    def __init__(self):
        super().__init__()
        self.client_player = Player(self, "Placeholder thingy", 1000)

    def sync_game(self, game_sync_event: GameSyncEvent):
        """
        this will be our last jujutsu kaisen, sukuna
        """
        # Sync the attributes of `self`
        load_attrs(self, game_sync_event.attr_dict, ["players", "hand"])

        # Sync the attributes of `self.players` (list of `Player`)
        if "players" in game_sync_event.attr_dict:
            old_players_dict = {x.name: x for x in self.players}
            new_players_list = []

            for player_attr_dict in game_sync_event.attr_dict["players"]:
                if player_attr_dict["name"] in old_players_dict:
                    # Existing player
                    player = old_players_dict[player_attr_dict["name"]]
                    player.chips = player_attr_dict["chips"]
                    new_players_list.append(player)

                else:
                    # New player
                    player = Player(self, player_attr_dict["name"], player_attr_dict["chips"])
                    new_players_list.append(player)

            self.players = new_players_list

            for i, player in enumerate(self.players):
                player.player_number = i

        # Sync the attributes of `self.hand` (instance of `Hand`)
        if "hand" in game_sync_event.attr_dict and self.hand:
            load_attrs(self.hand, game_sync_event.attr_dict["hand"], ["players"])

            for player_hand, player_hand_attr_dict in zip(self.hand.players, game_sync_event.attr_dict["hand"]["players"]):
                load_attrs(player_hand, player_hand_attr_dict)

        # Determine the client player object
        if game_sync_event.client_player_number >= 0:
            self.client_player = self.players[game_sync_event.client_player_number]
        elif game_sync_event.client_player_number == -2:
            self.client_player.player_number = -2

        # Sync the pocket cards of the client player
        if game_sync_event.client_pocket_cards and self.client_player.player_hand:
            self.client_player.player_hand.pocket_cards = game_sync_event.client_pocket_cards

    """
    Overridden input and output methods
    """
    def on_event(self, game_event: GameEvent, game_sync_event: GameSyncEvent or None = None):
        """

        :param game_event:
        :param game_sync_event:
        """
        if game_event.code in GAME_SYNC and not game_sync_event:
            raise ValueError(f"game event of type {game_event.code} must be provided with a game sync event")

        """
        Update the game based on only the game event.
        """
        if game_event.prev_player != -1 and game_event.message:
            action_message = game_event.message.upper()

            if action_message in Actions.__dict__:
                action_code = Actions.__dict__[action_message]
            elif action_message == "ALL IN":
                action_code = Actions.RAISE
            else:
                raise ValueError(f"invalid action message: {action_message}")

            self.players[game_event.prev_player].action(action_code, game_event.bet_amount)

        if game_event.next_player != -1:
            self.hand.current_turn = game_event.next_player

        """
        Handle type-specific events.
        """
        match game_event.code:
            case GameEvent.NEW_HAND:
                self.sync_game(game_sync_event)
                self.new_hand()
                if game_sync_event.client_pocket_cards:
                    self.client_player.player_hand.pocket_cards = game_sync_event.client_pocket_cards
                else:
                    raise AttributeError("the game data should've came with client pocket cards on a new hand, but the "
                                         "server didn't provide it for some reason")

            case GameEvent.START_HAND:
                self.hand.start_hand()

            case GameEvent.NEW_ROUND | GameEvent.SKIP_ROUND:
                self.sync_game(game_sync_event)
                self.hand.next_round()

            case GameEvent.JOIN_MID_GAME:
                self.sync_game(game_sync_event)
                self.new_hand()
                self.sync_game(game_sync_event)

                # Convert the last action and bet amount of all the player hands into a series of game events to update
                # the sub-texts of the player displays in the game scene.
                for player_number, player_hand in enumerate(self.hand.players):
                    if player_hand.last_action and player_hand.last_action != "folded":
                        ClientComms.game_event_queue.append(GameEvent(
                            code=GameEvent.DEFAULT_ACTION,
                            prev_player=player_number,
                            next_player=-1,
                            message=player_hand.last_action,
                            bet_amount=player_hand.current_round_spent)
                        )

            case _:
                if game_sync_event:
                    self.sync_game(game_sync_event)

        """
        Forward the event to the game scene's event receiver
        """
        self.event_receiver(game_event)

    def action(self, action_type, new_amount=0):
        ClientComms.send_packet(Packet(PacketTypes.GAME_ACTION, content=(action_type, new_amount)))

    def broadcast(self, broadcast: GameEvent) -> None:
        """
        `MultiplayerGame` objects do not broadcast anything. They only receive broadcasts from the server.
        """
        pass

    """
    Overridden general game methods
    """
    def new_hand(self):
        self.hand = MultiplayerHand(self)
        self.game_in_progress = True

    def update(self, dt):
        super().update(dt)

        if ClientComms.game_event_queue:
            event: GameEvent or GameSyncEvent = ClientComms.game_event_queue.pop(0)

            if type(event) is GameEvent:
                self.on_event(event)
            elif type(event) is GameSyncEvent:
                self.on_event(GameEvent(event.code), event)
            else:
                raise TypeError(f"invalid object type in the game event queue: {type(event)}")
