from collections import deque
from typing import List
from python.id import id

from .cards.card import Card


class Deck:
    """
    Deck object

    :param cards: array of Card objects
    """

    def __init__(self, cards: List[Card], np_shuffle):
        self.id = id()
        self.shuffle = np_shuffle
        self.shuffle(cards)
        self.cards = deque(cards)
        self.discardPile = []

    def __len__(self):
        return len(self.cards)

    def draw(self, num=1) -> List[Card]:
        output = []
        discarded = 0
        while len(self.cards) > 0 and discarded < num:
            output.append(self.cards.pop())
            discarded += 1
        return output

    def discard(self, num=1):
        discarded = 0
        while len(self.cards) > 0 and discarded < num:
            self.discardPile.append(self.cards.pop())
            discarded += 1

    def reset(self):
        self.shuffle(self.discardPile)
        self.cards = deque(self.discardPile)
        self.discardPile = []

    def __str__(self) -> str:
        return str(self.cards)
