from __future__ import annotations
from collections import defaultdict

from typing import TYPE_CHECKING, List, Set

if TYPE_CHECKING:
    from .board import Board

import copy
import math

from classes.buildings.enums import BuildingType
from classes.cards.card import Card
from classes.cards.enums import CardName
from classes.enums import Era
from classes.cards.industry_card import IndustryCard
from classes.cards.location_card import LocationCard
from classes.hand import Hand
from consts import (BUILDINGS, CANAL_PRICE, ONE_RAILROAD_COAL_PRICE,
                    ONE_RAILROAD_PRICE, STARTING_MONEY,
                    STARTING_ROADS, TWO_RAILROAD_BEER_PRICE,
                    TWO_RAILROAD_COAL_PRICE, TWO_RAILROAD_PRICE)
from python.id import id

from .build_location import BuildLocation
from .buildings.building import Building
from .buildings.market_building import MarketBuilding
from .road_location import RoadLocation
from .town import Town

PLAYER_COLORS = ["Red", "Blue", "Green", "Yellow"]

class Player:
    def __init__(self, name: str, board: Board):
        self.id = id()
        self.name = name
        self.board = board
        self.color = PLAYER_COLORS[len(self.board.players)]
        self.hand = Hand(self.board.deck)
        self.money = STARTING_MONEY
        self.income = 10
        self.victoryPoints = 0
        self.spentThisTurn = 0
        self.buildings = copy.deepcopy(
            BUILDINGS
        )  # buildings, array of Building objects
        for building in self.buildings:
            building.addOwner(self)
        self.buildingDict = {}

        self.roadCount = STARTING_ROADS
        self.board.addPlayer(self)

        for building in self.buildings:
            self.buildingDict[f"{building.name.value} {building.tier}"] = building

        
        self.industryMat = defaultdict(list)

        self.initIndustryMat()



        # reference to all RoadLocations that are preseent on the board by this player
        # TODO: Add to it after building 
        # TODO: Clear when changing era
        self.currentNetworks: Set[RoadLocation] = set()



        # reference to all buildings that are preseent on the board by this player
        # TODO: Add to it after building 
        # TODO: Clear when changing era
        # TODO: Remove buillding when overbuilding
        self.currentBuildings: Set[Building] = set()


        self.currentTowns: Set[Town] = set()

    def initIndustryMat(self):
        for building in self.buildings:
            self.industryMat[building.name].append(building)
        
        for ind in self.industryMat.keys():
            self.industryMat[ind].sort(key=lambda b: b.tier, reverse=True)



    """
    getters 
    """
    def getCurrentNetworks(self) -> Set[RoadLocation]:
        return self.currentBuildings

    def getCurrentBuildings(self) -> Set[Building]:
        return self.currentBuildings


    """
    pay - use instead of 'player.money -= amount' since this asserts no negative values
    :param int: amount to pay
    """
    def pay(self, amount: int):
        self.money -= amount
        assert self.money >= 0

    def incomeLevel(self):
        if self.income <= 10:
            return self.income - 10
        if self.income <= 30:
            return math.ceil((self.income - 10) / 2)
        if self.income <= 60:
            return math.ceil(self.income / 3)
        if self.income <= 96:
            return 20 + math.ceil((self.income - 60) / 4)
        return 30

    def decreaseIncomeLevel(self, levels: int):
        def decreaseLevel():
            if self.income <= 11:
                self.income -= 1
            elif self.income == 12:
                self.income -= 2
            elif self.income <= 32:
                self.income -= 3 - (self.income % 2)
            elif self.income == 33:
                self.income -= 4
            elif self.income <= 63:
                self.income -= (
                    3 if self.income % 3 == 1 else 4 if self.income % 3 == 2 else 5
                )
            elif self.income == 64:
                self.income -= 6
            elif self.income <= 96:
                self.income -= (
                    4
                    if self.income % 4 == 1
                    else 5
                    if self.income % 4 == 2
                    else 6
                    if self.income % 4 == 3
                    else 7
                )
            else:
                self.income = 93
            self.income = max(self.income, 0)

        for _ in range(levels):
            decreaseLevel()

    # pass "money" object (money remaining after spending on building cost)
    def canAffordBuildingIndustryResources(
        self, buildLocation: BuildLocation, building: Building
    ) -> bool:
        canAffordCoal = True
        canAffordIron = True
        moneyRemaining = self.money - building.cost
        if building.coalCost > 0:
            #first check if that amount is available
            canAffordCoal = (
                self.board.isCoalAvailableFromBuildings(buildLocation.town)
                or self.board.isCoalAvailableFromTradePosts(
                    buildLocation.town, building.coalCost, moneyRemaining
                )
            ) and (
                self.board.isIronAvailableFromBuildings()
                or self.board.isIronAvailableFromTradePosts(building.ironCost, moneyRemaining)
            )

        if building.ironCost > 0:
            #first check if that amount is available
            canAffordIron = (
                self.board.isIronAvailableFromBuildings()
                or self.board.isIronAvailableFromTradePosts(
                    building.ironCost, moneyRemaining
                )
            ) and (
                self.board.isIronAvailableFromBuildings()
                or self.board.isIronAvailableFromTradePosts(building.ironCost, moneyRemaining)
            )

        return canAffordCoal and canAffordIron

    def canAffordBuilding(self, building: Building) -> bool:
        return self.money >= building.cost

    def canPlaceBuilding(
        self, building: Building, buildLocation: BuildLocation
    ) -> bool:
        if building.onlyPhaseOne and self.board.era != Era.canal:
            return False
        if building.onlyPhaseTwo and self.board.era != Era.railroad:
            return False

        return buildLocation.isPossibleBuild(building)

    def totalBuildingCost(
        self, building: Building, coalCost: int, ironCost: int
    ) -> int:
        return (
            building.cost
            + self.board.priceForCoal(coalCost)
            + self.board.priceForIron(ironCost)
        )

    def canAffordCanal(self) -> bool:
        return self.money >= CANAL_PRICE

    def canPlaceCanal(self, roadLocation: RoadLocation) -> bool:
        return self.board.era == Era.canal and not roadLocation.isBuilt and roadLocation.canBuildCanal

    def canAffordOneRailroadIndustryResources(self, roadLocation: RoadLocation) -> bool:
        for town in roadLocation.towns:
            if self.board.getAvailableCoalAmount(town) >= ONE_RAILROAD_COAL_PRICE:
                return True
        return False

    def canAffordOneRailroad(self) -> bool:
        return self.money >= ONE_RAILROAD_PRICE

    def canPlaceOneRailroad(self, roadLocation: RoadLocation) -> bool:
        return self.board.era == Era.railroad and not roadLocation.isBuilt and roadLocation.canBuildRailroad

    def canAffordTwoRailroadIndustryResources(
        self, roadLocation1: RoadLocation, roadLocation2: RoadLocation
    ) -> bool:
        # FIXED issue - building second road X - 1 - 2, '2' isn't "networked" to X I think?
        # def fix second road - go one at a time func
        road1 = False
        road2 = False
        for town in roadLocation1.towns:
            if self.board.getAvailableCoalAmount(town) >= TWO_RAILROAD_COAL_PRICE and self.board.getAvailableBeerAmount(self, town) >= TWO_RAILROAD_BEER_PRICE:
                road1 = True
                # build tmp road (delete after)
                roadLocation1.isBuilt = True
                break
        if road1:
            for town in roadLocation2.towns:
                if self.board.getAvailableCoalAmount(town) >= TWO_RAILROAD_COAL_PRICE and self.board.getAvailableBeerAmount(self, town) >= TWO_RAILROAD_BEER_PRICE:
                    roadLocation1.isBuilt = False
                    return True

        for town in roadLocation2.towns:
            if self.board.getAvailableCoalAmount(town) >= TWO_RAILROAD_COAL_PRICE and self.board.getAvailableBeerAmount(self, town) >= TWO_RAILROAD_BEER_PRICE:
                road2 = True
                # build tmp road (delete after)
                roadLocation2.isBuilt = True
                break
        
        if road2:
            for town in roadLocation1.towns:
                if self.board.getAvailableCoalAmount(town) >= TWO_RAILROAD_COAL_PRICE and self.board.getAvailableBeerAmount(self, town) >= TWO_RAILROAD_BEER_PRICE:
                    roadLocation2.isBuilt = False
                    return True
            
        return False
    
    def canAffordTwoRailroads(self) -> bool:
        return self.money >= TWO_RAILROAD_PRICE

    def canPlaceTwoRailroads(
        self, roadLocation1: RoadLocation, roadLocation2: RoadLocation
    ) -> bool:
        return self.canPlaceOneRailroad(roadLocation1) and self.canPlaceOneRailroad(
            roadLocation2
        )

    def canAffordSellBuilding(self, building: MarketBuilding) -> bool:
        assert building.type == BuildingType.market
        return building.beerCost <= self.board.getAvailableBeerAmount(
            self, building.town
        )

    """Possible Actions
    probably useful to separate into canX and doX functions for generating state and possible action array (?)"""
    # 1 BUILD
    def canBuildBuilding(
        self, building: Building, buildLocation: BuildLocation
    ) -> bool:

        if self.board.era == Era.canal:
            # You may have a maximum of 1 Industry tile per location in Canal era
            for buildLocation_ in buildLocation.town.buildLocations:
                if buildLocation_.id != buildLocation.id:
                    if buildLocation_.building and buildLocation_.building.owner.id == self.id:
                        return False

        # print(
        #     self.canAffordBuildingIndustryResources(
        #         buildLocation, building
        #     ), self.canAffordBuilding(building), self.canPlaceBuilding(building, buildLocation), building.owner == self
        # )
        return (
            self.canAffordBuildingIndustryResources(
                buildLocation, building
            )
            and self.canAffordBuilding(building)
            and self.canPlaceBuilding(building, buildLocation)
            and building.owner == self
        )

    # 2 NETWORK
    def canBuildCanal(self, roadLocation: RoadLocation) -> bool:
        return (
            self.roadCount > 0
            and self.canAffordCanal()
            and self.canPlaceCanal(roadLocation)
        )

    def canBuildOneRailroad(self, roadLocation: RoadLocation) -> bool:
        return (
            self.roadCount > 0
            and self.canAffordOneRailroad()
            and self.canPlaceOneRailroad(roadLocation)
            and self.canAffordOneRailroadIndustryResources(roadLocation)
        )

    def canBuildTwoRailroads(
        self, roadLocation1: RoadLocation, roadLocation2: RoadLocation
    ) -> bool:
        return (
            self.roadCount > 1
            and self.canAffordTwoRailroads()
            and self.canAffordTwoRailroadIndustryResources(roadLocation1, roadLocation2)
            and self.canPlaceTwoRailroads(roadLocation1, roadLocation2)
        )

    # 3 DEVELOP
    def canDevelop(self, building1: Building, building2: Building) -> bool:
        return (
            not building1.isActive
            and not building1.isRetired
            and building1.canBeDeveloped
            and building1.owner == self
            and not building2.isActive
            and not building2.isRetired
            and building2.canBeDeveloped
            and building2.owner == self
        )

    # 4 SELL
    def canSell(self, building: MarketBuilding) -> bool:
        return (
            building.isActive
            and building.owner == self
            and self.canAffordSellBuilding(building)
        )

    # 5 LOAN
    def canLoan(self) -> bool:
        return self.income >= 3

    # 6 SCOUT
    def canScout(self, additionalDiscard: Card) -> bool:
        if len(self.board.wildIndustryCards) < 1 and len(self.board.wildlocationCards) < 1:
            return False

        ownership = False
        for card in self.hand.cards:
            if card.isWild:
                # No scouting if player has at least 1 wild card already
                return False
            if card.id == additionalDiscard.id:
                ownership = True

        return ownership

    # 7 PASS
    def canPassTurn(self) -> bool:
        return True

    """Actions"""
    
    # Get a list off all available road locations where a road could be build
    def getAvailableNetworks(self) -> Set[RoadLocation]:
        
        isRailEra = self.board.era == Era.railroad
        
        # Has buildings
        potentialRoads: Set[RoadLocation] = set()
        
        # First network verification.
        # If no networks or builddings built can build a road anywhere
        if len(self.currentNetworks) == 0 and len(self.currentBuildings) == 0:
            
            for rLocation in self.board.roadLocations:
                if rLocation.isBuilt == True or (self.board.era == Era.canal and  rLocation.canBuildCanal == False) or (self.board.era == Era.railroad and rLocation.canBuildRailroad == False):
                    continue

                potentialRoads.add(rLocation)

            return potentialRoads

       
    
        for t in self.currentTowns:           
            # Get all available roadLocations from each town in the network
            availableBuildingRoads: List[RoadLocation] = t.getAvailableRailroads() if isRailEra else t.getAvailableCanals()
            potentialRoads.update(availableBuildingRoads)

        # Get connected roads
        for network in self.currentNetworks:
            # print('Exploring network', network)
            for t in network.towns:
                # print('Exploring town', t)
                if t in self.currentTowns:
                    continue
                availableBuildingRoads: List[RoadLocation] = t.getAvailableRailroads() if isRailEra else t.getAvailableCanals()
                # print('Available Networks from this town', availableBuildingRoads)

                potentialRoads.update(availableBuildingRoads)
        
        
            
        return potentialRoads

    # Based on Location Cards, Industry Cards, Available Builds from the mat
    def getAvailableLocationCardBuilds(self, card: LocationCard):

        # set of tuples (building, buildLocation) indicating possible  builds 
        builds = set()

        if not isinstance(card, LocationCard):
            return builds

        firstBuildings = []
        for k in self.industryMat.keys():
            if len(self.industryMat[k]) > 0:
                firstBuildings.append(self.industryMat[k][-1])
        
        # TODO: Return all unoccupied towns if wild 
        if card.isWild:
            for b in firstBuildings: 
                for t in self.board.towns:
                    for bl in t.buildLocations:
                        if self.canBuildBuilding(b, bl):
                            builds.add((b, bl))
            return builds

        town: Town = self.board.townDict[card.name]

        availableBuildLocations = [bl for bl in town.buildLocations]
        
        for b in firstBuildings:
            for bl in availableBuildLocations:
                if self.canBuildBuilding(b, bl):
                    builds.add((b, bl))
        
        return builds
    
    # Based on Location Cards, Industry Cards, Available Builds from the mat
    def getAvailableIndustryCardBuilds(self, card: IndustryCard):

        # set of tuples (building, buildLocation) indicating possible  builds 
        builds = set()

        if not isinstance(card, IndustryCard):
            return builds

        # print('Getting available industry card builds. Industry is ', card.name)

        firstBuildings = []
        
        for buildName in card.getBuildNames():
            if len(self.industryMat[buildName]) > 0:
                firstBuildings.append(self.industryMat[buildName][-1])

        # print('First buildings are now', firstBuildings)
        availableBuildLocations = set()
        
        # First rounds nothing on board
        if len(self.currentBuildings) < 1 and len(self.currentNetworks) < 1:
            for t in self.board.towns:
                for bl in t.buildLocations:
                      for bname in card.getBuildNames():
                                if bname in bl.possibleBuilds:
                                    availableBuildLocations.add(bl)


        for b in self.currentBuildings:
            if b.town and isinstance(b.town, Town):
                for bl in b.town.buildLocations:
                    for bname in card.getBuildNames():
                                if bname in bl.possibleBuilds:
                                    availableBuildLocations.add(bl)

        for rl in self.currentNetworks:
            for t in rl.towns:
                if isinstance(t, Town):
                    for bl in t.buildLocations:
                        for bname in card.getBuildNames():
                                if bname in bl.possibleBuilds:
                                    availableBuildLocations.add(bl)

        # print('Availablee Build locations after going through current network', availableBuildLocations)

        for b in firstBuildings:
            for bl in availableBuildLocations:
                if self.canBuildBuilding(b, bl):
                    # print('Building ', b)
                    # print('BuildLocation', bl)
                    builds.add((b, bl))

        return builds

    def getAvailableBuilds(self):
        builds = set()
        for card in self.hand.cards:
            if isinstance(card, LocationCard):
                builds.update(self.getAvailableLocationCardBuilds(card))
            elif isinstance(card, IndustryCard):
                builds.update(self.getAvailableIndustryCardBuilds(card))
        return builds

    # Get a list of available actions rn
    def getAvailableActions(self):
        pass

    def isCardInHand(self, card: Card):
        return card.id in [_card.id for _card in self.hand.cards]

    # todo player discarding for actions
    # 1 BUILD
    def buildBuilding(self, building: Building, buildLocation: BuildLocation, card: Card):
        assert building == self.industryMat[building.name][-1]
        assert self.isCardInHand(card)
        assert self.canBuildBuilding(building, buildLocation)
        if isinstance(card, LocationCard):
            assert card.name == buildLocation.town.name
            if card.isWild:
                self.board.wildlocationCards.append(card)
                self.hand.cards = list(
                    filter(lambda x: x.id != card.id, self.hand.cards)
                )  
            else:
                self.hand.spendCard(card)

        if isinstance(card, IndustryCard):
            assert building.name in card.getBuildNames()
            if card.isWild:
                self.board.wildIndustryCards.append(card)
                self.hand.cards = list(
                    filter(lambda x: x.id != card.id, self.hand.cards)
                )  
            else:
                self.hand.spendCard(card)
        # if overbuilding
        if buildLocation.building:
            buildLocation.building.isActive = False
            buildLocation.building.isRetired = True
        building.build(buildLocation)
        self.board.buildBuilding(building, buildLocation, self)
        self.currentBuildings.add(building)
        self.industryMat[building.name].pop(-1)
        self.currentTowns.add(building.town)
        

    # 2 NETWORK
    def buildCanal(self, roadLocation: RoadLocation, discard: Card):
        assert self.isCardInHand(discard)
        assert self.canBuildCanal(roadLocation)
        self.board.buildCanal(roadLocation, self)
        self.currentNetworks.add(roadLocation)
        self.hand.spendCard(discard)

    def buildOneRailroad(self, roadLocation: RoadLocation, discard: Card):
        assert self.isCardInHand(discard)
        assert self.canBuildOneRailroad(roadLocation)
        self.board.buildOneRailroad(roadLocation, self)
        self.currentNetworks.add(roadLocation)
        self.hand.spendCard(discard)

    def buildTwoRailroads(
        self, roadLocation1: RoadLocation, roadLocation2: RoadLocation, discard: Card
    ):
        assert self.isCardInHand(discard)
        assert self.canBuildTwoRailroads(roadLocation1, roadLocation2)
        self.board.buildTwoRailroads(roadLocation1, roadLocation2, self)
        self.currentNetworks.add(roadLocation1, roadLocation2)
        self.hand.spendCard(discard)


    # 3 DEVELOP
    def develop(self, building1: Building, building2: Building, discard: Card):
        assert self.isCardInHand(discard)
        assert self.canDevelop(building1, building2)
        building1.isRetired = True
        building2.isRetired = True

        self.industryMat[building1.name].pop(-1)
        self.industryMat[building2.name].pop(-1)
        self.hand.spendCard(discard)


    # 4 SELL
    def sell(self, building: MarketBuilding, discard: Card):
        assert self.isCardInHand(discard)
        assert self.canSell(building)
        self.board.sellBuilding(building, self)
        self.hand.spendCard(discard)


    # 5 LOAN
    def loan(self, discard: Card):
        assert self.isCardInHand(discard)
        assert self.canLoan()
        self.decreaseIncomeLevel(3)
        self.money += 30
        self.hand.spendCard(discard)

    # 6 SCOUT
    def scout(self, additionalDiscard: Card, card1: Card, card2: Card):
        assert self.isCardInHand(additionalDiscard)
        assert self.isCardInHand(card1)
        assert self.isCardInHand(card2)
        assert self.canScout(additionalDiscard)
        self.hand.add(self.board.wildlocationCards.pop(0))
        self.hand.add(self.board.wildIndustryCards.pop(0))
        self.hand.spendCard(additionalDiscard)
        self.hand.spendCard(card1)
        self.hand.spendCard(card2)

    # 7 PASS
    def passTurn(self, discard: Card):
        assert self.isCardInHand(discard)
        assert self.canPassTurn()
        self.hand.spendCard(discard)
        return

    def __repr__(self) -> str:
        return self.name
