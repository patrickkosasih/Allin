import pygame.gfxdraw

from app.tools.draw import draw_circle
from app.widgets.widget import Widget, WidgetComponent


PFP_COLORS = [
    (27, 127, 127)
]


class ProfilePic(Widget):
    def __init__(self, parent, *rect_args):
        super().__init__(parent, *rect_args)

        self.base = WidgetComponent(self, 0, 0, 100, 100, "%", "ctr", "ctr")
        self.draw_base()

        # TODO add more stuffs, make it customizable

    def draw_base(self):
        r = self.rect.h // 2
        draw_circle(self.base.image, r, r, r, PFP_COLORS[0])
