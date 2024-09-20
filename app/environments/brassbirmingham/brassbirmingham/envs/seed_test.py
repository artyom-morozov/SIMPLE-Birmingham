from collections import defaultdict
import unittest
from unittest.mock import MagicMock, Mock

import numpy as np
from itertools import combinations_with_replacement

from classes.board import Board
from classes.deck import Deck
from classes.enums import Era
from classes.player import Player
from classes.buildings.enums import MerchantName
from classes.trade_post import Merchant
from consts import *
from render import render
from functools import reduce
import asyncio

# from wrapper import EnvWrapper


class Test(unittest.TestCase):
    def resetGame(self, numPlayers):

        self.board = Board(numPlayers, seed=1)

        self.p1 = Player("Noah", self.board)
        self.p2 = Player("Tyler", self.board)

        self.p1.money = 100
        self.p2.money = 100
        if numPlayers > 2:
            self.p3 = Player("Sam", self.board)
        if numPlayers > 3:
            self.p4 = Player("Mr. Mcdonald", self.board)

        # randomize merchant tile init
        # for i, tradePost in enumerate(self.board.tradePosts):
        #     tradePost.addMerchantTile(self.board.merchantTiles[0])

    def testSeed(self):
        # Test shuffle is the same
        self.resetGame(2)
        firstHalf = [card.name for card in list(self.board.deck.cards)[:5]]

        # print("Before reset: ", list(self.board.deck.cards)[:5])

        self.resetGame(2)
        # print("After reset: ", list(self.board.deck.cards)[:5])

        self.assertEqual(
            firstHalf,
            [card.name for card in list(self.board.deck.cards)[:5]],
            "Should be equal after reset",
        )

    def testShuffle(self):
        self.resetGame(2)  # Test shuffle is the same
        firstHalf = [card.name for card in list(self.board.deck.cards)[:5]]
        print("Before shuffle: ", list(self.board.deck.cards)[:5])

        self.board.shuffle(self.board.deck.cards)

        print("After shuffle: ", list(self.board.deck.cards)[:5])

        self.assertEqual(
            firstHalf,
            [card.name for card in list(self.board.deck.cards)[:5]],
            "Should be equal after shuffle",
        )

    def testNumCards(self):
        self.resetGame(2)

        size = 0

        # 8 Choose 2
        eight_choose_2 = 36

        size += eight_choose_2 * 6

        # Count cards
        for i in range(4):
            eight_choose_2 -= 2
            size += len(list(combinations_with_replacement(range(8 - i), 2)))
        print("Size", size)
        self.assertEqual(len(self.board.deck.cards), 48, "Should be 48 cards")

    # do stuff to board w/o having to close it! - I SAID DO IT!!
    async def call(self, board: Board):
        await asyncio.sleep(2)
        self.board.players[0].money = 999


if __name__ == "__main__":
    unittest.main()
