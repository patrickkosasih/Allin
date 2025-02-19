"""
app/rules_interface/interface.py

The interface module is used to bridge the communication between the rules engine and the GUI (game scene).
"""

from typing import Callable, Optional

from app.tools.app_timer import TimerGroup
from rules.game_flow import Player, GameEvent, PokerGame


class InterfaceGame(PokerGame):
    def __init__(self):
        super().__init__()

        self.client_player: Player = Player(self, "Placeholder Client Player", 1000)  # Only a placeholder
        self.event_receiver: Callable[[GameEvent], None] = lambda x: None

        self.timer_group = TimerGroup()

    def on_event(self, event):
        self.event_receiver(event)

    def action(self, action_type, new_amount=0):
        return self.client_player.action(action_type, new_amount)

    def update(self, dt):
        self.timer_group.update(dt)
