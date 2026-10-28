"""Real deck simulation for Blackjack.

The shoe is built from one or more standard 52-card decks and shuffled once
with Fisher-Yates (random.shuffle). After that the card order is FIXED --
cards are dealt sequentially off the top of the shoe. Nothing about the deck
adapts to the player's or dealer's hand, which is what makes this unrigged.
"""

import random
from dataclasses import dataclass

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["\u2660", "\u2665", "\u2666", "\u2663"]  # spades, hearts, diamonds, clubs
RED_SUITS = {"\u2665", "\u2666"}  # hearts, diamonds

RANK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10, "A": 11,
}


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def value(self) -> int:
        return RANK_VALUES[self.rank]

    @property
    def is_red(self) -> bool:
        return self.suit in RED_SUITS

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


class Deck:
    """A shoe of one or more 52-card decks, Fisher-Yates shuffled."""

    def __init__(self, num_decks: int = 6, cut_card_fraction: float = 0.25):
        self.num_decks = num_decks
        self.cards: list[Card] = []
        self._build()
        self._shuffle()
        # Reshuffle once the shoe is down to cut_card_fraction of its cards.
        self.cut_card = max(10, int(len(self.cards) * cut_card_fraction))

    def _build(self):
        for _ in range(self.num_decks):
            for suit in SUITS:
                for rank in RANKS:
                    self.cards.append(Card(rank, suit))

    def _shuffle(self):
        random.shuffle(self.cards)

    def draw(self) -> Card:
        if len(self.cards) <= self.cut_card:
            self._build()
            self._shuffle()
        return self.cards.pop()

    @property
    def remaining(self) -> int:
        return len(self.cards)
