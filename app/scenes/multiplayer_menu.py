from pygame import Vector2

from app import app_settings
from app.audio import MusicPlayer
from app.scenes.game_scene import GameScene
from app.scenes.scene import Scene
from app.shared import load_image, FontSave, percent_to_px, h_percent_to_px
from app.tools import app_async
from app.tools.names import generate_nickname
from app.widgets.basic.button import CircularButton, Button
from app.widgets.basic.textbox import Textbox
from app.widgets.menu.rooms_panel import RoomsPanel
from app.widgets.widget import Widget
from online.client.client_comms import ClientComms

from app.rules_interface.multiplayer import MultiplayerGame


class MultiplayerMenuScene(Scene):
    def __init__(self, app):
        # super().__init__(app, "multiplayer")
        super().__init__(app)

        ClientComms.connect()

        self.back_button = CircularButton(self, 1.5, 1.5, 4, "%h", "tl", "tl",
                                          command=self.back,
                                          icon=load_image("assets/sprites/menu icons/back.png"),
                                          icon_size=0.8)

        self.search_textbox = Textbox(self, -37.5, -40, 25, 8, "%", "ctr", "tl", placeholder="Enter Game ID",
                                      input_validator=str.isalpha, input_converter=str.upper)

        self.create_room_button = Button(self, 37.5, -40, 20, 8, "%", "ctr", "tr",
                                         text_str="Create Room", icon=load_image("assets/sprites/misc/plus.png"),
                                         icon_size=0.75, font=FontSave.get_font(5), nudge_by_icon=True)

        self.refresh_button = CircularButton(self, -37.5, -40, 4, "%", "ctr", "tl",
                                             icon=load_image("assets/sprites/menu icons/refresh.png"),
                                             icon_size=0.75)

        self.online_settings_button = CircularButton(self, -37.5, -40, 4, "%", "ctr", "tl",
                                                     icon=load_image("assets/sprites/menu icons/settings.png"),
                                                     icon_size=0.75)

        self.rooms_panel = RoomsPanel(self, 0, 40, 75, 70, "%", "ctr", "mb",
                                      base_color=(24, 31, 37, 200),
                                      base_radius=5, pack_height=12)

        # Alignment thingy for pixel perfect margins between the buttons because of my OCD.
        d_pos = Vector2(self.rooms_panel.rect.top - self.search_textbox.rect.bottom, 0)
        self.refresh_button.set_pos(*self.create_room_button.get_pos("px", "tl", "ml") - d_pos, "px", "tl", "mr")
        self.online_settings_button.set_pos(*self.refresh_button.get_pos("px", "tl", "ml") - d_pos, "px", "tl", "mr")

    @app_async.run_as_serial_coroutine
    def join(self, room_code):
        if ClientComms.should_update_name:
            name = app_settings.sep.get_value('nickname')
            if not name:
                name = generate_nickname()

            yield from ClientComms.send_request(f"name {name}")
            ClientComms.should_update_name = False

        response = yield from ClientComms.send_request(f"join {room_code}")

        if response == "SUCCESS":
            game = MultiplayerGame()
            ClientComms.current_game = game
            self.app.change_scene_anim(lambda: GameScene(self.app, game), duration=0.5)

            MusicPlayer.stop()

    def back(self):
        self.app.change_scene_anim("mainmenu")
