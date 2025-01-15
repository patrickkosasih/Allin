import random

from app.animations.interpolations import ease_out, ease_in, linear
from app.audio import play_sound
from app.widgets.game.side_pot_panel import SidePotPanel
from app.widgets.menu.side_menu import SideMenu, SideMenuButton

from rules.basic import HandRanking
from rules.game_flow import GameEvent
from app.rules_interface.singleplayer import InterfaceGame, SingleplayerGame

from app.scenes.scene import Scene
from app.shared import *
from app.tools import app_timer, app_async

from app import widgets, app_settings
from app.widgets.game.card import Card
from app.widgets.game.action_buttons import FoldButton, RaiseButton, CallButton
from app.widgets.game.dealer_button import DealerButton
from app.widgets.game.winner_crown import WinnerCrown
from app.widgets.game.player_display import PlayerDisplay
from app.widgets.game.bet_prompt import BetPrompt

from app.animations.var_slider import VarSlider


COMM_CARD_ROTATIONS = (198, 126, 270, 54, -18)
"""`COMM_CARD_ROTATIONS` defines the rotation for the animation's starting position of the n-th community card."""


## noinspection PyUnresolvedReferences,PyTypeChecker
class GameScene(Scene):
    def __init__(self, app, game: InterfaceGame):
        super().__init__(app, "")

        self.game: InterfaceGame = game
        self.game.event_receiver = self.receive_event

        """
        Miscellaneous GUI
        """
        self.app.background_scene.background.fade_anim(2, 128)

        self.side_menu_button = SideMenuButton(self, 1.5, 1.5, 4, "%h", "tl", "tl")
        self.side_menu = SideMenu(self, 0, 0, 25, 100, "%", "ml", "ml", toggle_button=self.side_menu_button)
        self.side_menu.set_shown(False, 0)

        self.flash_fac = 0

        """
        Table and players
        """
        self.table = widgets.game.table.Table(self, 0, 0, 55, 55, "%", "ctr", "ctr")

        self.players = pygame.sprite.Group()
        self.winner_crowns = pygame.sprite.Group()

        """
        Table texts
        """
        self.pot_text = widgets.game.table_texts.PotText(self, 0, -12.5, 12.5, 5, "%", "ctr", "ctr")
        self.pot_text.set_shown(False, duration=0)

        self.ranking_text = widgets.game.table_texts.RankingText(self, 0, 12.5, 17.5, 5, "%", "ctr", "ctr")
        self.ranking_text.set_shown(False, duration=0)

        self.side_pot_panel = SidePotPanel(self, 0, 0, 25, 30, "%", "ctr", "ctr", game=self.game)
        self.side_pot_panel.set_shown(False, duration=0)

        """
        Action buttons and bet prompt
        """
        self.action_buttons = pygame.sprite.Group()

        self.fold_button = None
        self.call_button = None
        self.raise_button = None

        self.bet_prompt: Optional[BetPrompt] = None

        self.init_action_buttons()

        """
        Dealer and blinds buttons
        """
        self.dealer_button = DealerButton(self, 0, 0)
        self.sb_button = DealerButton(self, 0, 0, "SB")
        self.bb_button = DealerButton(self, 0, 0, "BB")

        """
        Cards and game initialization
        """
        Card.set_size(height=h_percent_to_px(12.5))  # Initialize card size
        self.community_cards = pygame.sprite.Group()

        if type(game) is SingleplayerGame:
            self.game.start_game()

    def receive_event(self, event: GameEvent):
        """
        The method that is called everytime an action or event happens.
        """
        # print(event)

        """
        Handle non-player-action events
        """
        player_action = False

        match event.code:
            case GameEvent.RESET_PLAYERS:
                self.reset_players()

            case GameEvent.NEW_HAND:
                self.deal_cards()

            case GameEvent.NEW_ROUND | GameEvent.SKIP_ROUND:
                self.next_round()

            case GameEvent.SHOWDOWN:
                app_timer.Timer(1, self.showdown)

            case GameEvent.RESET_HAND:
                self.reset_hand()

            case _:
                player_action = True

        if not player_action:
            return

        """
        Update the subtext on a player action
        """
        is_sb: bool = (event.code == GameEvent.START_HAND) and (event.prev_player == self.game.hand.blinds[0])
        # True if the current game event is the small blinds (SB) action.

        if event.prev_player >= 0:
            action_str = event.message.capitalize()

            if event.bet_amount > 0 and event.message != "fold":
                action_str += f" ${event.bet_amount:,}"

                """
                Update the pot text
                """
                if not is_sb:
                    total_pot = sum(self.game.hand.pots) + self.game.hand.current_round_bets
                    self.pot_text.set_text_anim(total_pot)
                    self.side_pot_panel.update_current_bets()

                """
                Chips sound effect
                """
                play_sound("assets/audio/game/actions/chips.mp3", 0.5)

            self.players.sprites()[event.prev_player].set_sub_text_anim(action_str)
            self.players.sprites()[event.prev_player].update_chips()

        """
        Action sound effect
        """
        if event.code == GameEvent.START_HAND:
            if is_sb:
                play_sound("assets/audio/game/rounds/blinds.mp3")
            if event.message == "all in":
                play_sound("assets/audio/game/actions/all in.mp3")

        elif event.message:
            play_sound(f"assets/audio/game/actions/{event.message}.mp3")

        """
        Show/hide action buttons
        """
        if event.next_player == self.game.client_player.player_number and not is_sb:
            for x in self.action_buttons:
                x.update_bet_amount(self.game.hand.amount_to_call)
            self.show_action_buttons(True)

        elif event.prev_player == self.game.client_player.player_number:
            self.show_action_buttons(False)
            self.bet_prompt.set_shown(False)

        """
        Fold
        """
        if event.message == "fold":
            self.fold_cards(event.prev_player)

    def reset_players(self, time_interval=0.075):
        """
        Initialize or rearrange all the player displays. When calling this function, 3 different scenarios can happen
        for each player display:

        1. Move an existing player display
        2. Create a new player display
        3. Remove an existing player display
        """

        self.dealer_button.set_shown(False)
        play_sound("assets/audio/game/player/slide.mp3")

        old_group = self.players.copy()
        self.players.empty()

        player_display_datas = [x.player_data for x in old_group.sprites()]
        """A list of the player data of each player display that exists before rearranging the players."""

        for i, player_data in enumerate(self.game.players):
            pos = self.table.get_player_pos(i, (1.25, 1.2))

            player_display: PlayerDisplay

            if player_data in player_display_datas:
                """
                1. Move player display
                """
                old_i = player_display_datas.index(player_data)
                player_display = old_group.sprites()[old_i]

            else:
                """
                2. New player display
                """
                start_pos = self.table.get_player_pos(i, (3, 3))

                player_display = PlayerDisplay(self, *start_pos, 15, 12.5, ("px", "%"), "tl", "ctr",
                                               player_data=player_data)

            self.players.add(player_display)

            player_display.move_anim(1.5 + i * time_interval, pos)

        screen_center = self.rect.center

        for i, old_player_display in enumerate(old_group.sprites()):
            if old_player_display not in self.players:
                """
                3. Remove player display
                """
                start_pos = old_player_display.rect.center
                end_pos = screen_center + 3 * (Vector2(start_pos) - screen_center)  # Offscreen

                old_player_display.move_anim(1.5 + i * time_interval, end_pos,
                                             call_on_finish=lambda x=old_player_display: self.all_sprites.remove(x))

    def init_action_buttons(self):
        """
        Initialize the three action buttons and the bet prompt.
        """

        """
        Measurements
        """
        w, h = (15, 6.5)  # Button dimensions (in %screen)
        m = 2  # Margin in %screen

        rects = [(-m, (-m - i * (h + m)), w, h, "%", "br", "br") for i in range(3)]  # List of all the button rects

        self.fold_button = FoldButton(self, *rects[0])
        self.call_button = CallButton(self, *rects[1])
        self.raise_button = RaiseButton(self, *rects[2])

        for x in (self.fold_button, self.call_button, self.raise_button):
            self.action_buttons.add(x)
            x.set_shown(False, 0.0)

        """
        Bet prompt
        """
        bp_dimensions = 30, 2 * h + m  # Width and height of bet prompt (in %screen)

        self.bet_prompt = BetPrompt(self, -m, -m, *bp_dimensions, "%", "br", "br")
        self.bet_prompt.set_shown(False, 0.0)

    def show_action_buttons(self, shown: bool):
        for i, x in enumerate(self.action_buttons):
            x.set_shown(shown, duration=0.4 + 0.05 * i)

    def show_bet_prompt(self, shown: bool):
        if self.game.hand.current_turn != self.game.client_player.player_number:
            self.bet_prompt.set_shown(False)
            return

        self.bet_prompt.set_shown(shown)

        for x in (self.call_button, self.fold_button):
            x.set_shown(not shown, duration=0.3)

    def show_side_pot_panel(self, shown: bool):
        self.side_pot_panel.set_shown(shown, duration=0.2)
        self.pot_text.set_shown(not shown, duration=0.2)

    def deal_cards(self):
        """
        Deals the pocket cards to all players and also moves the dealer button.
        """
        self.move_dealer_button()

        play_sound("assets/audio/game/card/deal cards.mp3")

        for i, player_display in enumerate(self.players.sprites()):
            for j in range(2):  # Every player has 2 pocket cards
                x, y = player_display.rect.midtop
                x += w_percent_to_px(1) * (1 if j else -1)

                start_pos = self.table.get_player_pos(i, (2.75, 2.75), 2)

                card = Card(self, *start_pos)
                animation = card.move_anim(random.uniform(1.75, 2), (x, y))

                # Pocket cards are added to 2 different sprite groups.
                self.all_sprites.add(card)
                player_display.pocket_cards.add(card)

                if player_display.player_data is self.game.client_player:
                    card.card_data = player_display.player_data.player_hand.pocket_cards[j]
                    animation.call_on_finish = card.reveal

        app_timer.Timer(1, self.pot_text.set_shown, (True,))


    def highlight_cards(self, showdown=False, unhighlight=False):
        """
        Select the cards that make up a poker hand and `highlight` them.

        :param showdown: If True, then highlight the winning hand (the ranked cards and the kickers).
        Otherwise, highlight the ranked cards of the client user player (the kickers are not highlighted).

        :param unhighlight: If set to True then clear all the highlights.
        """
        if app_settings.main.get_value("card_highlights") == "off":
            return

        ranked_cards: set = set()
        kickers: set = set()

        if unhighlight:
            pass

        elif showdown:
            # Showdown: Highlight the winning hand(s)
            ranked_cards = set(card for winner_index in self.game.hand.winners[0]
                                    for card in self.game.hand.players[winner_index].hand_ranking.ranked_cards)

            if app_settings.main.get_value("card_highlights") in ("all", "all_always"):
                kickers = set(card for winner_index in self.game.hand.winners[0]
                                    for card in self.game.hand.players[winner_index].hand_ranking.kickers)

        else:
            # Highlight the ranked cards of the client user
            ranked_cards = set(self.game.client_player.player_hand.hand_ranking.ranked_cards)

            if app_settings.main.get_value("card_highlights") == "all_always":
                kickers = set(self.game.client_player.player_hand.hand_ranking.kickers)

        highlighted_cards = set.union(ranked_cards, kickers)
        card_displays = self.community_cards.sprites() + [card for player_display in self.players
                                                          for card in player_display.pocket_cards]

        for card_display in card_displays:
            if card_display.is_revealed:
                card_display.show_highlight(card_display.card_data in highlighted_cards,
                                            ranked=card_display.card_data not in kickers)

    def fold_cards(self, i: int):
        """
        Discard the pocket cards of the specified player when that player folds.

        :param i: The index of the player.
        """
        player = self.players.sprites()[i]

        for card in player.pocket_cards:
            if player.player_data is self.game.client_player:
                card.fade_anim(0.25, 128)

                if self.ranking_text.shown:
                    self.ranking_text.set_text_anim("Folded:  " + self.ranking_text.text_str)

            else:
                pos = self.table.get_player_pos(i, (2.75, 2.75), 2)

                card.move_anim(random.uniform(1, 1.5), pos)

    def next_round(self):
        """
        The method that is called when the hand advances to the next round (a NEW_ROUND game event is received).
        """

        round_names = {3: "flop", 4: "turn", 5: "river"}

        if self.game.hand.winners:
            return

        for player in self.players.sprites():
            player.set_sub_text_anim("All in" if player.player_data.player_hand.all_in else "")

        self.update_chips_texts()

        """
        Show next community cards
        """
        for i in range(len(self.community_cards), len(self.game.hand.community_cards)):
            card_data = self.game.hand.community_cards[i]

            start_pos = self.table.get_edge_pos(COMM_CARD_ROTATIONS[i], (3, 3), 5)
            card = Card(self, *start_pos, "px", "tl", "ctr", card_data=card_data)

            card.move_anim(2 + i / 8, (6.5 * (i - 2), 0), "%", "ctr", "ctr",
                           call_on_finish=card.reveal)

            self.community_cards.add(card)

        anim_delay = 2 + len(self.community_cards) / 8

        """
        Card sliding sound effect
        """
        play_sound(f"assets/audio/game/card/slide/{round_names[len(self.community_cards)]}.mp3")

        app_timer.Timer(anim_delay,
                        lambda: play_sound(f"assets/audio/game/rounds/{round_names[len(self.community_cards)]}.mp3")
                        )

        """
        Update hand ranking
        """
        ranking_int = self.game.client_player.player_hand.hand_ranking.ranking_type
        ranking_str = HandRanking.TYPE_STR[ranking_int].capitalize()
        if self.game.client_player.player_hand.folded:
            ranking_str = "Folded:  " + ranking_str

        app_timer.Timer(anim_delay, self.ranking_text.set_text_anim, (ranking_str,))
        app_timer.Timer(anim_delay + 0.15, self.highlight_cards)

        """
        Hide blinds button and show ranking text on the flop round
        """
        if len(self.game.hand.community_cards) == 3:
            if self.game.client_player.player_number >= 0:
                app_timer.Timer(2, self.ranking_text.set_shown, (True,))

            self.sb_button.set_shown(False)
            self.bb_button.set_shown(False)

    def showdown(self):
        """
        Perform a showdown and reveal the winner(s) of the current hand.
        """

        self.ranking_text.set_shown(False)
        self.highlight_cards(unhighlight=True)
        self.update_chips_texts(update_players=False)

        for player in self.players.sprites():
            player.set_sub_text_anim("")

        """
        Show all pocket cards
        """
        play_sound("assets/audio/game/card/reveal cards.mp3")

        for player_display in self.players.sprites():
            if player_display.player_data is not self.game.client_player:
                for i, card in enumerate(player_display.pocket_cards.sprites()):
                    card.card_data = player_display.player_data.player_hand.pocket_cards[i]
                    card.reveal(random.uniform(1, 1.5), sfx=False)

        """
        Get a sorted list of player indexes sorted from the lowest hand ranking to the winners.
        """
        get_score = lambda x: x[1].player_data.player_hand.hand_ranking.overall_score
        # A lambda function that gets the player's overall score of an (index, player display) tuple.

        is_not_folded = lambda x: not x.player_data.player_hand.folded
        # A lambda function that returns True if the player (`x: PlayerDisplay`) is not folded.

        """
        Start revealing the hand rankings
        """
        app_async.Coroutine(self.reveal_rankings())

    def reveal_rankings(self) -> Generator[float, None, None]:
        """
        Reveal the hand rankings of each player one by one in order from the lowest ranking.
        """

        yield 2  # Delay after the `showdown` method call.

        """
        Create various lists of player displays.
        """
        sorted_players: list[PlayerDisplay]
        sorted_players = [player for player in
                          sorted(self.players, key=lambda x: x.player_data.player_hand.hand_ranking.overall_score)
                          if not player.player_data.player_hand.folded]

        n_winners = len(self.game.hand.winners[0])  # Number of main pot winners

        main_winners = sorted_players[-n_winners:]  # List of player displays who won the main pot.
        all_winners = [player for player in sorted_players
                       if player.player_data.player_hand.pots_won]  # List of player displays who won at least one of
                                                                    # the main or side pot(s)
        """
        Reveal the players' hand rankings.
        """
        for i, player_display in enumerate(sorted_players):
            # Update sub text to hand ranking
            ranking_int = player_display.player_data.player_hand.hand_ranking.ranking_type
            if ranking_int == 0:
                continue  # Don't reveal the ranking if the ranking is "n/a"

            ranking_text = HandRanking.TYPE_STR[ranking_int].capitalize()
            player_display.set_sub_text_anim(ranking_text)

            rank_number = len(sorted_players) - n_winners - i + 1  # "The current player is ranked in n-th place."

            # Play the reveal sound
            play_sound(f"assets/audio/game/showdown/reveal {rank_number}.mp3",
                       volume_mult=0.5 + 0.5 / max(1, rank_number))

            # Delay
            if player_display not in main_winners:
                yield 1 / rank_number

        """
        Create a winner crown for each winner.
        """
        show_pots = any(max(self.game.hand.players[winner_number].pots_won) != len(self.game.hand.pots) - 1
                        for winner_number in self.game.hand.winners[0])
        # If true then the player crowns show which pots have been won by its represented player.

        for player_display in all_winners:
            winner_crown = WinnerCrown(self, player_display, show_pots)
            self.winner_crowns.add(winner_crown)

        """
        Update the players' chips texts and set the pot text to 0.
        """
        self.update_chips_texts()
        self.pot_text.set_text_anim(0)

        """
        Extra effects
        """
        def set_flash_fac(flash_fac):
            self.flash_fac = int(flash_fac)

        animation = VarSlider(1.5, 50, 0, setter_func=set_flash_fac)
        self.anim_group.add(animation)

        app_timer.Timer(0.25, self.highlight_cards, (True,))

        play_sound("assets/audio/game/showdown/win.mp3", volume_mult=0.7)

    def reset_hand(self):
        """
        Reset the sprites of cards and winner crowns, and then start a new hand.
        """

        self.pot_text.set_shown(False)
        self.ranking_text.set_text("")
        self.side_pot_panel.set_shown(False)
        app_timer.Timer(1, self.side_pot_panel.reset_all_pots)

        self.sb_button.set_shown(False)
        self.bb_button.set_shown(False)
        self.highlight_cards(unhighlight=True)

        """
        Clear winner crowns
        """
        for winner_crown in self.winner_crowns.sprites():
            winner_crown.hide()

        """
        Clear cards
        """
        # Pocket cards
        for i, player in enumerate(self.players.sprites()):
            for card in player.pocket_cards.sprites():
                # self.all_sprites.remove(card)
                card_end_pos = self.table.get_player_pos(i, (3, 3), 2)
                card.move_anim(random.uniform(1.5, 2), card_end_pos)

            player.set_sub_text_anim("")  # Reset sub text

        play_sound("assets/audio/game/card/deal cards.mp3")

        # Community cards
        for card, rot in zip(self.community_cards.sprites(), COMM_CARD_ROTATIONS):
            card_end_pos = self.table.get_edge_pos(rot, (3, 3), 5)
            card.move_anim(random.uniform(2, 2.5), card_end_pos)

        app_timer.Timer(2.5, self.delete_on_new_hand)

        """
        Reset action buttons
        """
        for x in (self.fold_button, self.call_button, self.raise_button):
            x.set_shown(False, 0.0)

        self.call_button.all_in = False

    def delete_on_new_hand(self):
        """
        When starting a new hand, remove all pocket cards, community cards, and winner crowns from the `all_sprites`
        sprite group and other sprite groups.
        """

        for player in self.players.sprites():
            for card in player.pocket_cards.sprites():
                self.all_sprites.remove(card)

            player.pocket_cards.empty()

        for sprite in self.community_cards.sprites() + self.winner_crowns.sprites():
            self.all_sprites.remove(sprite)

        self.community_cards.empty()
        self.winner_crowns.empty()

    def move_dealer_button(self):
        """
        Move the dealer button to the player display of the current dealer, then shows the SB and BB button and moves it
        to their respective player displays.
        """

        dealer: PlayerDisplay = self.players.sprites()[self.game.dealer]
        sb: PlayerDisplay = self.players.sprites()[self.game.hand.blinds[0]]
        bb: PlayerDisplay = self.players.sprites()[self.game.hand.blinds[1]]

        app_timer.Sequence([
            lambda: self.dealer_button.move_to_player(0.75, dealer, interpolation=ease_in),
            0.751,
            lambda: self.sb_button.move_to_player(0.3, sb, self.dealer_button, interpolation=linear),
            0.301,
            lambda: self.bb_button.move_to_player(0.75, bb, self.sb_button, interpolation=ease_out),
        ])

    def update_chips_texts(self, update_players=True):
        self.side_pot_panel.update_all_pots()

        if self.pot_text.pot != sum(self.game.hand.pots):
            self.pot_text.set_text_anim(sum(self.game.hand.pots))

        if update_players:
            for player in self.players:
                player: PlayerDisplay
                player.update_chips()

    def update(self, dt):
        super().update(dt)

        self.game.update(dt)

        if self.flash_fac > 0:
            self.app.display_surface.fill(3 * (self.flash_fac,), special_flags=pygame.BLEND_RGB_ADD)
