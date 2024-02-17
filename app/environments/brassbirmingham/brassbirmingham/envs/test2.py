from collections import defaultdict
import unittest
from unittest.mock import MagicMock, Mock

from classes.board import Board
from classes.deck import Deck
from classes.enums import Era
from classes.player import Player
from classes.buildings.enums import MerchantName
from consts import *
from render import render
from functools import reduce
import random
import asyncio



class Test(unittest.TestCase):
    def resetGame(self, numPlayers):
        self.board = Board(numPlayers)

        self.p1 = Player("Noah", self.board)
        self.p2 = Player("Tyler", self.board)

        if numPlayers > 2:
            self.p3 = Player("Sam", self.board)
        if numPlayers > 3:
            self.p4 = Player("Mr. Mcdonald", self.board)

        # randomize merchant tile init
        for i, tradePost in enumerate(self.board.tradePosts):
            tradePost.addMerchantTile(self.board.merchantTiles[0])

        
    def testAllNetworks(self):
        self.resetGame(2)


        # TEST Canals
        availableRoads = self.p1.getAvailableNetworks()

        # for road in availableRoads.symmetric_difference(set(self.board.roadLocations)):
        #     print(road)


        # print('Len Roads', len(availableRoads))
        # print('Len In Board', len(self.board.roadLocations))
        self.assertTrue(
            len(availableRoads) == len(self.board.roadLocations) - 8,
            f"Should have all - 8 canal roads available",
        )

        # TEST Railroads
        self.board.era = Era.railroad

        availableRoads = self.p1.getAvailableNetworks()

        
        self.assertTrue(
            len(availableRoads) == len(self.board.roadLocations) - 1,
            f"Should have (all - 1 ) railroads available",
        )

        # Test After Building Networks
        self.board.era = Era.canal
        birm = self.board.townDict['Birmingham']
        b_to_ox = birm.networks[4]
        self.p2.buildCanal(b_to_ox)
        availableRoadsP1 = self.p1.getAvailableNetworks()
        availableRoadsP2 = self.p2.getAvailableNetworks()


        self.assertNotIn(b_to_ox, availableRoadsP1)
        self.assertNotIn(b_to_ox, availableRoadsP2)
        # render(self.board)

        self.assertFalse(
            self.p1.canBuildCanal(b_to_ox),
            "Player 1 Should NOT be able to build this canal",
        )

        self.assertFalse(
            self.p2.canBuildCanal(b_to_ox),
            "Player 2 Should NOT be able to build this canal",
        )


        # Test affter building

        self.p1CottonBuilding = self.p1.buildings[10]
        self.p1.buildBuilding(self.p1CottonBuilding, birm.buildLocations[0])
        availableRoadsP1 = self.p1.getAvailableNetworks()



        # for i, road in enumerate(self.board.townDict['Cannock'].networks):
        #     print(i, road)
        # render(self.board, self.call)
        self.assertTrue(
            len(availableRoadsP1) == 5,
            f"Player 1 Should have 4 railroads from birmingham after building",
        )

        b_to_w = birm.networks[0]
        # wallsall = self.board.townDict['Walsall']
        self.p1.buildCanal(b_to_w)
        # for i, road in enumerate(self.p1.getAvailableNetworks().difference(availableRoadsP1)):
        #     print(i, road)
        
        self.assertEqual(len(self.p1.getAvailableNetworks().difference(availableRoadsP1)), 3, 'Adding Walsall-Birm network should add just 3 additional roads')


        self.resetGame(2)
    
    
    # EXPEERIMENTS
    
        # countBuilds = 0
        # for t in TOWNS:
        #     for bl in t.buildLocations:
        #         countBuilds +=  len(bl.possibleBuilds)

        # print('Possible Builds', countBuilds)
        # print('Possible industry builds for player ', )
        # print('RoadLocations', len(ROAD_LOCATIONS))
        # print('IndustryTiles', len(BUILDINGS))
        # print('Towns', len(TOWNS))
        
        # name = {}    
        # totalVp = 0
        # maxVp = 0
        # uniqueVPS = set()
        # uniqueCosts = set()


        # for b in BUILDINGS:
        #     if not b.name in name:
        #         name[b.name] = {}
        #     if not b.tier in name[b.name]:
        #         name[b.name][b.tier] = 0
        #     name[b.name][b.tier] += 1
        #     totalVp += b.victoryPointsGained
        #     maxVp = max(maxVp, b.victoryPointsGained)
        #     uniqueVPS.add(b.victoryPointsGained)
        #     uniqueCosts.add(b.cost)

        # for n in name.keys():
        #     print(f'{n}:')
        #     for tier in name[n].keys():
        #         print(f'Level {tier} - {name[n][tier]} builldings')       
        #     print()
        
        
        # roads_canal = [rl for rl in  self.board.roadLocations if rl.canBuildCanal]
        # roads_railroad = [rl for rl in  self.board.roadLocations if rl.canBuildRailroad]

        # print('Canal roads', len(roads_canal))
        # print('Railroads', len(roads_railroad))

        # def biggestPointsFromCanalLink(rl: RoadLocation):
        #     maxPoints = 0
        #     for t in rl.towns:
        #         if isinstance(t, TradePost):
        #             maxPoints += 2
        #             continue
        #         maxPointsTown = 0
        #         for bl in t.buildLocations:
        #             if BuildingName.cotton in  bl.possibleBuilds or BuildingName.coal in bl.possibleBuilds or BuildingName.beer in bl.possibleBuilds or BuildingName.goods in bl.possibleBuilds:
        #                 maxPointsTown += 2
        #             else:
        #                 maxPointsTown += 1
        #         maxPoints += maxPointsTown
        #     return maxPoints
        
        # def biggestPointsFromRailLink(rl: RoadLocation):
        #     maxPoints = 0

        #     for t in rl.towns:
        #         if isinstance(t, TradePost):
        #             maxPoints += 2
        #             continue
        #         maxPointsTown = 0
        #         for bl in t.buildLocations:
        #             if BuildingName.cotton in  bl.possibleBuilds or BuildingName.beer in bl.possibleBuilds or BuildingName.goods in bl.possibleBuilds:
        #                 maxPointsTown += 2
        #             else:
        #                 maxPointsTown += 1
        #         maxPoints += maxPointsTown
        #     return maxPoints


        # best_canals = sorted(roads_canal, key=lambda x: biggestPointsFromCanalLink(x), reverse=True)[:14]
        # best_roads = sorted(roads_railroad, key=lambda x: biggestPointsFromRailLink(x), reverse=True)[:14]
        # print('Best Canals:')
        # for canal in best_canals[:3]:
        #     print(canal)
        # print()
        
        # print('Best Railroads:')
        # for road in best_roads[:3]:
        #     print(road)
        # print()
        
        
        
        # totalCanalScore = 0
        # totalRoadScore = 0
        
        # for canal in best_canals:
        #     totalCanalScore += biggestPointsFromCanalLink(canal)
        
        # for road in best_roads:
        #     totalRoadScore += biggestPointsFromRailLink(road)
        
        
        # print('Total victory points that can be gained is', totalVp+3+4+totalCanalScore+totalRoadScore)
        # print('Max victory point per building is ', maxVp)
        # print('Unique victory points are ', uniqueVPS, len(uniqueVPS))
        # print('Unique building costs  are ', uniqueCosts, len(uniqueCosts))


    def testAvailableCardBuilds(self):
                
        self.resetGame(2)


        self.p1.hand.cards = [IndustryCard(name=CardName.brewery)]
        # availableBls = set([bl for b, bl in self.p1.getAvailableBuilds()])
        # industriesOnBoard = set()
        # for t in self.board.towns:
        #     if isinstance(t, Town):
        #         for bl in t.buildLocations:
        #             for card in self.p1.hand.cards:
        #                 if isinstance(card, IndustryCard):
        #                     for bname in card.getBuildNames():
        #                         if bname in bl.possibleBuilds:
        #                             industriesOnBoard.add(bl)
        # # print("buildibngs before network")
        # # for b, bl in self.p1.getAvailableBuilds():
        # #     print(b.name, ' in ',bl.town.name)
        # self.assertEqual(len(availableBls.difference(industriesOnBoard)), 0, 'Builds available from industry cards should be equal to all build locations')



        coalbrookdale: Town = self.board.townDict[COALBROOKDALE]


        p2brewery = self.p2.industryMat[BuildingName.beer][-1]
        p1brewery = self.p1.industryMat[BuildingName.beer][-1]
        
        shrew_to_coal = coalbrookdale.networks[1]
        
        
        # # Test Builds After Network
        self.p1.buildCanal(shrew_to_coal)
        # # render(self.board)
        
        coalbrookdaleBeerSlot = coalbrookdale.buildLocations[0]


        availableBuilds = self.p1.getAvailableBuilds()
        # for b, bl in availableBuilds:
        #     print(b.name, ' in ',bl.town.name)
        

        self.assertEqual(availableBuilds, set([(p1brewery, coalbrookdaleBeerSlot)]), 'Should only have one build available after network')


        # TEst After other player building
        
        self.p2.buildBuilding(p2brewery, coalbrookdaleBeerSlot)


        self.assertEqual(len(self.p1.getAvailableBuilds()), 0 , 'Shoould be no builds after occupiing')
        
        self.p2.hand.cards = [LocationCard(name=COALBROOKDALE)]
        self.assertEqual(len(self.p2.getAvailableBuilds()), 0 , 'Shoould be no builds after occupiing')

        # self.board.era = Era.railroad
        self.p1.hand.cards = [LocationCard(name=COALBROOKDALE)]

       

        self.assertEqual(self.p1.getAvailableBuilds(), set([(self.p1.industryMat[BuildingName.iron][-1], coalbrookdale.buildLocations[1]), (self.p1.industryMat[BuildingName.coal][-1], coalbrookdale.buildLocations[2])]) , 'Shoould be no builds after occupiing')

        
        self.p2.develop(self.p2.industryMat[BuildingName.beer][-1], self.p2.industryMat[BuildingName.beer][-2])

        # print('Last beer',  self.p2.industryMat[BuildingName.beer][-1])
        # print('Available Builds after development:')
        # for b, bl in self.p2.getAvailableBuilds():
        #     print(b.name, ' in ',bl.town.name)


        self.assertEqual(len(self.p2.getAvailableBuilds()), 1, 'Shoould have overbuilding availablee after deveelopment')


        # render(self.board)


    def testIndustryMat(self):
        self.resetGame(2)


        # self.p1.hand = [LocationCard()]


        # Test Industry Card Builds


        # print('Cards:')
        # print(self.p1.hand)
        # print()
        # builds = self.p1.getAvailableBuilds()
        # print(f'Can build {len(builds)}:')
        # for b, bl in builds:
        #     print(f"{b.name} level {b.tier} in {bl.town.name}")
        
        

    # do stuff to board w/o having to close it! - I SAID DO IT!!
    async def call(self, board: Board):
        await asyncio.sleep(2)
        self.board.players[0].money = 999

if __name__ == "__main__":
    unittest.main()
