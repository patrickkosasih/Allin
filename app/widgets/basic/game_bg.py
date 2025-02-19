import pygame

from app import app_settings
from app.animations.var_slider import VarSlider
from app.shared import load_image
from app.widgets.widget import Widget, WidgetComponent


class GameBackground(Widget):
    def __init__(self, parent, *rect_args):
        super().__init__(parent, *rect_args)

        self._unscaled_image: pygame.Surface = load_image("assets/sprites/misc/background.png")
        self._scale_to_screen: float = self.rect.width / self._unscaled_image.get_width()
        self._scale = 1.0

        self._scaled_image: pygame.Surface = self._unscaled_image
        self.set_scale(self._scale)

    def set_scale(self, scale, smooth=True):
        scale_func = pygame.transform.smoothscale_by if smooth else pygame.transform.scale_by
        self._scaled_image = scale_func(self._unscaled_image, scale * self._scale_to_screen)

    def scale_anim(self, duration, end_scale, start_scale=-1, **kwargs):
        if duration > 0:
            anim = VarSlider(duration,
                             start_val=self._scale if start_scale == -1 else start_scale,
                             end_val=end_scale,
                             setter_func=self.set_scale, **kwargs,
                             call_on_finish=lambda: self.set_scale(1.0, smooth=True))
            self.scene.anim_group.add(anim)
        else:
            self.set_scale(end_scale)

    def update(self, dt):
        self.image.blit(self._scaled_image, self._scaled_image.get_rect(center=(self.rect.w / 2, self.rect.h / 2)))
