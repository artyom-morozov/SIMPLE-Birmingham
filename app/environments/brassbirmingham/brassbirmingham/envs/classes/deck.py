from collections import deque
import random
from typing import List

from python.id import id

from .cards.card import Card


class Deck:
    """
    Deck object

    :param cards: array of Card objects
    """

    def __init__(self, cards: List[Card]):
        self.id = id()
        self.cards = deque(cards)
        self.discardPile = []
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

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
        self.cards = self.discardPile
        self.discardPile = []
        self.shuffle()

    def __str__(self) -> str:
        return str(self.cards)
