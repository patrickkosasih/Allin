import pygame
import random

from app.animations.interpolations import ease_out, ease_in, linear
from app.audio import play_sound
from app.widgets.menu.side_menu import SideMenu, SideMenuButton

from rules.basic import HandRanking
from rules.game_flow import GameEvent
from rules.singleplayer import InterfaceGame, SingleplayerGame

from app.scenes.scene import Scene
from app.shared import *
from app.tools import app_timer

from app import widgets, app_settings
from app.widgets.game.card import Card
from app.widgets.game.action_buttons import FoldButton, RaiseButton, CallButton
from app.widgets.game.dealer_button import DealerButton
from app.widgets.game.winner_crown import WinnerCrown
from app.widgets.game.player_display import PlayerDisplay
from app.widgets.game.bet_prompt import BetPrompt

from app.animations.var_slider import VarSlider
from app.animations.fade import FadeAlphaAnimation


COMM_CARD_ROTATIONS = (198, 126, 270, 54, -18)
"""`COMM_CARD_ROTATIONS` defines the rotation for the animation's starting position of the n-th community card."""


## noinspection PyUnresolvedReferences,PyTypeChecker
class GameScene(Scene):
    def __init__(self, app, game: InterfaceGame):
        super().__init__(app, "")

        self.game = game
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
        self.pot_text.set_visible(False, duration=0)

        self.ranking_text = widgets.game.table_texts.RankingText(self, 0, 12.5, 17.5, 5, "%", "ctr", "ctr")
        self.ranking_text.set_visible(False, duration=0)

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

            case GameEvent.NEW_DEAL:
                self.deal_cards()

            case GameEvent.NEW_ROUND | GameEvent.SKIP_ROUND:
                self.next_round()

            case GameEvent.DEAL_END:
                app_timer.Timer(1, self.showdown)

            case GameEvent.RESET_DEAL:
                self.reset_deal()

            case _:
                player_action = True

        if not player_action:
            return

        """
        Update the subtext on a player action
        """
        is_sb: bool = (event.code == GameEvent.START_DEAL) and (event.prev_player == self.game.deal.blinds[0])
        # True if the current game event is the small blinds (SB) action.

        if event.prev_player >= 0:
            action_str = event.message.capitalize()

            if event.bet_amount > 0 and event.message != "fold":
                action_str += f" ${event.bet_amount:,}"

                """
                Update the pot text
                """
                if not is_sb:
                    total_pot = sum(self.game.deal.pots) + self.game.deal.current_round_pot
                    self.pot_text.set_text_anim(total_pot)

                """
                Money sound effect
                """
                play_sound("assets/audio/game/actions/money.mp3", 0.5)

            self.players.sprites()[event.prev_player].set_sub_text_anim(action_str)
            self.players.sprites()[event.prev_player].update_money()

        """
        Action sound effect
        """
        if event.code == GameEvent.START_DEAL:
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
                x.update_bet_amount(self.game.deal.bet_amount)
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

        for i, old_player_display in enumerate(old_group.sprites()):
            if old_player_display not in self.players:
                """
                3. Remove player display
                """

                pos = self.table.get_edge_pos(self.table.get_player_rotation(i, len(old_group)),
                                              (3, 3))

                old_player_display.move_anim(1.5 + i * time_interval, pos,
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

        self.fold_button = FoldButton(self, *rects[0], player=self.game.client_player)
        self.call_button = CallButton(self, *rects[1], player=self.game.client_player)
        self.raise_button = RaiseButton(self, *rects[2], player=self.game.client_player)

        for x in (self.fold_button, self.call_button, self.raise_button):
            self.action_buttons.add(x)
            x.set_shown(False, 0.0)

        """
        Bet prompt
        """
        bp_dimensions = 30, 2 * h + m  # Width and height of bet prompt (in %screen)

        self.bet_prompt = BetPrompt(self, -m, -m, *bp_dimensions, "%", "br", "br",
                                    game_scene=self, player=self.game.client_player)
        self.bet_prompt.set_shown(False, 0.0)

    def show_action_buttons(self, shown: bool):
        for i, x in enumerate(self.action_buttons):
            x.set_shown(shown, duration=0.4 + 0.05 * i)

    def show_bet_prompt(self, shown: bool):
        if self.game.deal.current_turn != self.game.client_player.player_number:
            self.bet_prompt.set_shown(False)
            return

        self.bet_prompt.set_shown(shown)

        for x in (self.call_button, self.fold_button):
            x.set_shown(not shown, duration=0.3)

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

        app_timer.Timer(1, self.pot_text.set_visible, (True,))


    def highlight_cards(self, showdown=False, unhighlight=False):
        """
        Select the cards that make up a poker hand and `highlight` them.

        :param showdown: If True, then highlight the winning hand (the ranked cards and the kickers).
        Otherwise, highlight the ranked cards of the client user player (the kickers are not highlighted).

        :param unhighlight: If set to True then clear all the highlights.
        """
        # TODO Hey..... IMPROVE THIS AS WELL

        if app_settings.main.get_value("card_highlights") == "off":
            return

        ranked_cards: set
        kickers: set = set()

        if showdown:
            # Showdown: Highlight the winning hand(s)
            ranked_cards = set(x for winner in self.game.deal.winners[0] for x in winner.hand_ranking.ranked_cards)

            if app_settings.main.get_value("card_highlights") in ("all", "all_always"):
                kickers = set(x for winner in self.game.deal.winners[0] for x in winner.hand_ranking.kickers)

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
                card_display.show_highlight(card_display.card_data in highlighted_cards and not unhighlight,
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

                if self.ranking_text.visible:
                    self.ranking_text.set_text_anim("Folded:  " + self.ranking_text.text_str)

            else:
                pos = self.table.get_player_pos(i, (2.75, 2.75), 2)

                card.move_anim(random.uniform(1, 1.5), pos)

    def next_round(self):
        """
        The method that is called when the deal advances to the next round (a NEW_ROUND game event is received).
        """

        round_names = {3: "flop", 4: "turn", 5: "river"}

        if self.game.deal.winners:
            return

        for player in self.players.sprites():
            player.set_sub_text_anim("All in" if player.player_data.player_hand.all_in else "")

        self.update_money_texts()

        """
        Show next community cards
        """
        for i in range(len(self.community_cards), len(self.game.deal.community_cards)):
            card_data = self.game.deal.community_cards[i]

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
        if len(self.game.deal.community_cards) == 3:
            if self.game.client_player.player_number >= 0:
                app_timer.Timer(2, self.ranking_text.set_visible, (True,))

            self.sb_button.set_shown(False)
            self.bb_button.set_shown(False)

    def showdown(self):
        """
        Perform a showdown and reveal the winner(s) of the current deal.
        """

        self.ranking_text.set_visible(False)
        self.highlight_cards(unhighlight=True)
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

        sorted_players = [i for i, player in sorted(enumerate(self.players), key=get_score) if is_not_folded(player)]
        # A list of player indexes who hasn't folded sorted by the hand ranking.

        """
        Start revealing the hand rankings
        """
        app_timer.Timer(2, self.reveal_rankings, args=(sorted_players,))

    def reveal_rankings(self, sorted_players, i=0):
        """
        Reveal the hand rankings of each player one by one in order from the lowest ranking.

        :param sorted_players: The list of player indexes sorted by the hand ranking.
        :param i: The index of sorted_players to show. This method recursively calls itself (using a timer with a delay)
        with `i + 1` as the new argument.
        """
        # TODO Hey..... IMPROVE THIS
        if i >= len(sorted_players):
            """
            Execute once when revealing the winner(s):
            
            Update the money texts, flash the screen, set the pot text to 0, and play the win sound effect.
            """
            self.update_money_texts()

            def set_flash_fac(flash_fac):
                self.flash_fac = int(flash_fac)

            animation = VarSlider(1.5, 50, 0, setter_func=set_flash_fac)
            self.anim_group.add(animation)

            self.pot_text.set_text_anim(0)
            app_timer.Timer(0.25, self.highlight_cards, (True,))

            play_sound("assets/audio/game/showdown/win.mp3", volume_mult=0.7)

            return

        player_display = self.players.sprites()[sorted_players[i]]
        player_hand = player_display.player_data.player_hand

        rank_number = len(sorted_players) - len(self.game.deal.winners[0]) - i + 1
        # e.g. rank_number = 2 -> The current player is the player placing in 2nd place.

        """
        Update sub text to hand ranking
        """
        ranking_int = player_hand.hand_ranking.ranking_type
        ranking_text = HandRanking.TYPE_STR[ranking_int].capitalize()
        player_display.set_sub_text_anim(ranking_text)

        """
        Ranking reveal sound effect
        """
        try:
            play_sound(f"assets/audio/game/showdown/reveal {rank_number}.mp3",
                       volume_mult=0.5 + 0.5 / max(1, rank_number))
        except FileNotFoundError:
            pass

        if player_hand in self.game.deal.winners[0]:
            """
            Reveal the winner(s)
            """
            # Create a winner crown
            winner_crown = WinnerCrown(self, player_display)
            self.winner_crowns.add(winner_crown)

            # Update player money text
            player_display.update_money()

            # Call `reveal_rankings` again without delay to reveal other winners if there are any.
            # Calling the function when the new `i` is out of range creates the screen flash effect.
            self.reveal_rankings(sorted_players, i + 1)

        else:
            """
            Reveal the next loser(s)
            """
            next_player_delay = 1 / rank_number
            app_timer.Timer(next_player_delay, self.reveal_rankings, args=(sorted_players, i + 1))

    def reset_deal(self):
        """
        Reset the sprites of cards and winner crowns, and then start a new deal.
        """

        self.pot_text.set_visible(False)
        self.ranking_text.set_text("")

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

        app_timer.Timer(2.5, self.delete_on_new_deal)

        """
        Reset action buttons
        """
        for x in (self.fold_button, self.call_button, self.raise_button):
            x.set_shown(False, 0.0)

        self.call_button.all_in = False

    def delete_on_new_deal(self):
        """
        When starting a new deal, remove all pocket cards, community cards, and winner crowns from the `all_sprites`
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
        sb: PlayerDisplay = self.players.sprites()[self.game.deal.blinds[0]]
        bb: PlayerDisplay = self.players.sprites()[self.game.deal.blinds[1]]

        app_timer.Sequence([
            lambda: self.dealer_button.move_to_player(0.75, dealer, interpolation=ease_in),
            0.75,
            lambda: self.sb_button.move_to_player(0.3, sb, self.dealer_button, interpolation=linear),
            0.3,
            lambda: self.bb_button.move_to_player(0.75, bb, self.sb_button, interpolation=ease_out),
        ])

    def update_money_texts(self):
        if self.pot_text.pot != sum(self.game.deal.pots):
            self.pot_text.set_text_anim(sum(self.game.deal.pots))

        for player in self.players:
            player: PlayerDisplay
            player.update_money()

    def update(self, dt):
        super().update(dt)

        self.game.timer_group.update(dt)

        if self.flash_fac > 0:
            self.app.display_surface.fill(3 * (self.flash_fac,), special_flags=pygame.BLEND_RGB_ADD)
