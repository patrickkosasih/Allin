from app import app_settings
from app.audio import MusicPlayer
from app.scenes.game_scene import GameScene
from app.scenes.scene import Scene
from app.shared import load_image, FontSave
from app.tools import app_async
from app.widgets.basic.button import CircularButton, Button
from app.widgets.basic.textbox import Textbox
from app.widgets.menu.rooms_panel import RoomsPanel
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

        self.search_textbox = Textbox(self, -37.5, -40, 25, 8, "%", "ctr", "tl")

        self.search_button = CircularButton(self, -11.5, -40, 4, "%", "ctr", "tl")

        self.create_room_button = Button(self, 37.5, -40, 20, 8, "%", "ctr", "tr",
                                         text_str="Create Room", icon=load_image("assets/sprites/misc/plus.png"),
                                         icon_size=0.75, font=FontSave.get_font(6), nudge_by_icon=True)

        self.rooms_panel = RoomsPanel(self, 0, 1.5, 75, 62.5, "%", "ctr", "ctr",
                                      base_color=(24, 31, 37, 200),
                                      base_radius=5, pack_height=12)

        self.server_settings_button = CircularButton(self, -37.5, 40, 2.5, "%", "ctr", "bl")

    @app_async.run_as_serial_coroutine
    def join(self, room_code):
        if ClientComms.should_update_name:
            yield from ClientComms.send_request(f"name {app_settings.sep.get_value('nickname')}")
            ClientComms.should_update_name = False

        response = yield from ClientComms.send_request(f"join {room_code}")

        if response == "SUCCESS":
            game = MultiplayerGame()
            ClientComms.current_game = game
            self.app.change_scene_anim(lambda: GameScene(self.app, game), duration=0.5)

            MusicPlayer.stop()

    def back(self):
        self.app.change_scene_anim("mainmenu")
