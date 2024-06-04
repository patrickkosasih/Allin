import pygame
import os

from app import app_settings


class SoundGroup:
    def __init__(self):
        self.sound_cache: dict[str, pygame.mixer.Sound] = {}
        self.volume = 1.0

    def update_volume(self):
        self.volume = app_settings.main.get_value("sfx_volume")

    def play_sound(self, filename, volume_mult=1.0):
        sound = self.sound_cache.setdefault(filename, pygame.mixer.Sound(filename))
        sound.set_volume(self.volume * volume_mult)
        sound.play()


default_group = SoundGroup()

def play_sound(filename, volume_mult=1.0):
    default_group.play_sound(filename, volume_mult)
