import pygame
import pygame.sprite
import pygame.gfxdraw

from app.audio import play_sound
from app.shared import *
from app.widgets.listeners import MouseListener
from app.widgets.widget import WidgetComponent


DEFAULT_COLOR = (128, 128, 128)


class Button(MouseListener):
    def __init__(self, parent, *rect_args,
                 color=DEFAULT_COLOR, command: Callable = None, disabled=False,
                 text_str="", text_color=(255, 255, 255), font: pygame.font.Font = None,
                 b_color=None, b_thickness=0, rrr=-1,
                 icon: pygame.Surface or None = None, icon_size: float = 1.0,
                 text_align="middle", icon_align="left", text_align_offset=0, nudge_by_icon=True):

        """
        Parameters:

        :param rect: The AutoRect positioning of the button.
        :param color: Background color of button.
        :param command: The function that is run when the button is clicked.

        :param text_str: The string data of the button's text.
        :param text_color: Text / foreground color of button.
        :param font: The font of the button's text.

        :param b_color: The color of the button's border.
        :param b_thickness: The thickness of the button's border. If set to 0 then no border is drawn.
        :param rrr: The corner radius of the rounded rectangle-shaped button. RRR: Rounded rectangle radius.

        :param icon: The icon of the button
        :param icon_size: The scale of the icon based on the button's height. Icon height = Button height * Icon size.

        :param text_align: The alignment of the text. Possible alignments: "middle" (default), "top", "bottom".
        :param icon_align: The alignment of the icon. Possible alignments: "left" (default), "right", "middle".
        :param text_align_offset: The offset of the text when it is aligned at the top or bottom.
                                  Text y pos = Original text y pos +- (Button height * Text align offset).

        :param nudge_by_icon: If set to true then the text is slightly moved to the left/right so that it's also centered
                              based on the icon. idfk man
        """

        super().__init__(parent, *rect_args)

        """
        General button attributes
        """
        self.command = command if command else lambda: None
        self.disabled = disabled

        """
        Button appearance
        """

        self.color = color
        self.b_color = b_color if b_color else hsv_factor(color, vf=0.75)
        self.b_thickness = b_thickness
        self.text_color = text_color
        self.rrr = rrr
        self._brightness = None
        self.nudge_by_icon = nudge_by_icon

        """
        Components
        """

        # Base
        self.base = WidgetComponent(self, 0, 0, 100, 100, "%", "ctr", "ctr")
        self.draw_base()

        # Icon
        self.icon = WidgetComponent(self, 0, 0, 0, 0, "%", "ml", "ml")

        self.icon_size = icon_size
        self.icon_align = icon_align

        self.set_icon(icon, icon_size)

        # Text
        self.text = WidgetComponent(self, 0, 0, 100, 100, "%", "ctr", "ctr")

        self.font = font if font else FontSave.get_font(4)
        self.text_str = text_str
        self.text_align = text_align
        self.text_align_offset = text_align_offset

        self.set_text(self.text_str)

        self.draw()

    def draw_base(self):
        """
        Draw a rounded rectangle for the button with the set color and border color attributes.
        """
        draw_rounded_rect(self.base.image, self.base.rect, self.color, self.b_color, self.b_thickness, self.rrr)

    def set_text(self, text_str: str):
        self.text_str = text_str
        self.text.image = self.font.render(self.text_str, True, self.text_color)

        x = self.rect.w / 2

        if self.icon and self.nudge_by_icon:
            if self.icon_align == "left":
                x += (3.1415 / 8 - (1 - self.icon_size) / 2) * self.rect.h
            elif self.icon_align == "right":
                x -= (3.1415 / 8 - (1 - self.icon_size) / 2) * self.rect.h

        match self.text_align:
            case "top":     y = self.text.image.get_height() / 2 + self.rect.h * self.text_align_offset
            case "middle":  y = self.rect.h / 2
            case "bottom":  y = self.rect.h - self.text.image.get_height() / 2 - self.rect.h * self.text_align_offset
            case _:         raise ValueError(f"invalid text alignment: {self.text_align}")

        self.text.rect = self.text.image.get_rect(center=(x, y))

    def set_icon(self, icon: pygame.Surface, size=1.0):
        if not icon:
            icon = pygame.Surface((1, 1), pygame.SRCALPHA)
            self.icon.image = icon
            self.icon.rect = (0, 0, 1, 1)
            return

        """
        Icon positioning
        
        Icon height = Button height * Icon size.
        Icon width = (Original width / Original height) * New icon height.
        """

        h = int(self.rect.h * size)
        w = int((icon.get_width() / icon.get_height()) * h)

        y = self.rect.h / 2

        match self.icon_align:
            case "left":    x = y
            case "middle":  x = self.rect.w / 2
            case "right":   x = self.rect.w - y
            case _:         raise ValueError(f"invalid icon alignment: {self.icon_align}")

        """
        Set attributes
        """
        self.icon_size = size

        self.icon.image = pygame.transform.smoothscale(icon, (w, h))
        self.icon.rect = self.icon.image.get_rect(center=(x, y))

    def set_color(self, color=None, b_color=None):
        if color:
            self.color = color
        if b_color:
            self.b_color = b_color

        self.draw_base()

    def brighten(self, brightness):
        """
        Fill the image with the BLEND_ADD or BLEND_SUB special flag to brighten/darken the button.

        :param brightness: The brightness factor. If the value is negative then the button is darkened. Value must be
                           between -255 to 255.
        """
        if brightness >= 0:
            self.image.fill(3 * (brightness,), special_flags=pygame.BLEND_ADD)

        else:
            self.image.fill(3 * (-brightness,), special_flags=pygame.BLEND_SUB)

    def on_click(self, event):
        if event.button == 1 and not self.disabled:
            self.command()
            play_sound("assets/audio/widgets/button.mp3")

    def update(self, dt):
        super().update(dt)

        if self.disabled:
            # self.brighten(-60)
            pass

        else:
            """
            Update button apperance based on mouse states
            """
            if self.hover:
                if self.mouse_down:
                    self.brighten(-30)
                else:
                    self.brighten(30)


class CircularButton(Button):
    """
    A button that has a circular base and mouse hover detection.
    """

    def __init__(self, parent, x, y, r,
                 unit: str or tuple = "px",
                 anchor: str = "tl",
                 pivot: str = "tl",
                 **kwargs):
        """
        The parameters for this class are slightly different from the usual widget parameters, where width (w) and
        height (h) are replaced with radius (r) instead.

        The size unit cannot be set to "%", because otherwise, the width and height of the rect would have different
        values (in pixels). If the size unit is set to "%", then "%h" is used instead.
        """

        w, h = 2 * r, 2 * r
        pos_unit, size_unit = unit if type(unit) is tuple else (unit, unit)

        size_unit = size_unit if size_unit != "%" else "%h"

        super().__init__(parent, x, y, w, h, (pos_unit, size_unit), anchor, pivot, **kwargs)

    def draw_base(self):
        """
        Draw a circle instead of a rounded rectangle for the button's base.
        """
        r = int(self.rect.h / 2) - 1
        pygame.gfxdraw.aacircle(self.base.image, r, r, r, self.color)
        pygame.gfxdraw.filled_circle(self.base.image, r, r, r, self.color)

    @property
    def hover(self):
        """
        The circular button class uses a special way to calculate if the mouse is hovering on the button or not.

        r: Radius of button.
            r = Button height / 2
        d_sq: Distance between mouse and button center, squared.
            d^2 = |Mouse pos (vector) - Button's global pos (vector)| ^ 2

        If d < r (or d^2 < r^2), then the cursor is inside the button's circle.
        """
        r = self.rect.h / 2
        d_sq = (Vector2(self.mouse_x, self.mouse_y) - Vector2(self.rect.global_rect.center)).magnitude_squared()
        return d_sq < r ** 2
