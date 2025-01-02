import random
import time
from threading import Thread

from app.scenes.scene import Scene
from app.shared import load_image
from app.tools import app_async
from app.widgets.basic.button import CircularButton, Button
from online.client.client_comms import ClientComms

from online.packets import Packet


class MultiplayerMenuScene(Scene):
    def __init__(self, app):
        # super().__init__(app, "multiplayer")
        super().__init__(app)

        ClientComms.connect()

        self.back_button = CircularButton(self, 1.5, 1.5, 4, "%h", "tl", "tl",
                                          command=self.back,
                                          icon=load_image("assets/sprites/menu icons/back.png"),
                                          icon_size=0.8)

        self.test_button = Button(self, 0, 0, 20, 20, "%", "ctr", "ctr",
                                  command=self.test_send_thing,
                                  text_str="oi oi oi")

    @app_async.run_as_serial_coroutine
    def test_send_thing(self):
        print("wait 1 second")
        yield 1

        print("wait 0.5 second")
        yield 0.5

        response = yield from ClientComms.send_request("echo omaygyatt")
        print(f"result of send request: {response}")

        response = yield from ClientComms.send_request("join oiia")
        print(f"result of send request: {response}")

    def back(self):
        self.app.change_scene_anim("mainmenu")
