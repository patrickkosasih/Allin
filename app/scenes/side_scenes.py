from app import app_settings
from app.animations.interpolations import ease_out, ease_in_out, linear
from app.scenes.scene import Scene
from app.widgets.basic.fps_counter import FPSCounter
from app.tools.bg_renderer import BackgroundRenderer
from app.widgets.widget import Widget


class OverlayScene(Scene):
    def __init__(self, app):
        super().__init__(app, "")

        self.fader = Widget(self, 0, 0, 100, 100, "%", "tl", "tl")
        self.fader.image.fill((0, 0, 0))
        self.fader.image.set_alpha(0)

        self.fps_counter = FPSCounter(self, 0.5, 0.5, 15, 5, "%", "tl", "tl")


class BackgroundScene(Scene):
    def __init__(self, app):
        super().__init__(app, "")

        self._bg_renderer = BackgroundRenderer(self)
        self._tint = Widget(self, 0, 0, 101, 101, "%", "tl", "tl")

        if app_settings.main.get_value("startup_sequence") and app_settings.main.get_value("show_bg"):
            self._tint.image.fill((0, 0, 0))
        else:
            self._tint.image.fill("#123456")
            self._tint.image.set_alpha(0)

    def move_on_startup(self):
        if not app_settings.main.get_value("show_bg"):
            return

        self._bg_renderer.set_pos(0, -100, "%", "mb", "mb")
        self._bg_renderer.move_anim(3.5, (0, 0), "px", "ctr", "ctr",
                                   interpolation=lambda x: ease_out(x, power=2))
        self._tint.fade_anim(3.5, 0,
                                  interpolation=linear)
        self._bg_renderer.scale_anim(4.5, 1.1, 1.5,
                                    interpolation=lambda x: ease_in_out(x, power=3))

    def update(self, dt):
        self._bg_renderer.update(dt)
        super().update(dt)

    @property
    def bg_renderer(self):
        return self._bg_renderer

    @property
    def tint(self):
        return self._tint
