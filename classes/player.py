from __future__ import annotations
from collections import defaultdict, deque

import itertools
from typing import TYPE_CHECKING, List, Set, Tuple

from .buildings.industry_building import IndustryBuilding

if TYPE_CHECKING:
    from .board import Board

import copy
import math

from classes.buildings.enums import BuildingName, BuildingType
from classes.cards.card import Card
from classes.cards.enums import CardName
from classes.enums import Era, PlayerId
from classes.cards.industry_card import IndustryCard
from classes.cards.location_card import LocationCard
from classes.hand import Hand
from consts import (
    BUILDINGS,
    CANAL_PRICE,
    ONE_RAILROAD_COAL_PRICE,
    ONE_RAILROAD_PRICE,
    STARTING_MONEY,
    STARTING_ROADS,
    TWO_RAILROAD_BEER_PRICE,
    TWO_RAILROAD_COAL_PRICE,
    TWO_RAILROAD_PRICE,
)
from python.id import id

from .trade_post import Merchant, TradePost
from .build_location import BuildLocation
from .buildings.building import Building
from .buildings.market_building import MarketBuilding
from .road_location import RoadLocation
from .town import Town

PLAYER_COLORS = ["Red", "Blue", "Green", "Yellow"]


class Player:
    def __init__(self, name: str, board: Board, playerId: PlayerId = None):
        self.id = playerId if playerId else id()
        self.name = name
        self.board = board
        self.color = (
            playerId.name if playerId else PLAYER_COLORS[len(self.board.players)]
        )

        self.hand = Hand(self.board.deck.draw(8))
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

        # If a playr just received a trade post bonus for free development
        self.freeDevelopCount = 0

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
        return self.currentNetworks

    def getCurrentBuildings(self) -> Set[Building]:
        return self.currentBuildings

    """
    pay - use instead of 'player.money -= amount' since this asserts no negative values
    :param int: amount to pay
    """

    def pay(self, amount: int):
        self.money -= amount
        assert self.money >= 0
        self.spentThisTurn += amount

    def incomeLevel(self, income=None):

        incomePoints = self.income if income is None else income

        if incomePoints <= 10:
            return incomePoints - 10
        if incomePoints <= 30:
            return math.ceil((incomePoints - 10) / 2)
        if incomePoints <= 60:
            return math.ceil(incomePoints / 3)
        if incomePoints <= 96:
            return 20 + math.ceil((incomePoints - 60) / 4)
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
                    else 5 if self.income % 4 == 2 else 6 if self.income % 4 == 3 else 7
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
            # first check if that amount is available
            canAffordCoal = (
                self.board.isCoalAvailableFromBuildings(buildLocation.town)
                or self.board.isCoalAvailableFromTradePosts(
                    buildLocation.town, building.coalCost, moneyRemaining
                )
            ) and (
                self.board.isIronAvailableFromBuildings()
                or self.board.isIronAvailableFromTradePosts(
                    building.ironCost, moneyRemaining
                )
            )

        if building.ironCost > 0:
            # first check if that amount is available
            canAffordIron = (
                self.board.isIronAvailableFromBuildings()
                or self.board.isIronAvailableFromTradePosts(
                    building.ironCost, moneyRemaining
                )
            ) and (
                self.board.isIronAvailableFromBuildings()
                or self.board.isIronAvailableFromTradePosts(
                    building.ironCost, moneyRemaining
                )
            )

        return canAffordCoal and canAffordIron

    def canAffordBuilding(
        self, building: Building, buildLocation: BuildLocation
    ) -> bool:

        ironCost = 0
        coalCost = 0

        ironNeeded = building.ironCost
        coalNeeded = building.coalCost

        if coalNeeded == 0 and ironNeeded == 0:
            return self.money >= building.cost

        coalAvailable = 0
        ironAvailable = 0

        for ironBuilding in self.board.getIronBuildings():
            ironAvailable += ironBuilding.resourceAmount
            if ironAvailable == ironNeeded:
                break

        if ironAvailable < ironNeeded:
            ironCost += self.board.priceForIron(ironNeeded - ironAvailable)

        if coalNeeded == 0:
            return self.money >= (building.cost + ironCost + coalCost)

        connectedToMine = False

        q = deque([buildLocation.town])
        v = set([buildLocation.town.id])

        while q:
            town: TradePost | Town = q.popleft()

            # Verify if tradepost has beer
            if isinstance(town, TradePost):
                connectedToMine = True

            # verify each town for coal
            if isinstance(town, Town):
                for bl in town.buildLocations:
                    if (
                        bl.building
                        and isinstance(bl.building, IndustryBuilding)
                        and bl.building.type == BuildingType.industry
                        and bl.building.name == BuildingName.coal
                    ):
                        coalAvailable += bl.building.resourceAmount

                    if coalAvailable >= coalNeeded:
                        return self.money >= (building.cost + ironCost + 0)

            # get town neighbors, add to q
            for roadLocation in town.networks:
                if roadLocation.isBuilt:
                    for _town in roadLocation.towns:
                        if _town.id not in v:
                            q.append(_town)
                            v.add(_town.id)

        if coalAvailable >= coalNeeded:
            return self.money >= (building.cost + ironCost + 0)

        if coalAvailable < coalNeeded and not connectedToMine:
            return False

        coalCost = self.board.priceForCoal(coalNeeded - coalAvailable)

        return self.money >= (building.cost + ironCost + coalCost)

    def canPlaceBuilding(
        self, building: Building, buildLocation: BuildLocation
    ) -> bool:
        if building.onlyPhaseOne and self.board.era != Era.canal:
            return False
        if building.onlyPhaseTwo and self.board.era != Era.railroad:
            return False

        if building.name not in buildLocation.possibleBuilds:
            return False

        # check if an alternative building exists in town
        if not buildLocation.building and len(buildLocation.possibleBuilds) > 1:
            for other_bl in buildLocation.town.buildLocations:
                if other_bl.id == buildLocation.id:
                    continue
                if (
                    not other_bl.building
                    and building.name in other_bl.possibleBuilds
                    and len(other_bl.possibleBuilds) == 1
                ):
                    return False

        return True

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
        return (
            self.board.era == Era.canal
            and not roadLocation.isBuilt
            and roadLocation.canBuildCanal
        )

    def canAffordOneRailroadIndustryResources(self, roadLocation: RoadLocation) -> bool:
        for town in roadLocation.towns:
            if self.board.getAvailableCoalAmount(town) >= ONE_RAILROAD_COAL_PRICE:
                return True
        return False

    def canAffordOneRailroad(self) -> bool:
        return self.money >= ONE_RAILROAD_PRICE

    def canPlaceOneRailroad(self, roadLocation: RoadLocation) -> bool:
        return (
            self.board.era == Era.railroad
            and not roadLocation.isBuilt
            and roadLocation.canBuildRailroad
        )

    def canAffordTwoRailroadIndustryResources(
        self, roadLocation1: RoadLocation, roadLocation2: RoadLocation
    ) -> bool:
        # FIXED issue - building second road X - 1 - 2, '2' isn't "networked" to X I think?
        # def fix second road - go one at a time func
        road1 = False
        road2 = False
        for town in roadLocation1.towns:
            if (
                self.board.getAvailableCoalAmount(town) >= TWO_RAILROAD_COAL_PRICE
                and self.board.getAvailableBeerAmount(self, town)
                >= TWO_RAILROAD_BEER_PRICE
            ):
                road1 = True
                # build tmp road (delete after)
                roadLocation1.isBuilt = True
                break
        if road1:
            for town in roadLocation2.towns:
                if (
                    self.board.getAvailableCoalAmount(town) >= TWO_RAILROAD_COAL_PRICE
                    and self.board.getAvailableBeerAmount(self, town)
                    >= TWO_RAILROAD_BEER_PRICE
                ):
                    roadLocation1.isBuilt = False
                    return True

        for town in roadLocation2.towns:
            if (
                self.board.getAvailableCoalAmount(town) >= TWO_RAILROAD_COAL_PRICE
                and self.board.getAvailableBeerAmount(self, town)
                >= TWO_RAILROAD_BEER_PRICE
            ):
                road2 = True
                # build tmp road (delete after)
                roadLocation2.isBuilt = True
                break

        if road2:
            for town in roadLocation1.towns:
                if (
                    self.board.getAvailableCoalAmount(town) >= TWO_RAILROAD_COAL_PRICE
                    and self.board.getAvailableBeerAmount(self, town)
                    >= TWO_RAILROAD_BEER_PRICE
                ):
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

        return building.beerCost <= self.board.getAvailableBeerAmount(
            self, building.town
        )

    """Possible Actions
    probably useful to separate into canX and doX functions for generating state and possible action array (?)"""

    def canOverbuild(self, oldBuilding: Building, newBuilding: Building):
        if oldBuilding.type != newBuilding.type:
            return False

        if newBuilding.tier <= oldBuilding.tier:
            return False

        if oldBuilding.name != newBuilding.name:
            return False

        if oldBuilding.owner.id != newBuilding.owner.id:
            if newBuilding.name == BuildingName.iron:
                return (
                    oldBuilding.isFlipped
                    and len(self.board.getIronBuildings()) == 0
                    and self.board.ironMarketRemaining == 0
                )
            if newBuilding.name == BuildingName.coal:
                return (
                    oldBuilding.isFlipped
                    and len(self.board.getCoalBuildings()) == 0
                    and self.board.ironMarketRemaining == 0
                )
            return False
        return True

    # 1 BUILD
    def canBuildBuilding(
        self, building: Building, buildLocation: BuildLocation
    ) -> bool:

        if self.board.era == Era.canal:
            # You may have a maximum of 1 Industry tile per location in Canal era
            for buildLocation_ in buildLocation.town.buildLocations:
                if buildLocation_.id != buildLocation.id:
                    if (
                        buildLocation_.building
                        and buildLocation_.building.owner.id == self.id
                    ):
                        return False

        canOverbuild = True
        # Check ovrbuilding
        if buildLocation.building:
            canOverbuild = self.canOverbuild(buildLocation.building, building)

        # print(
        #     self.canAffordBuildingIndustryResources(
        #         buildLocation, building
        #     ), self.canAffordBuilding(building), self.canPlaceBuilding(building, buildLocation), building.owner == self
        # )

        return (
            canOverbuild
            and self.canPlaceBuilding(building, buildLocation)
            and building.owner == self
            and self.canAffordBuilding(building, buildLocation)
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
    def canDevelop(self, building1: Building, building2: Building = None) -> bool:
        if not building2:
            return (
                building1.canBeDeveloped
                and building1.owner == self
                and not building1.isActive
                and not building1.isRetired
            )

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

    # BEER sourcee has to be correctly passed be in network
    # 4 SELL
    # TODO: Assert Connected to market
    def canSell(
        self,
        building: MarketBuilding,
        merchant: Merchant,
        beerSource: IndustryBuilding | Merchant = None,
    ) -> bool:
        assert (
            isinstance(beerSource, IndustryBuilding)
            and beerSource.type == BuildingType.industry
            and beerSource.name == BuildingName.beer
            and beerSource.resourceAmount > 0
        ) or (
            isinstance(beerSource, Merchant)
            and merchant.id == beerSource.id
            and beerSource.hasBeer
        )
        assert building.type == BuildingType.market
        assert building.isActive and building.owner == self
        assert merchant.canSellHere(building.name)
        assert self.board.areNetworked(building.town, merchant.tradePost)
        if not beerSource:
            return building.beerCost == 0

        if isinstance(beerSource, IndustryBuilding) and beerSource.owner != self:
            return self.board.areNetworked(building.town, beerSource.town)

        return True

    def liquidate(self, debt):

        sortedBuildings = sorted(self.currentBuildings, key=lambda x: x.cost)

        total_money = 0
        buildings_to_remove: List[Building] = []

        for building in sortedBuildings:
            if total_money >= debt:
                break
            total_money += building.cost // 2
            buildings_to_remove.append(building)

        # If the total money obtained is less than the debt, return -1
        if total_money < debt:
            return -1

        # Remove the liquidated buildings from the set
        for building in buildings_to_remove:
            building.isActive = False
            building.isRetired = True
            buildLocation: BuildLocation = building.buildLocation
            building.buildLocation = None
            buildLocation.building = None
            self.currentBuildings.remove(building)
        return total_money - debt

    def getIncome(self):
        newMoneyValue = self.money + self.incomeLevel()

        if newMoneyValue >= 0:
            self.money = newMoneyValue
            return

        debt = abs(newMoneyValue)

        liquidationMoney = self.liquidate(debt=debt)

        # substract VPS
        if len(self.currentBuildings) == 0 or liquidationMoney == -1:
            self.victoryPoints = max(0, self.victoryPoints - debt)
            return

        self.money = liquidationMoney

    # 5 LOAN
    def canLoan(self) -> bool:
        if self.income > 10:
            return True
        return self.income >= 3

    # 6 SCOUT
    def canScout(self) -> bool:
        if (
            len(self.board.wildIndustryCards) < 1
            or len(self.board.wildlocationCards) < 1
            or len(self.hand.cards) < 3
        ):
            return False

        for card in self.hand.cards:
            if card.isWild:
                return False

        return True

    # 7 PASS
    def canPassTurn(self) -> bool:
        return True

    """Actions"""

    def getAvailableBeerSources(
        self, building: MarketBuilding, test=False
    ) -> Tuple[Set[Merchant], Set[IndustryBuilding | Merchant], int]:

        # print("Getting available beer sources for", building)

        # Breweries with available beer that can be used
        beers: Set[IndustryBuilding | Merchant] = set()

        # merchants where the building can be sold
        merchants = set()

        beerFromBreweries = 0
        beerFromTradePosts = 0

        # Add all own beers
        for b in self.currentBuildings:
            if (
                isinstance(b, IndustryBuilding)
                and b.isBeerBuilding()
                and not b in beers
            ):
                beers.add(b)
                beerFromBreweries += b.resourceAmount

        # If Building is present start a searching for available Oponent BeerSources and Tradeposts in the network

        q = deque([building.town])
        v = set([building.town.id])

        while q:
            town: TradePost | Town = q.popleft()

            # Verify if tradepost has beer
            if isinstance(town, TradePost):
                if town.canSellHere(building.name):
                    for merchant in town.merchantTiles:
                        if merchant.canSellHere(building.name):
                            if merchant.hasBeer:
                                beerFromTradePosts = 1
                                beers.add(merchant)
                            merchants.add(merchant)

            # verify each town for beer
            if isinstance(town, Town):
                for bl in town.buildLocations:
                    if (
                        bl.building
                        and isinstance(bl.building, IndustryBuilding)
                        and bl.building.isBeerBuilding()
                        and not bl.building in beers
                    ):
                        beers.add(bl.building)
                        beerFromBreweries += bl.building.resourceAmount

            # get town neighbors, add to q
            for roadLocation in town.networks:
                if roadLocation.isBuilt:
                    for _town in roadLocation.towns:
                        if _town.id not in v:
                            q.append(_town)
                            v.add(_town.id)

        return merchants, beers, beerFromBreweries + beerFromTradePosts

    def getOwnBeerSources(self) -> Set[IndustryBuilding]:
        sources = set()
        for building in self.currentBuildings:
            if building.isBeerBuilding():
                sources.add(building)
        return sources

    def getAvailableRailroads(self, firstCoalSource: Town = None) -> Set[RoadLocation]:
        assert self.board.era == Era.railroad
        potenitalRoads: Set[RoadLocation] = self.getAvailableNetworks()
        potentialRailRoads: Set[RoadLocation] = set()

        townsConnectedToCoal, townsConnectedToMarket = (
            self.board.getTownsConnectedToCoal(firstCoalSource)
        )

        # print("Towns connected to coal", townsConnectedToCoal)

        ownBeerSources: Set[IndustryBuilding] = self.getOwnBeerSources()

        townsConnectedToBeer: Set[Town] = self.board.getTownsConnectedToBeer()

        for roadLocation in potenitalRoads:
            for town in roadLocation.towns:
                if (
                    not town in townsConnectedToCoal
                    and not town in townsConnectedToMarket
                ):
                    continue
                if firstCoalSource and not (
                    len(ownBeerSources) > 0 or town in townsConnectedToBeer
                ):
                    continue

                potentialRailRoads.add(roadLocation)
                break
        return potentialRailRoads

    # Get a list off all available road locations where a road could be build
    def getAvailableNetworks(self) -> Set[RoadLocation]:
        # print("Getting available networks...")

        isRailEra = self.board.era == Era.railroad

        # Has buildings
        potentialRoads: Set[RoadLocation] = set()

        # First network verification.
        # If no networks or builddings built can build a road anywhere
        if len(self.currentNetworks) == 0 and len(self.currentBuildings) == 0:

            for rLocation in self.board.roadLocations:
                if (
                    rLocation.isBuilt == True
                    or (
                        self.board.era == Era.canal and rLocation.canBuildCanal == False
                    )
                    or (
                        self.board.era == Era.railroad
                        and rLocation.canBuildRailroad == False
                    )
                ):
                    continue

                potentialRoads.add(rLocation)

            return potentialRoads

        # print("Current Towns", self.currentTowns)
        for t in self.currentTowns:
            # Get all available roadLocations from each town in the network
            availableBuildingRoads: List[RoadLocation] = (
                t.getAvailableRailroads() if isRailEra else t.getAvailableCanals()
            )
            # print(f"Available Networks from this {t}", availableBuildingRoads)

            potentialRoads.update(availableBuildingRoads)
        # print("Potential Roads", potentialRoads)

        # Get connected roads
        for network in self.currentNetworks:
            # print('Exploring network', network)
            for t in network.towns:
                # print('Exploring town', t)
                if t in self.currentTowns:
                    continue

                availableBuildingRoads: List[RoadLocation] = (
                    t.getAvailableRailroads() if isRailEra else t.getAvailableCanals()
                )
                # print('Available Networks from this town', availableBuildingRoads)

                potentialRoads.update(availableBuildingRoads)

        return potentialRoads

    # Based on Location Cards, Industry Cards, Available Builds from the mat
    def getAvailableLocationCardBuilds(self, card: LocationCard):

        # set of tuples (building, buildLocation) indicating possible  builds
        builds = set()

        firstBuildings = []
        for k in self.industryMat.keys():
            if len(self.industryMat[k]) > 0:
                firstBuildings.append(self.industryMat[k][-1])

        towns: List[Town] = (
            self.board.towns if card.isWild else [self.board.townDict[card.name]]
        )
        buildLocations: Set[BuildLocation] = set()

        for b in firstBuildings:
            for t in towns:
                if isinstance(t, Town):
                    for bl in t.buildLocations:
                        if self.canUseCardForBuilding(b, bl, card):
                            buildLocations.add(bl)
                            builds.add((b, bl))

        return builds, firstBuildings, buildLocations

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
                if self.canUseCardForBuilding(b, bl, card):
                    # print('Building ', b)
                    # print('BuildLocation', bl)
                    builds.add((b, bl))

        return builds, firstBuildings, availableBuildLocations

    def getAvailableBuilds(
        self,
    ) -> Tuple[Set[Tuple[Building, BuildLocation]], Set[Building], Set[BuildLocation]]:
        builds = set()
        firstBuildings = set()
        buildLocations = set()
        for card in self.hand.cards:
            if isinstance(card, LocationCard):
                zipped, fb, abl = self.getAvailableLocationCardBuilds(card)
                # print(f'Location Card ({card.name})', end=' [')
                # for b, bl in zipped:
                #     print(f'{b.name} in {bl.town.name}', end=', ')
                # print(']')
                builds.update(zipped)
            elif isinstance(card, IndustryCard):
                zipped, fb, abl = self.getAvailableIndustryCardBuilds(card)
                # print(f'Industry Card ({card.name})', end=' [')
                # for b, bl in zipped:
                #     print(f'{b.name} in {bl.town.name}', end=', ')
                # print(']')
                builds.update(zipped)
        return (
            builds,
            set([building for building, bl in builds]),
            set([buildLocation for b, buildLocation in builds]),
        )

    # Get a list of available actions rn
    def getAvailableActions(self):
        pass

    def isCardInHand(self, card: Card):
        return card.id in [_card.id for _card in self.hand.cards]

    def isInNetwork(self, buildLocation: BuildLocation):
        if buildLocation.building and buildLocation.building.owner == self:
            return True

        if self.board.era == Era.railroad and buildLocation.town in self.currentTowns:
            return True

        for roadLocation in self.currentNetworks:
            if buildLocation.town in roadLocation.towns:
                return True
        return False

    def canUseCardForBuilding(
        self, building: Building, buildLocation: BuildLocation, card: Card
    ):
        canUse = card.name == buildLocation.town.name or card.isWild
        if isinstance(card, IndustryCard):
            builds = set(card.getBuildNames())

            canUse = (
                (
                    (len(self.currentBuildings) == 0 and len(self.currentNetworks) == 0)
                    or self.isInNetwork(buildLocation)
                )
                and building.name in builds
                and len(set(buildLocation.possibleBuilds).intersection(builds)) > 0
            )

        return canUse and self.canBuildBuilding(building, buildLocation)

    # Get A list of buildings that could be sold if you have a beer source
    #
    #  should not work if  (2 beer box) connected to Tradepost with 1 beer available at each tile - no other beer

    def getAvailableBuildingsForSale(self):
        marketBuildings = set()

        # print("Getting available buildings for sale")
        # print("Current buildings", self.currentBuildings)
        for building in self.currentBuildings:
            # print(
            # "Checking building",
            # building,
            # )
            if (
                building.isFlipped
                or not building.isActive
                or not isinstance(building, MarketBuilding)
            ):
                continue
            tradePosts, beers, numBeerAvailable = self.getAvailableBeerSources(building)
            if len(tradePosts) > 0 and building.beerCost <= numBeerAvailable:
                marketBuildings.add(building)

        return marketBuildings

    # todo player discarding for actions
    # 1 BUILD
    def buildBuilding(
        self,
        industryName: BuildingName,
        buildLocation: BuildLocation,
        card: Card,
        coalSources: List[IndustryBuilding | TradePost] = [],
        ironSources: List[IndustryBuilding] = [],
    ):

        assert len(self.industryMat[industryName]) > 0

        building: Building = self.industryMat[industryName][-1]

        assert self.isCardInHand(card)
        assert self.canUseCardForBuilding(building, buildLocation, card)

        coalCost = 0
        ironCost = 0
        if len(coalSources) == 0:
            assert building.coalCost == 0
        elif len(coalSources) > 1:
            assert building.coalCost == len(coalSources)

        if card.isWild:
            if isinstance(card, LocationCard):
                self.board.wildlocationCards.append(card)

            if isinstance(card, IndustryCard):
                self.board.wildIndustryCards.append(card)

        # if overbuilding
        if buildLocation.building:
            buildLocation.building.isActive = False
            buildLocation.building.isRetired = True

        building.build(buildLocation)
        self.board.buildBuilding(building, buildLocation, self)

        # consume reesources
        if building.coalCost:
            if len(coalSources) < 2:
                coalCost += self.board.consumeCoal(coalSources[0], building.coalCost)
            else:
                for coalSource in coalSources:
                    coalCost += self.board.consumeCoal(coalSource, 1)

        if building.ironCost:

            if len(ironSources) == 0:
                ironCost += self.board.priceForIron(building.ironCost)
                self.board.ironMarketRemaining = max(
                    self.board.ironMarketRemaining - building.ironCost, 0
                )
            elif len(ironSources) < 2:
                if building.ironCost <= ironSources[0].resourceAmount:
                    ironSources[0].decreaseResourceAmount(building.ironCost)
                else:
                    diff = building.ironCost - ironSources[0].resourceAmount
                    ironSources[0].decreaseResourceAmount(ironSources[0].resourceAmount)
                    ironCost += self.board.priceForIron(diff)
                    self.board.ironMarketRemaining = max(
                        self.board.ironMarketRemaining - diff, 0
                    )
            else:
                for ironSource in ironSources:
                    ironSource.decreaseResourceAmount(1)
        self.pay(building.cost + ironCost + coalCost)
        # print(
        #     "Adding building",
        #     building,
        #     " to curreent buildings. Current buildings now",
        #     self.currentBuildings,
        # )
        self.currentBuildings.add(building)
        self.industryMat[industryName].pop(-1)
        self.currentTowns.add(building.town)
        self.hand.spendCard(card)

    # 2 NETWORK
    def buildCanal(self, roadLocation: RoadLocation, discard: Card):
        assert self.isCardInHand(discard)
        assert self.canBuildCanal(roadLocation)
        self.board.buildCanal(roadLocation, self)
        self.currentNetworks.add(roadLocation)
        self.hand.spendCard(discard)

    def buildOneRailroad(
        self,
        discard: Card,
        roadLocation: RoadLocation,
        coalSource: IndustryBuilding | TradePost,
    ):
        assert self.isCardInHand(discard)
        assert self.canBuildOneRailroad(roadLocation)

        price = 5 + self.board.consumeCoal(coalSource, 1)
        self.pay(price)
        self.board.buildOneRailroad(roadLocation, self)
        self.currentNetworks.add(roadLocation)
        self.hand.spendCard(discard)

    def buildTwoRailroads(
        self,
        discard: Card,
        roadLocation1: RoadLocation,
        roadLocation2: RoadLocation,
        coalSources: List[IndustryBuilding | TradePost],
        beerSource: IndustryBuilding,
    ):
        assert self.isCardInHand(discard)
        assert self.canBuildTwoRailroads(roadLocation1, roadLocation2)
        assert len(coalSources) == 2

        price = 15

        for coalSource in coalSources:
            price += self.board.consumeCoal(coalSource, 1)
        self.pay(price)

        self.board.buildTwoRailroads(roadLocation1, roadLocation2, self)
        self.currentNetworks.add(roadLocation1, roadLocation2)
        self.hand.spendCard(discard)

    def developOneIndustry(
        self,
        building: Building,
        discard: Card,
        ironSources: List[IndustryBuilding] = [],
    ):
        assert self.isCardInHand(discard)
        assert self.canDevelop(building)
        assert len(ironSources) == 1

        ironNeeded = 1
        if ironSources[0] is None:
            ironCost = self.board.priceForIron(ironNeeded)
            self.pay(ironCost)
            self.board.ironMarketRemaining = max(
                self.board.ironMarketRemaining - ironNeeded, 0
            )
        else:
            ironBuilding = ironSources[0]
            assert (
                ironBuilding.type == BuildingType.industry
                and ironBuilding.name == BuildingName.iron
            )
            assert (
                ironBuilding.isFlipped == False
                and ironBuilding.isActive == True
                and ironBuilding.isRetired == False
            )
            assert ironBuilding.resourceAmount >= ironNeeded
            ironBuilding.decreaseResourceAmount(ironNeeded)

        building.isRetired = True
        self.industryMat[building.name].pop(-1)
        self.hand.spendCard(discard)

    def countCurrentPoints(self):
        points = self.victoryPoints
        for building in self.currentBuildings:
            if building.isFlipped:
                points += building.victoryPointsGained

        for network in self.currentNetworks:
            for town in network.towns:
                if isinstance(town, Town):
                    points += town.getNetworkVictoryPoints()
                elif isinstance(town, TradePost):
                    points += town.networkPoints

        return points

    def canAffordOneDevelop(self):
        freeIron = sum(
            [ironB.resourceAmount for ironB in self.board.getIronBuildings()]
        )

        if freeIron >= 1:
            return True
        else:
            ironCost = self.board.priceForIron(1)
            return self.money >= ironCost

    def canAffordSecondDevelop(self, markedUsed: bool = False):
        freeIron = sum(
            [ironB.resourceAmount for ironB in self.board.getIronBuildings()]
        )

        if not markedUsed:
            freeIron -= 1

        if freeIron >= 1:
            return True

        ironNeeded = max(2 - freeIron, 0)
        ironCost = self.board.priceForIron(ironNeeded)
        return self.money >= ironCost

    def developTwoIndustries(
        self,
        building1: Building,
        building2: Building,
        discard: Card,
        ironSources: List[IndustryBuilding] = [],
    ):
        assert self.isCardInHand(discard)
        assert self.canDevelop(building1, building2)
        assert len(ironSources) == 2

        ironNeeded = 2
        for ironBuilding in ironSources:
            if ironBuilding is not None:
                assert (
                    ironBuilding.type == BuildingType.industry
                    and ironBuilding.name == BuildingName.iron
                )
                assert (
                    ironBuilding.isFlipped == False
                    and ironBuilding.isActive == True
                    and ironBuilding.isRetired == False
                )
                assert ironBuilding.resourceAmount >= 1
                ironBuilding.decreaseResourceAmount(1)
                ironNeeded -= 1
        if ironNeeded > 0:
            ironCost = self.board.priceForIron(ironNeeded)
            self.pay(ironCost)
            self.board.ironMarketRemaining = max(
                self.board.ironMarketRemaining - ironNeeded, 0
            )
        building1.isRetired = True
        building2.isRetired = True
        self.industryMat[building1.name].pop(-1)
        self.industryMat[building2.name].pop(-1)
        self.hand.spendCard(discard)

    # 3 DEVELOP
    def freeDevelop(self, building1: Building, building2: Building = None):
        assert self.freeDevelopCount > 0
        numBuildings = 1 if not building2 else 2
        assert self.freeDevelopCount == numBuildings

        assert self.canDevelop(building1, building2)
        building1.isRetired = True
        building2.isRetired = True

        self.industryMat[building1.name].pop(-1)
        self.industryMat[building2.name].pop(-1)
        self.freeDevelopCount -= numBuildings

    # 4 SELL
    def sell(
        self,
        discard: Card,
        forSale: List[
            Tuple[MarketBuilding, Tuple[IndustryBuilding | Merchant], Merchant]
        ],
        freeDevelop: List[BuildingName] = [],
    ):

        assert self.isCardInHand(discard)
        assert len(forSale) > 0
        for building, beerSources, merchant in forSale:
            assert building.beerCost == len(beerSources)
            for beerSource in beerSources:
                assert self.canSell(building, merchant, beerSource)
            self.board.sellBuilding(
                player=self, building=building, beerSources=beerSources
            )

        if self.freeDevelopCount > 0:
            assert len(freeDevelop) == self.freeDevelopCount
            for building in freeDevelop:
                assert building.name in self.industryMat.keys()
                assert len(self.industryMat[building.name]) > 0
                building = self.industryMat[building.name].pop(-1)
                building.isRetired = True
            self.freeDevelopCount = 0

        # self.board.sellBuilding(building, self)
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
        assert self.canScout()
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
