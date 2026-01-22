"""
A module to generate random nicknames because why the hell not.
"""

import random

NICKNAME_ADJ = ["Professional", "Lucky", "Fearless", "Royal", "Sneaky", "Wild", "Risky", "Slick"]
NICKNAME_NOUN = ["Gambler", "Bluffer", "Trickster", "Pokerface", "Whale"]

def generate_nickname() -> str:
    return random.choice(NICKNAME_ADJ) + random.choice(NICKNAME_NOUN)
