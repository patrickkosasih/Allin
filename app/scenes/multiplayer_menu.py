from app import app_settings
from app.audio import MusicPlayer
from app.scenes.game_scene import GameScene
from app.scenes.scene import Scene
from app.shared import load_image
from app.tools import app_async
from app.widgets.basic.button import CircularButton, Button
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

        self.join_button = Button(self, 0, 0, 20, 20, "%", "ctr", "ctr",
                                  command=lambda: self.join("AAAA"),
                                  text_str="JOIN GAME RAHHHH")

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
