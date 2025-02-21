"""
A module to generate random nicknames because why the hell not.
"""

import random

NICKNAME_ADJ = ["Professional", "Lucky", "Fearless", "Royal", "Sneaky", "Wild", "Risky", "Slick", "Flashy"]
NICKNAME_NOUN = ["Gambler", "Ace", "Bluffer", "Trickster", "Pokerface", "Shark", "Whale", "Professor"]

def generate_nickname() -> str:
    return random.choice(NICKNAME_ADJ) + random.choice(NICKNAME_NOUN)
