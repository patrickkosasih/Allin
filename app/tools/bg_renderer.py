import pygame
from typing import TYPE_CHECKING

from app.animations.var_slider import VarSlider
from app.widgets.widget import Widget
if TYPE_CHECKING:
    from app.scenes.side_scenes import BackgroundScene


MAX_SCALE_FOR_SMOOTH = 1.05


class BackgroundRenderer:
    def __init__(self, scene: "BackgroundScene"):
        self._scene = scene
        # self._display_surface = scene.app.display_surface

        self._scale = 1.0
        self._positioner = Widget(self._scene, 0, 0, 100, 100, "%", "ctr", "ctr")
        # A dummy widget whose position tells the background renderer where the image should be drawn/blitted.

        self._unscaled_image: pygame.Surface = pygame.image.load("assets/sprites/misc/background.png").convert()
        self._scale_to_screen: float = (self._positioner.rect.w + 10) / self._unscaled_image.get_width()

        self._scaled_image: pygame.Surface = pygame.transform.smoothscale_by(self._unscaled_image, self._scale_to_screen)

        self.set_scale(self._scale)

    def set_pos(self, *args, **kwargs):
        self._positioner.set_pos(*args, **kwargs)

    def set_scale(self, scale: float):
        scale_func = pygame.transform.smoothscale_by if scale <= MAX_SCALE_FOR_SMOOTH else pygame.transform.scale_by

        self._scale = scale
        self._scaled_image = scale_func(self._unscaled_image, scale * self._scale_to_screen).convert()

    def set_alpha(self, alpha: int or float):
        self._unscaled_image.set_alpha(int(alpha))
        self._scaled_image.set_alpha(int(alpha))

    def move_anim(self, *args, **kwargs):
        self._positioner.move_anim(*args, **kwargs)

    def scale_anim(self, duration, end_scale, start_scale=-1, **kwargs):
        if duration > 0:
            anim = VarSlider(duration,
                             start_val=self._scale if start_scale == -1 else start_scale,
                             end_val=end_scale,
                             setter_func=self.set_scale, **kwargs)

            self._scene.anim_group.add(anim)
        else:
            self.set_scale(end_scale)

    def fade_anim(self, duration, end_alpha, start_alpha=-1, **kwargs):
        if duration > 0:
            if start_alpha == -1:
                start_alpha = self._scaled_image.get_alpha()
            if start_alpha is None:
                start_alpha = 255

            anim = VarSlider(duration,
                             start_val=self._scaled_image.get_alpha() if start_alpha == -1 else start_alpha,
                             end_val=end_alpha,
                             setter_func=self.set_alpha, **kwargs)

            self._scene.anim_group.add(anim)
        else:
            self.set_alpha(end_alpha)

    def update(self, dt):
        self._scene.app.display_surface.blit(
            self._scaled_image, self._scaled_image.get_rect(center=self._positioner.rect.center)
        )
