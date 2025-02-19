"""
widgets.py

A module containing the essential base classes for widgets and its components. Both of them are extensions of the Pygame
sprite class, and they use an AutoRect (an extension of the Pygame Rect class) for their positioning.
"""

import pygame
from abc import ABC

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.scenes.scene import Scene

from app.animations.animation import AnimGroup
from app.animations.fade import FadeAlphaAnimation
from app.animations.move import MoveAnimation
from app.shared import *



class AutoRect(pygame.rect.Rect):
    """
    An extended version of Pygame's Rect class.
    An AutoRect has a settable unit, anchor, pivot, and parent rect that would make it easier to position widgets.
    """

    VALID_UNITS = ["px", "%", "%w", "%h"]

    ALIGNMENT_FACTORS = {           # Aliases
        "topleft": (0, 0),          "tl": (0, 0),
        "midtop": (0.5, 0),         "mt": (0.5, 0),
        "topright": (1, 0),         "tr": (1, 0),
        "midleft": (0, 0.5),        "ml": (0, 0.5),
        "center": (0.5, 0.5),       "ctr": (0.5, 0.5),
        "midright": (1, 0.5),       "mr": (1, 0.5),
        "bottomleft": (0, 1),       "bl": (0, 1),
        "midbottom": (0.5, 1),      "mb": (0.5, 1),
        "bottomright": (1, 1),      "br": (1, 1),
    }

    def __init__(self, x, y, w, h,
                 unit: str or tuple[str, str] = "px",
                 anchor: str = "topleft",
                 pivot: str ="topleft",
                 parent_rect: "AutoRect" = None):
        """
        Parameters:

        :param x: X position
        :param y: Y position
        :param w: Width
        :param h: Height

        :param unit: The unit of x, y, w, and h. Possible units:
                       "px": Pixels (default).
                       "%":  A fraction of the parent widget/display's dimensions in percentage.
                             x and w are based on the parent's width, while y and h are based on the parent's height.
                       "%w": A fraction of the parent's width.
                       "%h": A fraction of the parent's height.

                     Alternatively, a tuple of two strings can also be passed as an argument. If so, then the position
                     (x and y) and size (w and h) arguments would have different units.
                       Format: (<pos unit>, <size unit>).

        :param anchor: The anchor/origin of the rect on the parent rect. Possible anchors: See `ALIGNMENT_FACTORS`.
                         e.g. When the anchor is set to "center", then the position's (0, 0) would be located in the
                         center of the screen / parent rect.

        :param pivot: The pivot of the rect. Possible anchors: See `ALIGNMENT_FACTORS`.
                        e.g. When the pivot is set to "bottomright", then the rect's bottom right corner would be placed
                        in the given x and y positions.

        :param parent_rect: The parent widget/display's rect.
        """

        pos_unit, size_unit = unit if type(unit) is tuple else (unit, unit)

        if pos_unit not in self.VALID_UNITS:
            raise ValueError(f"invalid pos unit: {pos_unit}")
        elif size_unit not in self.VALID_UNITS:
            raise ValueError(f"invalid size unit: {size_unit}")

        if not parent_rect:
            parent_rect = pygame.Rect(0, 0, *pygame.display.get_window_size())

        if size_unit == "%":
            w, h = elementwise_mult(parent_rect.size, (w / 100, h / 100))
        elif size_unit == "%w":
            w, h = Vector2(w, h) / 100 * parent_rect.w
        elif size_unit == "%h":
            w, h = Vector2(w, h) / 100 * parent_rect.h

        super().__init__(0, 0, w, h)

        """
        Extended attributes
        """
        self.parent_rect = parent_rect

        self._unit = unit
        self._pos_unit, self._size_unit = pos_unit, size_unit
        self._anchor = anchor
        self._pivot = pivot

        """
        Initialize position
        """
        self.set_pos(x, y)

    def __repr__(self):
        x, y, w, h = self
        return f"<AutoRect({x}, {y}, {w}, {h}, {self._unit=}, {self._anchor=}, {self._pivot=})>"

    def set_pos(self, x, y, unit=None, anchor=None, pivot=None):
        """
        Set the position of the rect.

        :param x: X position.
        :param y: Y position.
        :param unit: Temporarily override the rect's pos unit. Possible units: "px", "%", "%w", "%h".
        :param anchor: Temporarily override the rect's anchor.
        :param pivot: Temporarily override the rect's pivot.
        """

        unit = unit if unit else self._pos_unit
        anchor = anchor if anchor else self._anchor
        pivot = pivot if pivot else self._pivot

        """
        Set the original Rect position (where the anchor and pivot are in the top right)
        """
        if unit == "px":
            self.x, self.y = x, y
        elif unit == "%":
            self.x, self.y = elementwise_mult(self.parent_rect.size, (x / 100, y / 100))
        elif unit == "%w":
            self.x, self.y = Vector2(x, y) / 100 * self.parent_rect.w
        elif unit == "%h":
            self.x, self.y = Vector2(x, y) / 100 * self.parent_rect.h
        else:
            raise ValueError(f"invalid pos unit: {unit}")

        """
        Validate anchor and pivot 
        """
        if anchor not in AutoRect.ALIGNMENT_FACTORS:
            raise ValueError(f"invalid anchor: {anchor}")
        elif pivot not in AutoRect.ALIGNMENT_FACTORS:
            raise ValueError(f"invalid pivot: {pivot}")

        """
        Align the position according to the anchor and pivot

        Pos = Original pos + (Anchor alignment factors * Parent rect size) - (Pivot alignment factors * Dimensions)
        """
        anchor_offset = Vector2(*elementwise_mult(AutoRect.ALIGNMENT_FACTORS[anchor], self.parent_rect.size))
        pivot_offset = Vector2(*elementwise_mult(AutoRect.ALIGNMENT_FACTORS[pivot], self.size))

        self.x, self.y = Vector2(self.topleft) + anchor_offset - pivot_offset

    def get_pos(self, unit=None, anchor=None, pivot=None) -> Vector2:
        """
        Returns the rect's position with the specified unit relative to the specified anchor and pivot.
        If the unit/anchor/pivot is not specified, then the rect's attribute is used instead.
        """

        unit = unit if unit else self._unit
        anchor = anchor if anchor else self._anchor
        pivot = pivot if pivot else self._pivot

        anchor_offset = Vector2(*elementwise_mult(AutoRect.ALIGNMENT_FACTORS[anchor], self.parent_rect.size))
        pivot_offset = Vector2(*(elementwise_mult(AutoRect.ALIGNMENT_FACTORS[pivot], self.size)))
        pos = Vector2(self.topleft) - anchor_offset + pivot_offset

        if unit == "%":
            pos.x = (pos.x / self.parent_rect.w) * 100
            pos.y = (pos.y / self.parent_rect.h) * 100
        elif unit == "%w":
            pos = pos / self.parent_rect.w * 100
        elif unit == "%h":
            pos = pos / self.parent_rect.h * 100

        return pos

    def set_size(self, w, h):
        prev_pos = self.get_pos("px")

        self.w, self.h = w, h
        self.set_pos(*prev_pos, "px")

    def set_alignment(self, unit=None, anchor=None, pivot=None, update_pos=True):
        prev_pos = self.get_pos("px")

        if unit:    self._unit = unit
        if anchor:  self._anchor = anchor
        if pivot:   self._pivot = pivot

        if update_pos:
            self.set_pos(prev_pos, "px")

    @property
    def global_rect(self):
        if issubclass(type(self.parent_rect), AutoRect):
            return self.move(*self.parent_rect.global_rect.topleft)
        else:
            return self

    @property
    def aspect_ratio(self):
        return self.w / self.h

    @property
    def unit(self):
        return self._unit

    @property
    def anchor(self):
        return self._anchor

    @property
    def pivot(self):
        return self._pivot


class AutoSprite(pygame.sprite.Sprite, ABC):
    """
    The AutoSprite class is the parent class of Widget and WidgetComponent that contains the attributes both of them
    have in common.
    """

    def __init__(self, parent: "Widget" or "Scene", *rect_args):
        """
        Parameters:

        :param rect_args: Non-keyword arguments of the __init__ method of this class are read as arguments for the
                          AutoRect of the widget.

        :param parent: The parent widget of this widget.
        :param groups: A tuple of the sprite groups the new widget is part of.
        """

        super().__init__()

        self._rect = AutoRect(*rect_args, parent_rect=parent.rect if parent else None)
        self._image = pygame.Surface(self._rect.size, pygame.SRCALPHA)  # Protected attribute
        self._layer = Layer.DEFAULT

        self._current_move_anim: Optional[MoveAnimation] = None
        self._current_fade_anim: Optional[FadeAlphaAnimation] = None

        self.parent = parent

    def delete(self, parent_attribute_name=""):
        if parent_attribute_name:
            setattr(self.parent, parent_attribute_name, None)

        for group in self.groups():
            group.remove(self)

    """
    Animations
    """

    def move_anim(self, duration: int or float, end_pos: tuple or Vector2,
                  unit=None, anchor=None, pivot=None, start_pos: tuple or None = None, stop_other_anims=True,
                  **kwargs) -> MoveAnimation or None:

        if stop_other_anims and self._current_move_anim and self._current_move_anim.running:
            self._current_move_anim.stop()

        if duration > 0:
            anim = MoveAnimation(duration, self, start_pos, end_pos, unit, anchor, pivot, **kwargs)
            self.scene.anim_group.add(anim)
            self._current_move_anim = anim
            return anim
        else:
            self.set_pos(*end_pos, unit, anchor, pivot)

    def fade_anim(self, duration: int or float, end_val: int,
                  start_val: int = -1,
                  **kwargs) -> FadeAlphaAnimation or None:
        if self._current_fade_anim and self._current_fade_anim.running:
            self._current_fade_anim.stop()

        if duration > 0:
            anim = FadeAlphaAnimation(duration, self, start_val, end_val, **kwargs)
            self.scene.anim_group.add(anim)
            self._current_fade_anim = anim
            return anim
        else:
            self.image.set_alpha(end_val)
            return None

    """
    Getters and setters
    """

    def set_pos(self, x, y, unit=None, anchor=None, pivot=None):
        self._rect.set_pos(x, y, unit, anchor, pivot)

    def get_pos(self, unit=None, anchor=None, pivot=None):
        return self._rect.get_pos(unit, anchor, pivot)

    def is_root_widget(self) -> bool:
        return not issubclass(type(self.parent), Widget)

    @property
    def scene(self) -> "Scene":
        return self.parent if self.is_root_widget() else self.parent.scene

    @property
    def rect(self) -> AutoRect:
        return self._rect

    @rect.setter
    def rect(self, rect: pygame.Rect or AutoRect):
        self._rect.update(*rect)

    @property
    def image(self) -> pygame.Surface:
        return self._image

    @image.setter
    def image(self, image: pygame.Surface):
        self._image = image
        self._rect.set_size(*image.get_size())

    @property
    def layer(self) -> int:
        return self._layer

    @layer.setter
    def layer(self, layer: int):
        self._layer = layer
        self.parent.all_sprites.change_layer(self, layer)


class Widget(AutoSprite):
    def __init__(self, parent: "Widget" or "Scene", *rect_args):
        super().__init__(parent, *rect_args)

        try:
            if issubclass(type(parent), Widget):
                parent.children_group.add(self)
            else:
                parent.all_sprites.add(self)
        except AttributeError:
            raise TypeError("the parent must either be a scene or a widget")

        self.children_group = pygame.sprite.Group()
        self.component_group = pygame.sprite.Group()

    def draw(self):
        self.image.fill((0, 0, 0, 0))
        self.component_group.draw(self.image)
        self.children_group.draw(self.image)

    def update(self, dt):
        if self.children_group.sprites() or self.component_group.sprites():
            self.children_group.update(dt)
            self.component_group.update(dt)
            self.draw()


class WidgetComponent(AutoSprite):
    def __init__(self, parent: Widget, *rect_args):
        if not issubclass(type(parent), Widget):
            raise TypeError("widget components must have a widget for a parent")

        super().__init__(parent, *rect_args)
        self.parent.component_group.add(self)
