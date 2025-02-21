from typing import Callable

import pygame

from app.shared import FontSave
from app.tools.draw import draw_rounded_rect
from app.widgets.listeners import MouseListener, KeyboardListener
from app.widgets.widget import Widget, WidgetComponent


DEFAULT_BG_COLOR = (50, 50, 50, 169)
DEFAULT_FG_COLOR = (255, 255, 255)


class Textbox(MouseListener, KeyboardListener):
    def __init__(self, parent, *rect_args,
                 text_str="", font: pygame.font.Font = None,
                 char_limit=100, adaptive_char_limit=True, input_validator: Callable[[str], bool] = str.isprintable,
                 text_align="middle", editing_text_align="", label_hybrid=False,
                 call_on_deselect: Callable[[], None] = lambda: None):

        """

        :param parent: The parent widget/scene.
        :param rect_args: The AutoRect arguments for positioning.

        :param text_str: The text.
        :param font: The font object. If set to None then a default font is automatically chosen.

        :param char_limit: The max number of characters in the textbox.
        :param adaptive_char_limit: If set to true then in addition to the number of characters, the textbox also limits
                                    the input based on the width of the text in pixels.
        :param input_validator: A customizable `(str) -> bool` function that determines if a character can be inputted
                                into the textbox or not.

        :param text_align: The alignment of the text: "middle", "left", or "right".
        :param editing_text_align: The alignment of the text when the textbox is being edited. If set to an empty string
                                   then it's the same as `text_align`

        :param label_hybrid: If set to true then the textbox appears as a "label hybrid". A label hybrid is a stylized
                             textbox disguised as regular text, but morphs into a textbox when interacting with the mouse.
        """

        super().__init__(parent, *rect_args)

        """
        Data fields
        """
        self._text_str = text_str
        self._font: pygame.font.Font = font if font else FontSave.get_font(4)
        self._char_limit = char_limit
        self._adaptive_char_limit = adaptive_char_limit
        self._input_validator = input_validator

        self._editing = False
        self._caret_blink = 0.0

        self._text_align = text_align
        self._editing_text_align = editing_text_align if editing_text_align else self._text_align
        self._label_hybrid = label_hybrid
        self._call_on_deselect = call_on_deselect

        self._prev_hover = False
        self._prev_editing = False

        """
        Widget components
        """
        self._base = WidgetComponent(self, 0, 0, 100, 100, "%", "tl", "tl")
        draw_rounded_rect(self._base.image, pygame.Rect(0, 0, *self._base.rect.size), DEFAULT_BG_COLOR)
        if label_hybrid:
            self._base.image.set_alpha(0)

        self._text = WidgetComponent(self, 0, 0, 0, 0, "px", "ctr", "ctr")
        self.redraw_text()

        self._caret = WidgetComponent(self, 0, 0, 2, self._text.rect.h * 0.75, "px", "ctr", "ctr")
        self._caret.image.fill((255, 255, 255, 128))
        self._caret.image.set_alpha(0)

        self._underline = WidgetComponent(self, 0, 0, 0, 2, "px", "ctr", "ctr")

    def redraw_text(self):
        self._text.image = self._font.render(self._text_str, True, DEFAULT_FG_COLOR)
        self.set_pos_from_alignment()

    def set_pos_from_alignment(self, duration=0.0):
        align = self._editing_text_align if self._editing else self._text_align
        margin = 0 if self._label_hybrid and not self._editing else 50

        match align:
            case "middle":
                self._text.move_anim(duration, (0, 0), "%h", "ctr", "ctr", stop_other_anims=False)
            case "left":
                self._text.move_anim(duration, (margin, 0), "%h", "ml", "ml", stop_other_anims=False)
            case "right":
                self._text.move_anim(duration, (-margin, 0), "%h", "mr", "mr", stop_other_anims=False)

    def on_click(self, event):
        self._editing = True

    def on_mouse_down(self, event):
        super().on_mouse_down(event)

        if not self.hover:
            self._editing = False
            self._call_on_deselect()

    def key_down(self, event):
        if not self._editing:
            return

        c = event.unicode
        textbox_not_full = (len(self._text_str) <= self._char_limit and
                            (self._adaptive_char_limit and self.rect.w - self._text.rect.w >= self.rect.h))


        if event.key == pygame.K_BACKSPACE:
            if pygame.key.get_mods() & pygame.KMOD_CTRL:
                self._text_str = ""
            else:
                self._text_str = self._text_str[:-1]

        elif event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self._editing = False
            self._call_on_deselect()

        elif textbox_not_full and self._input_validator(c):
            self._text_str += c

        self.redraw_text()

    def update(self, dt):
        super().update(dt)

        """
        Update appearance based on mouse hover and editing mode.
        """
        if self._label_hybrid:
            # Show/hide the underline
            if self.hover and not self._editing:
                if self._underline.rect.w != self._text.rect.w:
                    # Update the underline's size and position
                    self._underline.rect.w = self._text.rect.w
                    self._underline.image = pygame.Surface(self._underline.rect.size, pygame.SRCALPHA)
                    self._underline.image.fill(DEFAULT_FG_COLOR)

                self._underline.set_pos(self._text.rect.centerx, self._text.rect.top + self._font.get_ascent() + 2,
                                       "px", "tl", "mt")
                self._underline.image.set_alpha(255)
            else:
                self._underline.image.set_alpha(0)

            # Show/hide the textbox base
            if self._prev_editing != self._editing:
                self._base.fade_anim(0.25, 255 if self._editing else 0)

        else:
            # Brighten the textbox
            if self.hover or self._editing:
                self.image.fill((20, 20, 20), special_flags=pygame.BLEND_ADD)

        """
        Caret blinking stuff
        """
        if self._editing:
            self._caret_blink += dt
            self._caret_blink %= 1

            self._caret.rect.x = self._text.rect.right + 1
            self._caret.image.set_alpha(255 if self._caret_blink < 0.5 else 0)

        elif self._prev_editing and not self._editing:
            self._caret.image.set_alpha(0)

        """
        Switching alignment between editing and not editing
        """
        if self._prev_editing != self._editing and self._editing_text_align != self._text_align:
            self.set_pos_from_alignment(0.25)

        """
        Update the "prev" attributes
        """
        self._prev_hover = self.hover
        self._prev_editing = self._editing

    @property
    def text_str(self):
        return self._text_str

    @text_str.setter
    def text_str(self, text_str: str):
        self._text_str = text_str
        self.redraw_text()
