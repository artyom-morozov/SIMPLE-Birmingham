from typing import List, Set

from python.id import id

from .cards.card import Card
from .deck import Deck


class Hand:
    """
    Hand object

    :param deck: Deck object"""

    def __init__(self, cards: List[Card]):
        self.id = id()
        self.cardIds: Set[str] = set()
        self.cards: List[Card] = cards
        self.discard = []

    def spendCard(self, card: Card):
        self.cards = list(
            filter(lambda x: x.id != card.id, self.cards)
        )  # remove that card from hand
        self.discard.append(card)

    def add(self, card: Card):
        self.cards.append(card)

    """
    getTotal
    
    :return: amount of cards in hand
    """

    def getTotal(self) -> int:
        return len(self.cards)

    def __repr__(self):
        return self.cards

    def __str__(self):
        return str(self.cards)
