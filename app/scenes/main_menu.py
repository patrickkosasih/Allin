import pygame.image

from app import app_settings
from app.animations.fade import FadeColorAnimation
from app.animations.interpolations import ease_out
from app.scenes.scene import Scene
from app.tools import app_timer
from app.tools.app_timer import Coroutine
from app.widgets.basic.button import Button
from app.shared import *
from app.widgets.menu.welcome_text import WelcomeText
from app.widgets.widget import Widget

MAIN_MENU_BUTTON_COLOR = (24, 31, 37, 169)

COPYRIGHT_TEXT = "Copyright (c) 2023-2024 Patrick Kosasih."
COPYRIGHT_TEXT_SUB = "All rights reserved."


class MainMenuScene(Scene):
    def __init__(self, app, startup_sequence=False):
        super().__init__(app, "mainmenu")

        self.welcome_text = None

        self.logo = Widget(self, 2, 2, 10, 10, "%h", "tl", "tl")
        self.logo.image = load_image("assets/sprites/misc/logo.png", (0, self.logo.rect.h))

        self.version_text = Widget(self, 1, -0.5, 3, 3, "%h", "bl", "bl")
        self.version_text.image = FontSave.get_font(3).render(VERSION_TEXT, True, "white")

        self.copyright_text = Widget(self, -1, -4, 3, 3, "%h", "br", "br")
        self.copyright_text.image = FontSave.get_font(3).render(COPYRIGHT_TEXT, True, "white")

        self.copyright_text_sub = Widget(self, -1, -0.5, 3, 3, "%h", "br", "br")
        self.copyright_text_sub.image = FontSave.get_font(3).render(COPYRIGHT_TEXT_SUB, True, "white")

        """
        Buttons
        """

        # region Buttons
        self.singleplayer_button = Button(self, -11, -7.5, 20, 50, "%", "ctr", "ctr", text_str="Singleplayer",
                                          rrr=h_percent_to_px(5), b_thickness=0, color=MAIN_MENU_BUTTON_COLOR,
                                          font=FontSave.get_font(5),
                                          icon=load_image("assets/sprites/menu icons/singleplayer.png"),
                                          icon_size=0.6, text_align="bottom", icon_align="middle", text_align_offset=0.04,
                                          command=self.singleplayer_click)

        self.multiplayer_button = Button(self, 11, -7.5, 20, 50, "%", "ctr", "ctr", text_str="Multiplayer",
                                         rrr=h_percent_to_px(5), b_thickness=0, color=MAIN_MENU_BUTTON_COLOR,
                                         font=FontSave.get_font(5),
                                         icon=load_image("assets/sprites/menu icons/multiplayer.png"),
                                         icon_size=0.6, text_align="bottom", icon_align="middle", text_align_offset=0.04,
                                         command=self.multiplayer_click)

        self.settings_button = Button(self, -11, 25, 20, 10, "%", "ctr", "ctr", text_str="Settings",
                                      b_thickness=0, color=MAIN_MENU_BUTTON_COLOR, font=FontSave.get_font(5),
                                      icon=load_image("assets/sprites/menu icons/settings.png"), icon_size=0.8,
                                      command=self.settings_click)

        self.quit_button = Button(self, 11, 25, 20, 10, "%", "ctr", "ctr", text_str="Quit",
                                  b_thickness=0, color=MAIN_MENU_BUTTON_COLOR, font=FontSave.get_font(5),
                                  icon=load_image("assets/sprites/menu icons/quit.png"), icon_size=0.8,
                                  command=self.app.quit)

        # endregion

        self.startup_fade = [self.singleplayer_button, self.multiplayer_button, self.settings_button, self.quit_button,
                             self.version_text, self.copyright_text, self.copyright_text_sub]

        if startup_sequence:
            self.startup_sequence()

    """
    Start-up sequence
    """

    def startup_sequence(self):
        for _ in self.set_startup_shown(False, 0, 0):
            pass

        self.app.solid_bg_color = (0, 0, 0)
        self.logo.set_pos(2, -10, "%h")

        if app_settings.main.get_value("background"):
            self.app.background_scene.background.image.set_alpha(0)

        else:
            FadeColorAnimation(6, (0, 0, 0), (18, 52, 86),  # end_color = "#123456"
                               setter_func=lambda x: setattr(self.app, "solid_bg_color", x),
                               anim_group=self.anim_group)

        self.welcome_text = WelcomeText(self, 0, 0, 50, 50, "%", "ctr", "ctr")

        app_timer.Sequence([
            1.5,
            self.app.background_scene.move_on_startup,

            2, lambda: self.welcome_text.fade_anim(1.5, 0),

            1, lambda: Coroutine(self.set_startup_shown(True, 0.5, 0.1)),
            lambda: self.logo.move_anim(0.5, (2, 2), interpolation=ease_out),

            1.5, lambda: self.welcome_text.delete("welcome_text"),
            lambda: setattr(self.app, "solid_bg_color", "#123456")
        ])

    def set_startup_shown(self, shown: bool, duration: float, interval: float):
        for button in self.startup_fade:
            button.fade_anim(duration, 255 if shown else 0)
            button.disabled = not shown

            if interval > 0:
                yield interval

    """
    Button commands
    """

    def singleplayer_click(self):
        self.app.change_scene_anim("singleplayer")

    def multiplayer_click(self):
        self.app.change_scene_anim("multiplayer")

    def settings_click(self):
        self.app.change_scene_anim("settings")
