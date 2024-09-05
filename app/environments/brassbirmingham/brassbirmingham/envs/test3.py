from collections import defaultdict
import unittest
from unittest.mock import MagicMock, Mock

import numpy as np

from classes.board import Board
from classes.deck import Deck
from classes.enums import Era
from classes.player import Player
from classes.buildings.enums import MerchantName
from classes.trade_post import Merchant
from consts import *
from render import render
from functools import reduce
import random
import asyncio
import copy


def get_valid_actions(env, player_id):
    return env.get_valid_actions(player_id)


def draw_new_cards(env, player_id, round_num):
    env.draw_new_cards(player_id, round_num)


# from wrapper import EnvWrapper
def generate_action_tree(env, player_id, round_num, max_rounds):
    if round_num > max_rounds:
        return "End of game"

    tree = {}

    # Get valid actions for the current player
    valid_actions = get_valid_actions(env, player_id)

    for action1 in valid_actions:
        env_copy1 = copy.deepcopy(env)
        obs1, reward1, done1, info1 = env_copy1.step(action1)

        # After first action, get new valid actions
        valid_actions2 = get_valid_actions(env_copy1, player_id)

        for action2 in valid_actions2:
            env_copy2 = copy.deepcopy(env_copy1)
            obs2, reward2, done2, info2 = env_copy2.step(action2)

            # Draw new cards (this would be deterministic based on the round)
            draw_new_cards(env_copy2, player_id, round_num)

            tree[f"Round {round_num}, Action 1: {action1}, Action 2: {action2}"] = {
                "reward": reward1 + reward2,
                "done": done2,
                "next_states": generate_action_tree(
                    env_copy2, 3 - player_id, round_num + 1, max_rounds
                ),
            }

    return tree


class Test(unittest.TestCase):
    def resetGame(self, numPlayers):
        self.board = Board(numPlayers, test=True)

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

    def testVectors(self):
        from wrapper import EnvWrapper

        env = EnvWrapper(interactive=False, debug_mode=True)

        env.reset()

        # Generate action tree for 1 player 1 round

        # count_bl = 0
        # for t in self.board.towns:
        #     if isinstance(t, Town):
        #         count_bl += len(t.buildLocations)
        # print("Just bls", count_bl)

        # print("Goods", BuildingName.goods)
        # print("First goods tier", self.p1.industryMat[BuildingName.goods][-1].tier)

        # print("Create VP for building map")

        # money = set()
        # coalCost = set()
        # ironCost = set()
        # beerCost = set()
        # resoruces = set()
        # incomeGained = set()
        # networkPoints = set()

        # for b in BUILDINGS:
        #     money.add(b.cost)
        #     coalCost.add(b.coalCost)
        #     ironCost.add(b.ironCost)
        #     incomeGained.add(b.incomeGained)
        #     if isinstance(b, MarketBuilding):
        #         beerCost.add(b.beerCost)
        #     elif isinstance(b, IndustryBuilding):
        #         resoruces.add(b.resourceAmount)
        #     networkPoints.add(b.networkPoints)

        # print(f"Unique money ({len(money)})", list(money))
        # print(f"Unique coalCost ({len(coalCost)})", list(coalCost))
        # print(f"Unique ironCost ({len(ironCost)})", list(ironCost))
        # print(f"Unique beerCost ({len(beerCost)})", list(beerCost))
        # print(f"Unique incomeGained ({len(incomeGained)})", list(incomeGained))
        # print(f"Unique resoruces ({len(resoruces)})", list(resoruces))
        # print(f"Unique networkPoints ({len(networkPoints)})", list(networkPoints))
        # all_bls = []
        # for t in self.board.towns:
        #     if isinstance(t, Town):
        #         for bl in t.buildLocations:
        #             for possibleBuild in bl.possibleBuilds:
        #                 all_bls.append((bl, possibleBuild))

        # print("All Build Locations ", len(all_bls))

        # print("First build Location", all_bls[0])

        # all_coal = [
        #     (bl, possibleBuild)
        #     for bl, possibleBuild in all_bls
        #     if possibleBuild == BuildingName.coal
        # ]

        # print("All Coal Sources", len(all_coal) + 1)

        # all_iron = [
        #     (bl, possibleBuild)
        #     for bl, possibleBuild in all_bls
        #     if possibleBuild == BuildingName.iron
        # ]

        # print("All Iron Sources", len(all_iron) + 1)

        # env = EnvWrapper()

        # self.assertEqual(
        #     len(env._get_road_features()),
        #     39,
        #     "Should have no vector size for no players",
        # )

        # self.p1.hand = [LocationCard()]

        # Test Industry Card Builds

        # print('Cards:')
        # print(self.p1.hand)
        # print()
        # builds = self.p1.getAvailableBuilds()[0]
        # print(f'Can build {len(builds)}:')
        # for b, bl in builds:
        #     print(f"{b.name} level {b.tier} in {bl.town.name}")

    # do stuff to board w/o having to close it! - I SAID DO IT!!
    async def call(self, board: Board):
        await asyncio.sleep(2)
        self.board.players[0].money = 999


if __name__ == "__main__":
    unittest.main()
