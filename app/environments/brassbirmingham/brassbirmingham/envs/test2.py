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

    def testSelling(self):
        self.resetGame(2)

        print('Player 1', self.p1, ' color - ', self.p1.color)
        print('Player 2', self.p2, ' color - ', self.p2.color)

        birmCard1 = LocationCard(name=BIRMINGHAM)
        birmCard2 = LocationCard(name=WALSALL)


        garb1 = LocationCard(name=WOLVERHAMPTON)
        garb2 = LocationCard(name=WOLVERHAMPTON)

        self.p1.hand.cards = [birmCard1, garb1]
        self.p2.hand.cards = [birmCard2, garb2]

        birm = self.board.townDict['Birmingham']
        b_to_ox = birm.networks[4]
        birm_cotton_bl = birm.buildLocations[0]
        ox: TradePost = self.board.tradePostDict[OXFORD]


        p1_cotton = self.p1.industryMat[BuildingName.cotton][-1]
        self.p1.buildBuilding(BuildingName.cotton, birm_cotton_bl, birmCard1)
        merchants, beers, beerAvailable = self.p1.getAvailableBeerSources(p1_cotton)

        # render(self.board)


        self.assertEqual(merchants, set(), 'Should have 0 tradpostS')
        self.assertEqual(beers, set(), 'Should have NO possible beer sources from merchants')
        self.assertEqual(beerAvailable, 0, 'Should only have ZEERO beer source available overall')


        # Build road to Oxword
        self.p2.buildCanal(b_to_ox, garb2)





        merchants, beers, beerAvailable = self.p1.getAvailableBeerSources(p1_cotton)

        # render(self.board)


        self.assertEqual(merchants, set(ox.merchantTiles), 'Should have one tradpost')
        self.assertEqual(beers, set(ox.merchantTiles), 'Should have two possible beer sources from merchants')
        self.assertEqual(beerAvailable, 1, 'Should only have one beer source available overall')
        # Enumerate birmingham build locations
        # Get buildlocation id
        # print('Birmingham builds')
        # for i, bl in enumerate(birm.buildLocations):
        #     print(i, ' can build', bl.possibleBuilds)


        # Build beer and road in walsall andd test 
        walsall: Town = self.board.townDict[WALSALL]
        b_to_w = walsall.networks[0]

        self.p2.money = 30
        p2_beer = self.p2.industryMat[BuildingName.beer][-1]
        self.p2.buildBuilding(BuildingName.beer, walsall.buildLocations[1], birmCard2)

        merchants, beers, beerAvailable = self.p1.getAvailableBeerSources(p1_cotton)

        self.assertEqual(merchants, set(ox.merchantTiles), 'Should only have  traedpost beer available after oponents beer')
        self.assertEqual(beers, set(ox.merchantTiles), 'Should only have two beer sources  after oponents beer')
        self.assertEqual(beerAvailable, 1, 'Should only have one beer source available overall after oponents beer')


        # Test after road to Oponenets beer

        self.p2.hand.cards = [LocationCard(WOLVERHAMPTON), LocationCard(WOLVERHAMPTON)]
        self.p2.buildCanal(birm.networks[0], self.p2.hand.cards[0])
        
        merchants, beers, beerAvailable = self.p1.getAvailableBeerSources(p1_cotton)



        self.assertEqual(merchants, set(ox.merchantTiles), 'Should  have tradpost beer after oponents beer')
        self.assertEqual(beers, set(ox.merchantTiles + [walsall.buildLocations[1].building]), 'Should  have 2 beer source after oponents beer (connected)')
        self.assertEqual(beerAvailable, 2, 'Should  have 2 beer source available overall after oponents beer (connected)')


        # Test after building own beer 
        self.p1.money = 30
        self.p1.hand.cards = [LocationCard(UTTOXETER)]
        utx: Town = self.board.townDict[UTTOXETER]
        self.p1.buildBuilding(BuildingName.beer, utx.buildLocations[0], self.p1.hand.cards[0])

        meerchants, beers, beerAvailable = self.p1.getAvailableBeerSources(p1_cotton)

        
        self.assertEqual(meerchants, set(ox.merchantTiles), 'Should  have one tradpost after oponents beer')
        self.assertEqual(beers, set(ox.merchantTiles + [walsall.buildLocations[1].building, utx.buildLocations[0].building]), 'Should  have own beer source  after own beer')
        self.assertEqual(beerAvailable, 3, 'Should  have 3 beer source available overall after own beer')



        # render(self.board)





        


        # Build cotton one in birm

    

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


        # SetupCards for building
        CoalbrookCard = LocationCard(name=COALBROOKDALE)
        WalsallCard = LocationCard(name=WALSALL)

        self.p2.hand.cards = [CoalbrookCard]
        self.p2.buildCanal(b_to_ox, CoalbrookCard)
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



        birmCard = LocationCard(name=BIRMINGHAM)
        self.p1.hand.cards.append(birmCard)

        self.p1.buildBuilding(BuildingName.cotton, birm.buildLocations[0], card=birmCard)
        availableRoadsP1 = self.p1.getAvailableNetworks()



        # for i, road in enumerate(self.board.townDict['Cannock'].networks):
        #     print(i, road)
        # render(self.board, self.call)
        self.assertTrue(
            len(availableRoadsP1) == 5,
            f"Player 1 Should have 5 railroads from birmingham after building",
        )

        b_to_w = birm.networks[0]
        # wallsall = self.board.townDict['Walsall']

        self.p1.hand.cards = [WalsallCard]
        self.p1.buildCanal(b_to_w, WalsallCard)
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


    def testAvailableIndustryCardBuilds(self):
        self.resetGame(2)

        ironCard = IndustryCard(name=CardName.iron_works)
        self.p1.hand.cards = [ironCard]

        builds, firstBuildings, buildLocations = self.p1.getAvailableBuilds()
        print('Failing test')
        for b, bl in builds:
            print(b.name, ' in ',bl.town.name)
            print(f'BID({b.id}) BL_ID({bl.id})')
        self.assertEqual(builds, set(), "Should not have iron as potential build")

                
        self.resetGame(2)

        beerCard1 = IndustryCard(name=CardName.brewery)
        beerCard2 = IndustryCard(name=CardName.brewery)
        self.p1.hand.cards = [beerCard1]
        self.p2.hand.cards = [beerCard2]
        # availableBls = set([bl for b, bl in self.p1.getAvailableBuilds()[0]])
        # industriesOnBoard = set()
        # for t in self.board.towns:
        #     if isinstance(t, Town):
        #         for bl in t.buildLocations:
        #             for card in self.p1.hand.cards:
        #                 if isinstance(card, LocationCard):
        #                     for bname in card.getBuildNames():
        #                         if bname in bl.possibleBuilds:
        #                             industriesOnBoard.add(bl)
        # # print("buildibngs before network")
        # # for b, bl in self.p1.getAvailableBuilds()[0]:
        # #     print(b.name, ' in ',bl.town.name)
        # self.assertEqual(len(availableBls.difference(industriesOnBoard)), 0, 'Builds available from industry cards should be equal to all build locations')



        coalbrookdale: Town = self.board.townDict[COALBROOKDALE]


        p2brewery = self.p2.industryMat[BuildingName.beer][-1]
        p1brewery = self.p1.industryMat[BuildingName.beer][-1]
        
        shrew_to_coal = coalbrookdale.networks[1]
        
        
        # # Test Builds After Network
        
        garbageCard1 = LocationCard(CANNOCK)
        self.p1.hand.cards.append(garbageCard1)


        # print('CARDS BEFORE CANAL', self.p1.hand.cards)

        self.p1.buildCanal(shrew_to_coal, discard=garbageCard1)
        # print('CARDS AFTER CANAL', self.p1.hand.cards)

        # # render(self.board)
        
        coalbrookdaleBeerSlot = coalbrookdale.buildLocations[0]


        availableBuilds = self.p1.getAvailableBuilds()[0]
        # print('Failing test')
        # for b, bl in availableBuilds:

        #     print(b.name, ' in ',bl.town.name)
        #     print(f'BID({b.id}) BL_ID({bl.id})')

        self.assertEqual(availableBuilds, set([(p1brewery, coalbrookdaleBeerSlot)]), 'Should only have one build available after network')


        # TEst After other player building
        
        self.p2.buildBuilding(BuildingName.beer, coalbrookdaleBeerSlot, card=beerCard2)


        self.assertEqual(len(self.p1.getAvailableBuilds()[0]), 0 , 'Shoould be no builds after occupiing')
        
        self.p2.hand.cards = [LocationCard(name=COALBROOKDALE)]
        self.assertEqual(len(self.p2.getAvailableBuilds()[0]), 0 , 'Shoould be no builds after occupiing')

        # self.board.era = Era.railroad
        self.p1.hand.cards = [LocationCard(name=COALBROOKDALE)]

       

        self.assertEqual(self.p1.getAvailableBuilds()[0], set([(self.p1.industryMat[BuildingName.iron][-1], coalbrookdale.buildLocations[1]), (self.p1.industryMat[BuildingName.coal][-1], coalbrookdale.buildLocations[2])]) , 'Shoould be no builds after occupiing')



        # Add card for developing and develop
        garbageCard2 = LocationCard(CANNOCK)
        self.p2.hand.cards.append(garbageCard2) 
        # print('Cards in hand', self.p2.hand.cards)

        self.p2.develop(self.p2.industryMat[BuildingName.beer][-1], self.p2.industryMat[BuildingName.beer][-2], discard=garbageCard2)

        # print('Last beer',  self.p2.industryMat[BuildingName.beer][-1])
        # print('Available Builds after development:')
        # for b, bl in self.p2.getAvailableBuilds()[0]:
        #     print(b.name, ' in ',bl.town.name)


        self.assertEqual(len(self.p2.getAvailableBuilds()[0]), 1, 'Shoould have overbuilding availablee after deveelopment')


        # render(self.board)
    def testCards(self):
        self.resetGame(2)

        dale1, dale2 = LocationCard(name=COALBROOKDALE), LocationCard(name=COALBROOKDALE)


        self.p1.hand.cards = [dale1, dale2]
        
        coalbrookdale: Town = self.board.townDict[COALBROOKDALE]
        
        # Get buildlocation id
        # print('Coalbrookdale builds')
        # for i, bl in enumerate(coalbrookdale.buildLocations):
        #     print(i, ' can build', bl.possibleBuilds)

        self.p1.buildBuilding(industryName=BuildingName.coal, buildLocation=coalbrookdale.buildLocations[2], card=dale1)
        
        availableBuilds = self.p1.getAvailableBuilds()[0]

        self.assertEqual(set([(self.p1.industryMat[BuildingName.coal][-1], coalbrookdale.buildLocations[2])]), availableBuilds, 'Should just have 1 build after spending location card')
        self.assertEqual(self.p1.hand.cards, [dale2], 'Should spend the card used')

        # print('Builds after building coal')
        # for b, bl in availableBuilds:

        #     print(b.name, f'({b.tier}) in ',bl.town.name)
        #     print(f'BID({b.id}) BL_ID({bl.id})')






    def testAvailableLocationCardBuilds(self):
                
        self.resetGame(2)


         # Test Wild Card
        
        self.p1.hand.cards = [LocationCard(name=CardName.wild_location, isWild=True)]
        # print('Printing available builds for Player 1 With WILD Location Card')
        # for b, bl in self.p1.getAvailableBuilds()[0]:
        #     print(b.name, f'({b.tier})  in ',bl.town.name)
        
        allAvailableTowns = set([bl.town for _, bl in self.p1.getAvailableBuilds()[0]])
        allGameTowns = set(self.board.towns)
        

        print('Towns UNAvailable for building after Wild Location Card', allGameTowns.difference(allAvailableTowns))




        self.p1.hand.cards = [LocationCard(name=COALBROOKDALE)]
        self.p2.hand.cards = [LocationCard(name=COALBROOKDALE)]
        # availableBls = set([bl for b, bl in self.p1.getAvailableBuilds()[0]])
        # industriesOnBoard = set()
        # for t in self.board.towns:
        #     if isinstance(t, Town):
        #         for bl in t.buildLocations:
        #             for card in self.p1.hand.cards:
        #                 if isinstance(card, LocationCard):
        #                     for bname in card.getBuildNames():
        #                         if bname in bl.possibleBuilds:
        #                             industriesOnBoard.add(bl)
        # # print("buildibngs before network")
        # # for b, bl in self.p1.getAvailableBuilds()[0]:
        # #     print(b.name, ' in ',bl.town.name)
        # self.assertEqual(len(availableBls.difference(industriesOnBoard)), 0, 'Builds available from industry cards should be equal to all build locations')



        coalbrookdale: Town = self.board.townDict[COALBROOKDALE]


        p2brewery = self.p2.industryMat[BuildingName.beer][-1]
        p1coal = self.p1.industryMat[BuildingName.beer][-1]
        
        shrew_to_coal = coalbrookdale.networks[1]
        
        
        # Test Builds After Building 
        
        coalbrookdaleBeerSlot = coalbrookdale.buildLocations[0]
        
        
        self.p2.buildBuilding(industryName=BuildingName.coal, buildLocation=coalbrookdale.buildLocations[2], card=self.p2.hand.cards[0])
        


        availableBuilds = self.p1.getAvailableBuilds()[0]
        self.assertNotIn((p1coal, coalbrookdale.buildLocations[2]), availableBuilds, 'Should not have occupied location')
        
        self.assertEqual(self.p2.getAvailableBuilds()[0], set(), "Should be empty if no cards")


       
        # print('Printing UNavailablee builds for Player 1 andd their reasons')
        # firstBuildings = 


        # self.assertEqual(allAvailableTowns, allGameTowns)
        # print('Printing available builds for Player 2')
        


        # for b, bl in self.p2.getAvailableBuilds()[0]:
        #     print(b.name, f'({b.tier})  in ',bl.town.name)
        

        # self.assertEqual(availableBuilds, set([(p1brewery, coalbrookdaleBeerSlot)]), 'Should only have one build available after network')


        # # TEst After other player building
        
        # self.p2.buildBuilding(p2brewery, coalbrookdaleBeerSlot)


        # self.assertEqual(len(self.p1.getAvailableBuilds()[0]), 0 , 'Shoould be no builds after occupiing')
        
        # self.p2.hand.cards = [LocationCard(name=COALBROOKDALE)]
        # self.assertEqual(len(self.p2.getAvailableBuilds()[0]), 0 , 'Shoould be no builds after occupiing')

        # # self.board.era = Era.railroad
        # self.p1.hand.cards = [LocationCard(name=COALBROOKDALE)]

       

        # self.assertEqual(self.p1.getAvailableBuilds()[0], set([(self.p1.industryMat[BuildingName.iron][-1], coalbrookdale.buildLocations[1]), (self.p1.industryMat[BuildingName.coal][-1], coalbrookdale.buildLocations[2])]) , 'Shoould be no builds after occupiing')

        
        # self.p2.develop(self.p2.industryMat[BuildingName.beer][-1], self.p2.industryMat[BuildingName.beer][-2])

        # # print('Last beer',  self.p2.industryMat[BuildingName.beer][-1])
        # # print('Available Builds after development:')
        # # for b, bl in self.p2.getAvailableBuilds()[0]:
        # #     print(b.name, ' in ',bl.town.name)


        # self.assertEqual(len(self.p2.getAvailableBuilds()[0]), 1, 'Shoould have overbuilding availablee after deveelopment')
    
   
    
    def testIndustryMat(self):
        self.resetGame(2)


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
