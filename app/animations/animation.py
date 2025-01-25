"""
animation.py

The animation module contains the `Animation` base class and the `AnimGroup` class to group and update animations.
"""

from abc import ABC, abstractmethod
from typing import Callable, Type, Any

from app.animations.interpolations import InterpolationFunc, ease_in_out


class Animation(ABC):
    """
    `Animation` is the base class for all animation classes.
    """

    def __init__(self, duration: float,
                 interpolation: InterpolationFunc = ease_in_out,
                 call_on_finish: Callable = lambda: None,
                 anim_group: "AnimGroup" or None = None,
                 auto_start=True):
        """
        Initialize the animation (superclass).

        :param duration: The duration of the animation.
        :param interpolation: The interpolation function that converts `phase` into `interpol_phase`.
        :param call_on_finish: An external function that is called when the function is finished (optional).
        """
        self.duration = duration
        self.phase = 0
        self.running = auto_start

        self.interpolation = interpolation
        self.interpol_phase = 0

        self.call_on_finish = call_on_finish

        self.anim_group = None
        if anim_group:
            anim_group.add(self)

        if duration <= 0:
            self.stop()

    def update(self, dt):
        if not self.running:
            return

        self.phase += dt / self.duration
        self.interpol_phase = self.interpolation(self.phase)

        if self.phase >= 1:
            self.stop(stop_midway=False)
        else:
            self.update_anim()

    """
    Abstract methods
    """

    @abstractmethod
    def update_anim(self) -> None:
        """
        Abstract method: Called on every update.
        """
        pass

    @abstractmethod
    def finish(self) -> None:
        """
        Abstract method: Called once the animation is finished playing.
        """
        pass

    """
    Start, stop, pause methods
    """

    def start(self):
        """
        Start or continue the animation.
        """
        self.running = True

    def pause(self):
        """
        Pause the animation.
        """
        self.running = False

    def stop(self, stop_midway=True):
        """
        Stop the animation. Once it's stopped, the animation cannot be continued anymore.
        """
        if not self.running:
            return

        self.running = False
        self.phase = 1

        self.anim_group.remove(self)
        self.anim_group = None

        if not stop_midway:
            self.finish()
            self.call_on_finish()


class AnimGroup:
    """
    An animation group is used to store multiple animations into one group. The update method of an animation group is
    then called every game tick which updates all the ongoing animations. When an animation is finished playing, it gets
    removed from the animation group.
    """

    def __init__(self):
        self.animations: list[Animation] = []  # Currently running animations

    def add(self, animation: Animation):
        """
        Add an animation to the animation group. Each animation can only be bound to one anim group, so if the animation
        is already in another animation group, then that animation is removed from its previous group.
        """
        if animation.anim_group and animation in animation.anim_group.animations:
            animation.anim_group.remove(animation)

        animation.anim_group = self
        self.animations.append(animation)

    def remove(self, animation: Animation):
        """
        Remove an animation from the group.
        """
        self.animations.remove(animation)
        animation.anim_group = None

    def reset(self, anim_type: Type or None = None):
        """
        Remove all the animations on the animation group. If `anim_type` is specified, then only the animations of the
        specified type/class is removed.
        """
        if anim_type:
            for anim in self.animations:
                if type(anim) is anim_type:
                    self.animations.remove(anim)

        else:
            self.animations = []

    def update(self, dt):
        """
        Run the update method of all the animations of this group.
        """
        for animation in self.animations:
            animation.update(dt)
