from typing import Callable

import pygame

from app import audio, app_settings
from app.scenes.multiplayer_menu import MultiplayerMenuScene
from app.scenes.settings_scene import SettingsScene
from app.scenes.side_scenes import BackgroundScene, OverlayScene
from app.scenes.singleplayer_menu import SingleplayerMenuScene
from app.scenes.scene import Scene
from app.scenes.main_menu import MainMenuScene
from app.shared import load_image, FontSave
from app.tools import app_timer, app_async
from app.widgets.listeners import MouseListener
from online.client.client_comms import ClientComms


class App:
    def __init__(self):
        pygame.init()

        # pygame.key.set_repeat(500, 50)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(32)

        audio.SoundGroup.update_volume()
        audio.MusicPlayer.update_volume(autoplay=False)

        ClientComms.app = self

        """
        Pygame and app attributes
        """
        self.fps_limit = 60
        self.windowed = False
        self.window_resolution = (1280, 720)

        self.screen = None
        self.update_display_settings(force_update_window=True)

        self.display_surface = pygame.display.get_surface()
        self.clock = pygame.time.Clock()

        self.running = True

        """
        Side scenes: Background and overlay
        """
        self.solid_bg_color = "#123456"
        self.show_background = app_settings.main.get_value("background")

        self.background_scene = BackgroundScene(self)
        self.overlay_scene = OverlayScene(self)

        """
        Scene and scene changing system
        """
        self.scene = MainMenuScene(self, startup_sequence=app_settings.main.get_value("startup_sequence"))
        self.scene_cache = {
            "singleplayer": SingleplayerMenuScene(self),
            "settings": SettingsScene(self)
        }

        self.changing_scene = False
        self.reset_next_dt = False

        """
        Title and icon
        """
        pygame.display.set_caption("Allin")
        pygame.display.set_icon(load_image("assets/sprites/misc/icon.png"))

        audio.MusicPlayer.play(intro=True)

    def run(self):
        while self.running:
            """
            Tick
            """
            dt = self.clock.tick(self.fps_limit) / 1000

            if self.reset_next_dt:
                dt = 0
                self.reset_next_dt = False

            """
            Event loop
            """
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                    self.scene.broadcast_keyboard(event)
                    self.overlay_scene.broadcast_keyboard(event)

                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL):
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        MouseListener.mouse_down = True
                    elif event.type == pygame.MOUSEBUTTONUP:
                        MouseListener.mouse_down = False

                    self.scene.broadcast_mouse(event)
                    self.overlay_scene.broadcast_mouse(event)

                if event.type == pygame.MOUSEMOTION:
                    MouseListener.mouse_x, MouseListener.mouse_y = event.pos

            """
            Updates
            """
            app_timer.default_group.update(dt)

            self.display_surface.fill(self.solid_bg_color)

            if self.show_background:
                self.background_scene.update(dt)
            self.scene.update(dt)
            self.overlay_scene.update(dt)

            pygame.display.update()

        app_settings.main.save()
        pygame.quit()

    def quit(self):
        self.running = False

    def change_scene(self, scene: Scene or str or Callable[[None], Scene], cache_old_scene=True):
        old_scene = self.scene
        self.reset_next_dt = True

        if issubclass(type(scene), Scene):
            self.scene = scene

        elif type(scene) is str:
            if scene in self.scene_cache and scene != "":
                self.scene = self.scene_cache[scene]

            else:
                match scene:
                    case "mainmenu":
                        self.scene = MainMenuScene(self)

                    case "singleplayer":
                        self.scene = SingleplayerMenuScene(self)

                    case "multiplayer":
                        self.scene = MultiplayerMenuScene(self)

                    case "settings":
                        self.scene = SettingsScene(self)

                    case "game":
                        raise ValueError("cannot change to game scene by string id")

                    case _:
                        raise ValueError(f"invalid scene id: {scene}")

        elif callable(scene):
            self.scene = scene()

        else:
            raise TypeError("the scene argument must be either a string, an instance of Scene, or a function that"
                            "returns a Scene instance")

        if cache_old_scene and old_scene.scene_cache_id:
            self.scene_cache[old_scene.scene_cache_id] = old_scene

    def change_scene_anim(self, scene: Scene or str or Callable[[None], Scene], cache_old_scene=True, duration=0.2):
        if self.changing_scene:
            return

        self.changing_scene = True

        app_timer.Sequence([
            lambda: self.overlay_scene.fader.fade_anim(duration, 255),
            duration + 0.1,
            lambda: self.change_scene(scene, cache_old_scene),
            lambda: self.overlay_scene.fader.fade_anim(duration, 0),
            lambda: setattr(self, "changing_scene", False)
        ])

    def leave_game(self):
        if ClientComms.is_in_multiplayer():
            # Multiplayer
            ClientComms.current_game = None
            app_async.Coroutine(ClientComms.send_request("leave"))

        self.scene.app.change_scene_anim("mainmenu", cache_old_scene=False, duration=0.5)
        self.scene.app.background_scene.background.fade_anim(0.25, 254)

        audio.SoundGroup.stop_all_sounds()
        app_timer.Timer(0.75, audio.MusicPlayer.play)

    def update_display_settings(self, force_update_window=False):
        prev_windowed = self.windowed
        prev_resolution = self.window_resolution

        self.fps_limit = app_settings.main.get_value("fps_limit")
        self.windowed = app_settings.main.get_value("windowed")
        self.window_resolution = app_settings.main.get_value("window_resolution")
        self.show_background = app_settings.main.get_value("background")

        update_window = (force_update_window or prev_windowed != self.windowed or
                         (prev_resolution != self.window_resolution and self.windowed))

        if update_window:
            if self.windowed:
                self.screen = pygame.display.set_mode(self.window_resolution)
            else:
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

            self.scene_cache = {}
            FontSave.reset()

            self.overlay_scene = OverlayScene(self)
            self.background_scene = BackgroundScene(self)

        return update_window

