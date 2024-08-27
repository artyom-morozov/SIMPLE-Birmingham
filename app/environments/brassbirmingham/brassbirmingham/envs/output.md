board.py:
```
from __future__ import annotations
from collections import defaultdict, deque

import copy
from typing import TYPE_CHECKING, Deque, Dict, List, Set, Tuple
from numpy.random import shuffle
from .cards.enums import CardName
from .cards.industry_card import IndustryCard
from .cards.location_card import LocationCard

from consts import (
    CANAL_PRICE,
    MAX_MARKET_COAL,
    MAX_MARKET_IRON,
    ONE_RAILROAD_COAL_PRICE,
    ONE_RAILROAD_PRICE,
    ROAD_LOCATIONS,
    STARTING_CARDS,
    STARTING_HAND_SIZE,
    STARTING_ROADS,
    TOWNS,
    TRADEPOSTS,
    TWO_RAILROAD_COAL_PRICE,
    TWO_RAILROAD_BEER_PRICE,
    TWO_RAILROAD_PRICE,
    MERCHANT_TILES,
)
from python.id import id
from python.print_colors import *

from .build_location import BuildLocation
from .buildings.building import Building
from .buildings.enums import BuildingName, BuildingType
from .buildings.industry_building import IndustryBuilding
from .buildings.market_building import MarketBuilding
from .deck import Deck
from .enums import Era, PlayerId
from .hand import Hand
from .road_location import RoadLocation
from .roads.canal import Canal
from .roads.railroad import Railroad
from .town import Town
from .trade_post import Merchant, TradePost

if TYPE_CHECKING:
    from .player import Player


class Board:
    def __init__(self, numPlayers: int, test=False):
        self.id = id()
        self.numPlayers = numPlayers
        self.era = Era.canal
        self.deck = Deck(copy.deepcopy(STARTING_CARDS[str(numPlayers)]))
        self.deck.discard(numPlayers)

        self.towns = copy.deepcopy(TOWNS)  # array of Town objects
        self.townDict = {}
        self.tradePosts = copy.deepcopy(TRADEPOSTS[str(numPlayers)])
        self.tradePostDict = {}
        self.merchantTiles = copy.deepcopy(MERCHANT_TILES[str(numPlayers)])
        self.merchants = [
            Merchant(name=merchantName) for merchantName in self.merchantTiles
        ]

        self.coalMarketRemaining = MAX_MARKET_COAL - 1  # coal market missing 1
        self.ironMarketRemaining = MAX_MARKET_IRON - 2  # iron market missing 1
        self.roadLocations = copy.deepcopy(ROAD_LOCATIONS)
        self.players: List[Player] = []  # array of Player objects
        self.id_to_player: Dict[str, Player] = {}

        self.wildIndustryCards: List[IndustryCard] = []
        self.wildlocationCards: List[LocationCard] = []

        for i in range(numPlayers):
            self.wildIndustryCards.append(IndustryCard(name=CardName.wild_industry))
            self.wildlocationCards.append(LocationCard(name=CardName.wild_location))

        for town in self.towns:
            town.addBoard(self)  # ref board to towns

        for town in self.towns:
            self.townDict[town.name] = town

        for tradePost in self.tradePosts:
            self.tradePostDict[tradePost.name] = tradePost
        # network towns together
        for town in self.towns:
            for roadLocation in self.roadLocations:
                if town.name in roadLocation.networks:
                    town.addRoadLocation(roadLocation)
        for tradePost in self.tradePosts:
            for roadLocation in self.roadLocations:
                if tradePost.name in roadLocation.networks:
                    tradePost.addRoadLocation(roadLocation)

        self.playerPoints = {}
        # init merchant tiles

        mechantTileId = 0
        if not test:
            shuffle(self.merchants)
        for tradePost in self.tradePosts:
            for beer in range(tradePost.beerAmount):
                tradePost.addMerchantTile(self.merchants[mechantTileId])
                mechantTileId += 1

    """
    addPlayer
    game init use only

    :param player: player
    """

    def addPlayer(self, player: Player):
        self.players.append(player)
        self.id_to_player[player.id] = player

    """
    orderPlayers
    determine turn order for players. Should be random on first turn

    :return id of the first player to go
    """

    def orderPlayers(self, random=False):

        if random:
            shuffle(self.players)
        else:
            self.players.sort(key=lambda p: p.spentThisTurn)

        for i in range(len(self.players)):
            self.players[i].player_order = i

        return self.players[0].id

    def getAllBuildings(self) -> List[Building]:
        l = []
        for town in self.towns:
            for buildLocation in town.buildLocations:
                if buildLocation.building:
                    l.append(buildLocation.building)
        return l

    def priceForCoal(self, coalNeeded: int) -> int:
        price = 0
        currCoalRemaining = self.coalMarketRemaining
        for _ in range(coalNeeded):
            if currCoalRemaining <= 0:
                price += 8
            elif currCoalRemaining == 1 or currCoalRemaining == 2:
                price += 7
            elif currCoalRemaining == 3 or currCoalRemaining == 4:
                price += 6
            elif currCoalRemaining == 5 or currCoalRemaining == 6:
                price += 5
            elif currCoalRemaining == 7 or currCoalRemaining == 8:
                price += 4
            elif currCoalRemaining == 9 or currCoalRemaining == 10:
                price += 3
            elif currCoalRemaining == 11 or currCoalRemaining == 12:
                price += 2
            elif currCoalRemaining >= 13:
                price += 1
            currCoalRemaining = max(currCoalRemaining - 1, 0)
        return price

    def priceForIron(self, ironNeeded: int) -> int:
        price = 0
        currIronRemaining = self.ironMarketRemaining
        for _ in range(ironNeeded):
            if currIronRemaining <= 0:
                price += 6
            elif currIronRemaining == 1 or currIronRemaining == 2:
                price += 5
            elif currIronRemaining == 3 or currIronRemaining == 4:
                price += 4
            elif currIronRemaining == 5 or currIronRemaining == 6:
                price += 3
            elif currIronRemaining == 7 or currIronRemaining == 8:
                price += 2
            elif currIronRemaining >= 9:
                price += 1
            currIronRemaining = max(currIronRemaining - 1, 0)
        return price

    """
    areNetworked
    
    :param town1: Town
    :param town2: Town
    :return: whether there is a road network built between towns
    """

    def areNetworked(
        self, t1: Town | Building | TradePost, t2: Town | Building | TradePost
    ) -> bool:
        # town contains building
        if type(t1) == Town and t2:
            for buildLocation in t1.buildLocations:
                if buildLocation.building and buildLocation.building.id == t2.id:
                    return True
        if type(t2) == Town and t1:
            for buildLocation in t2.buildLocations:
                if buildLocation.building and buildLocation.building.id == t1.id:
                    return True

        q = deque([t1])
        v = set(t1.id)

        while q:
            town = q.popleft()  # bfs
            # get town neighbors, add to q
            for roadLocation in town.networks:
                if roadLocation.isBuilt:
                    for _town in roadLocation.towns:
                        if _town.id not in v:
                            q.append(_town)
                            v.add(_town.id)
                            if _town.id == t2.id:
                                return True

                            if type(_town) == Town:
                                for buildLocation in _town.buildLocations:
                                    if (
                                        buildLocation.building
                                        and buildLocation.building.id == t2.id
                                    ):
                                        return True
        return False

    """
    removeXCoal
    
    :param X: amount of coal to remove
    :param towns: towns to search from, must be array [town]
    :param player: player to remove money from (if necessary)"""

    def removeXCoal(self, X: int, towns: List[Town], player: Player):
        for town in towns:
            availableCoal = self.getAvailableCoalBuildingsTradePosts(town)
            if len(availableCoal) == 0:
                continue

            _available = availableCoal.pop(0)
            while X > 0:
                if _available.type == "TradePost":
                    cost = self.priceForCoal(X)
                    player.pay(cost)
                    self.coalMarketRemaining = max(self.coalMarketRemaining - X, 0)
                    return
                else:
                    _available.decreaseResourceAmount(1)
                    if _available.resourceAmount == 0:
                        if len(availableCoal) == 0:
                            assert X == 1
                            return
                        _available = availableCoal.pop(0)
                X -= 1
            return

    """
    removeXIron
    
    :param X: amount of iron to remove
    :param player: player to remove money from (if necessary)"""

    def removeXIron(self, X: int, player: Player):
        availableIron = self.getAvailableIronBuildingsTradePosts()
        if len(availableIron) == 0:
            raise ValueError("Attempted to remove Iron but no iron is available")

        _available = availableIron.pop(0)
        while X > 0:
            if _available.type == "TradePost":
                cost = self.priceForIron(X)
                player.pay(cost)
                self.ironMarketRemaining = max(self.ironMarketRemaining - X, 0)
                return
            else:
                _available.decreaseResourceAmount(1)
                if _available.resourceAmount == 0:
                    if len(availableIron) == 0:
                        assert X == 1
                        return
                    _available = availableIron.pop(0)
            X -= 1
        return

    def giveTradePostBonus(self, player: Player, post: TradePost):
        if post.canDevelop:
            player.freeDevelopCount += 1
        elif post.moneyGained > 0:
            player.money += post.moneyGained
        elif post.incomeGained > 0:
            player.income += post.incomeGained
        elif post.victoryPointsGained > 0:
            player.victoryPoints += post.victoryPointsGained

    """
    removeXBeer
    
    :param X: amount of beer to remove
    :param towns: towns to search from, must be array [town]
    :param player: player to remove money from (if necessary)"""

    def removeXBeer(self, X: int, towns: List[Town], player: Player):
        for town in towns:
            availableBeer = self.getAvailableBeerBuildingsTradePosts(player, town)
            if len(availableBeer) == 0:
                continue

            _available = availableBeer.pop(0)
            while X > 0:
                if _available.type == "TradePost":
                    if _available.beerAmount > 0:
                        _available.beerAmount -= 1
                    else:
                        raise ValueError(
                            "Not enough beer in trade post, make sure we check there is enough before calling board.buildBuilding"
                        )
                else:
                    _available.decreaseResourceAmount(1)
                    if _available.resourceAmount == 0:
                        if len(availableBeer) == 0:
                            assert X == 1
                            return
                        _available = availableBeer.pop(0)
                X -= 1
            return

    """
    getCoalBuildings
    
    :return: array of buildings which have coal resources"""

    def getCoalBuildings(self) -> List[IndustryBuilding]:
        l = []
        for town in self.towns:
            for buildLocation in town.buildLocations:
                if (
                    buildLocation.building
                    and buildLocation.building.type == BuildingType.industry
                    and buildLocation.building.name == BuildingName.coal
                    and buildLocation.building.resourceAmount > 0
                ):
                    l.append(buildLocation.building)
        return l

    """
    getBeerBuildings
    
    :return: array of buildings which have beer resources"""

    def getBeerBuildings(self) -> List[IndustryBuilding]:
        l = []
        for building in self.getAllBuildings():
            if (
                building
                and building.type == BuildingType.industry
                and building.name == BuildingName.beer
                and building.resourceAmount > 0
            ):
                l.append(building)
        return l

    """
    getIronBuildings
    
    :return: array of buildings which have iron resources"""

    def getIronBuildings(self) -> List[IndustryBuilding]:
        l = []
        for building in self.getAllBuildings():
            if (
                building
                and building.type == BuildingType.industry
                and building.name == BuildingName.iron
                and building.resourceAmount > 0
            ):
                l.append(building)
        return l

    """
    isCoalAvailableFromBuildings
    
    :param town: town where coal is required
    :return: is there coal available from networked buildings
    """

    def isCoalAvailableFromBuildings(self, town: Town) -> bool:
        # areNetworked puts priority on closest buildings to pick from
        # todo add priority for own buildings (?)

        # check for towns with coal available
        coalBuildings = self.getCoalBuildings()
        for coalBuilding in coalBuildings:
            if self.areNetworked(town, coalBuilding):
                return True
        return False

    def findInNetwork(self, town: Town, function) -> bool:
        q = deque([town])
        v = set([town.id])

        while q:
            town: TradePost | Town = q.popleft()

            # Verify if tradepost has beer
            if function(town):
                return True

            # get town neighbors, add to q
            for roadLocation in town.networks:
                if roadLocation.isBuilt:
                    for _town in roadLocation.towns:
                        if _town.id not in v:
                            q.append(_town)
                            v.add(_town.id)
        return False

    """
    isIronAvailableFromBuildings
    
    :return: is there iron available from networked buildings
    """

    def isIronAvailableFromBuildings(self) -> bool:
        # areNetworked puts priority on closest buildings to pick from
        # todo add priority for own buildings (?)

        # check for towns with iron available
        return len(self.getIronBuildings()) > 0

    """
    isBeerAvailableFromBuildings
    
    :param player: player inquiring
    :param town: town where beer is required
    :return: is there beer available from networked buildings
    """

    def isBeerAvailableFromBuildings(self, player: Player, town: Town) -> bool:
        # areNetworked puts priority on closest buildings to pick from
        # todo add priority for own buildings (?)

        # check for towns with beer available
        beerBuildings = self.getBeerBuildings()
        for beerBuilding in beerBuildings:
            if beerBuilding.owner == player or self.areNetworked(town, beerBuilding):
                return True
        return False

    """
    isCoalAvailableFromTradePosts
    
    :param town: town where coal is required
    :param coalAmount: amount of coal required
    :param money: amount of money available
    :return: is there coal available from networked trade posts
    """

    def isCoalAvailableFromTradePosts(
        self, town: Town, coalAmount: int, money: int
    ) -> bool:
        # check for connection to tradeposts
        for tradePost in self.tradePosts:
            if self.areNetworked(town, tradePost):
                cost = self.priceForCoal(coalAmount)
                return money >= cost
        return False

    """
    isBeerAvailableFromTradePosts
    
    :param town: town where beer is required
    :param beerAmount: amount of beer required
    :param money: amount of money available
    :return: is there beer available from networked trade posts
    """

    def isBeerAvailableFromTradePosts(self, town: Town) -> bool:
        # check for connection to
        for tradePost in self.tradePosts:
            if self.areNetworked(town, tradePost):
                # enough money for beer amount?
                # tyler double check sale price on this
                if tradePost.beerAmount > 0:
                    return True
        return False

    """
    isIronAvailableFromTradePosts
    
    :param ironAmount: amount of iron required
    :param money: amount of money available
    :return: is there iron available from networked trade posts
    """

    def isIronAvailableFromTradePosts(self, ironAmount: int, money: int) -> bool:
        return money >= self.priceForIron(ironAmount)

    """
    getAvailableCoalAmount
    
    :param town: town where coal is required
    :return: amount of coal"""

    def getAvailableCoalAmount(self, town: Town) -> int:
        coalBuildings = self.getCoalBuildings()
        amount = 0
        for coalBuilding in coalBuildings:
            if self.areNetworked(town, coalBuilding):
                amount += coalBuilding.resourceAmount
        for tradePost in self.tradePosts:
            if self.areNetworked(town, tradePost):
                amount += self.coalMarketRemaining
                break
        return amount

    """
    getAvailableBeerAmount
    
    :param player: player inquiring
    :param town: town where beer is required
    :return: amount of beer"""

    def getAvailableBeerAmount(self, player: Player, town: Town) -> int:
        beerBuildings = self.getBeerBuildings()
        amount = 0
        for beerBuilding in beerBuildings:
            if beerBuilding.owner == player or self.areNetworked(town, beerBuilding):
                amount += beerBuilding.resourceAmount
        for tradePost in self.tradePosts:
            if self.areNetworked(town, tradePost):
                amount += tradePost.beerAmount
                break
        return amount

    """
    getAvailableCoalBuildingsTradePosts
    
    :param town: town where coal is required
    :return: buildings/tradeposts with coal"""

    def getAvailableCoalBuildingsTradePosts(
        self, town: Town
    ) -> List[IndustryBuilding | TradePost]:
        coalBuildings = self.getCoalBuildings()
        l = []
        for coalBuilding in coalBuildings:
            if self.areNetworked(town, coalBuilding):
                l.append(coalBuilding)
        for tradePost in self.tradePosts:
            if self.areNetworked(town, tradePost):
                l.append(tradePost)
        return l

    def dfs_and_collect(self, town: Town, visited: Set[Town] = set()):

        stack = [town]

        while len(stack):
            # Pop a vertex from stack and print it
            t = stack[-1]
            stack.pop()

            # Stack may contain same vertex twice. So
            # we need to print the popped item only
            # if it is not visited.
            if t not in visited:
                visited.add(t)

            # Get all adjacent vertices of the popped vertex s
            # If a adjacent has not been visited, then push it
            # to the stack.
            for roadLocation in t.networks:
                if roadLocation.isBuilt:
                    for newTown in roadLocation.towns:
                        if newTown not in visited:
                            stack.append(newTown)
        return visited

    def getTownsConnectedToCoal(
        self, excludeCoalSource: Town | TradePost = None
    ) -> Tuple[List[Town], List[Town | TradePost]]:
        coalTowns: List[Town] = [
            coalBuilding.buildLocation.town for coalBuilding in self.getCoalBuildings()
        ]

        # print("Towns With Coal:", [town.name for town in coalTowns])

        townsConnectedToCoal = set()
        townsConnectedtoMarket = set()  # towns connected to trade posts

        for coalTown in coalTowns:
            if (
                excludeCoalSource
                and coalTown.id == excludeCoalSource.id
                and excludeCoalSource.getBuildLocation(
                    BuildingName.coal
                ).building.resourceAmount
                < 2
            ):
                continue
            self.dfs_and_collect(coalTown, townsConnectedToCoal)

        for tradePost in self.tradePosts:
            self.dfs_and_collect(tradePost, townsConnectedtoMarket)

        return townsConnectedToCoal, townsConnectedtoMarket

    def getTownsConnectedToBeer(self) -> List[Town]:
        beerTowns: List[Town] = [
            beerBuilding.buildLocation.town for beerBuilding in self.getBeerBuildings()
        ]

        townsConnectedToBeer = set()

        for beerTown in beerTowns:
            self.dfs_and_collect(beerTown, townsConnectedToBeer)

        return townsConnectedToBeer

    def getAvailableCoalForTown(
        self, town: Town
    ) -> Tuple[List[IndustryBuilding | TradePost], TradePost]:
        l: Deque[Building] = deque()
        connectedMarket = None

        q = deque([town])
        v = set([town.id])

        while q:
            town: TradePost | Town = q.popleft()

            # Verify if tradepost has beer
            if isinstance(town, TradePost):
                connectedMarket = town

            # verify each town for coal
            if isinstance(town, Town):
                for bl in town.buildLocations:
                    if (
                        bl.building
                        and isinstance(bl.building, IndustryBuilding)
                        and bl.building.type == BuildingType.industry
                        and bl.building.name == BuildingName.coal
                        and bl.building.resourceAmount > 0
                    ):
                        l.append(bl.building)

            # get town neighbors, add to q
            for roadLocation in town.networks:
                if roadLocation.isBuilt:
                    for _town in roadLocation.towns:
                        if _town.id not in v:
                            q.append(_town)
                            v.add(_town.id)

        return l, connectedMarket

    def getAvailableBeerForTown(self, town: Town) -> List[IndustryBuilding]:
        l: Deque[Building] = deque()

        q = deque([town])
        v = set([town.id])

        while q:
            town: TradePost | Town = q.popleft()

            # verify each town for coal
            if isinstance(town, Town):
                for bl in town.buildLocations:
                    if (
                        bl.building
                        and isinstance(bl.building, IndustryBuilding)
                        and bl.building.type == BuildingType.industry
                        and bl.building.name == BuildingName.beer
                        and bl.building.resourceAmount > 0
                    ):
                        l.append(bl.building)

            # get town neighbors, add to q
            for roadLocation in town.networks:
                if roadLocation.isBuilt:
                    for _town in roadLocation.towns:
                        if _town.id not in v:
                            q.append(_town)
                            v.add(_town.id)

        return l

    """
    getAvailableIronBuildingsTradePosts
    :return: buildings/tradeposts with iron"""

    def getAvailableIronBuildingsTradePosts(self) -> List[IndustryBuilding | TradePost]:
        ironBuildings = self.getIronBuildings()
        l = []
        for ironBuilding in ironBuildings:
            l.append(ironBuilding)
        for tradePost in self.tradePosts:
            l.append(tradePost)
        return l

    """
    getAvailableBeerBuildingsTradePosts
    TODO: Remove this dumbass function
    
    :param player: player inquiring
    :param town: town where beer is required
    :return: buildings/tradeposts with beer"""

    def getAvailableBeerBuildingsTradePosts(
        self, player: Player, town: Town
    ) -> List[Building | TradePost]:
        beerBuildings = self.getBeerBuildings()
        l = []
        for beerBuilding in beerBuildings:
            if beerBuilding.owner == player or self.areNetworked(town, beerBuilding):
                l.append(beerBuilding)
        for tradePost in self.tradePosts:
            if self.areNetworked(town, tradePost):
                if tradePost.beerAmount > 0:
                    l.append(tradePost)
        return l

    """
    buildBuilding
    
    Make sure all costs and placements are checked and considered before calling this function
    :param building: building to build
    :param buildLocation: where to build building
    :param money: player's money
    """

    def buildBuilding(
        self, building: Building, buildLocation: BuildLocation, player: Player
    ):
        # build building - link building and buildLocation to each other
        buildLocation.addBuilding(building)
        building.build(buildLocation)

        if (
            building.name == BuildingName.iron
            and self.ironMarketRemaining < MAX_MARKET_IRON
        ):
            ironBuilding: IndustryBuilding = building
            available_space_in_market = MAX_MARKET_IRON - self.ironMarketRemaining
            resources_to_transfer = min(
                ironBuilding.resourceAmount, available_space_in_market
            )
            self.ironMarketRemaining += resources_to_transfer
            reward = self.priceForIron(resources_to_transfer)
            player.money += reward
            ironBuilding.decreaseResourceAmount(resources_to_transfer)
        # Fill coal
        if (
            building.name == BuildingName.coal
            and self.coalMarketRemaining < MAX_MARKET_COAL
            and self.findInNetwork(
                town=buildLocation.town, function=lambda t: isinstance(t, TradePost)
            )
        ):
            coalBuilding: IndustryBuilding = building
            available_space_in_market = MAX_MARKET_COAL - self.coalMarketRemaining
            resources_to_transfer = min(
                coalBuilding.resourceAmount, available_space_in_market
            )
            self.coalMarketRemaining += resources_to_transfer
            coalBuilding.decreaseResourceAmount(resources_to_transfer)

    def buildCanal(self, roadLocation: RoadLocation, player: Player):
        player.pay(CANAL_PRICE)
        player.roadCount -= 1
        roadLocation.build(Canal(player))

    def buildOneRailroad(self, roadLocation: RoadLocation, player: Player):
        player.pay(ONE_RAILROAD_PRICE)
        player.roadCount -= 1
        roadLocation.build(Railroad(player))

    def buildTwoRailroads(
        self, roadLocation1: RoadLocation, roadLocation2: RoadLocation, player: Player
    ):
        player.pay(TWO_RAILROAD_PRICE)
        player.roadCount -= 2
        roadLocation1.build(Railroad(player))
        roadLocation2.build(Railroad(player))

    """
    sellBuilding
    
    Make sure all costs and placements are checked and considered before calling this function
    :param building: building to sell
    """

    # def sellBuildings(self, buildings: List[MarketBuilding]):
    #     for building in buildings:
    #         building.sell()

    def consumeCoal(
        self, coalSource: IndustryBuilding | TradePost, coalNeeded: int
    ) -> int:
        if isinstance(coalSource, TradePost):
            coalCost = self.priceForCoal(coalNeeded)
            self.coalMarketRemaining = max(self.coalMarketRemaining - coalNeeded, 0)
            return coalCost
        coalSource.decreaseResourceAmount(coalNeeded)
        return 0

    def consumeBeer(
        self, building: MarketBuilding, beerSource: IndustryBuilding | Merchant
    ):
        if isinstance(beerSource, Merchant):
            assert beerSource.hasBeer == True
            beerSource.hasBeer = False
            self.giveTradePostBonus(player=building.owner, post=beerSource.tradePost)
            return
        beerSource.decreaseResourceAmount(1)

    def sellBuilding(
        self,
        player: Player,
        building: MarketBuilding,
        beerSources: Tuple[IndustryBuilding | Merchant],
    ):
        if building.beerCost == 0:
            building.sell()
        elif building.beerCost == 1:
            self.consumeBeer(building, beerSource=beerSources[0])
            building.sell()
            return
        else:
            self.consumeBeer(building, beerSource=beerSources[0])
            self.consumeBeer(building, beerSource=beerSources[1])
            building.sell()

    def getVictoryPoints(self) -> Dict[PlayerId, int]:
        points = defaultdict(int)

        for building in self.getAllBuildings():
            if building.isFlipped and not building.isRetired:
                points[building.owner.id] += building.victoryPointsGained

        print("Points for buildings:")
        for playerId, point_num in points.items():
            print(f"{self.id_to_player[playerId].name}: {point_num}")

        for player in self.players:
            amount = 0
            for network in player.currentNetworks:
                if network.road and network.isBuilt:
                    for town in network.towns:
                        if isinstance(town, Town):
                            amount += town.getNetworkVictoryPoints()
                        elif isinstance(town, TradePost):
                            amount += town.networkPoints
            print(f"Network points for {player.name}: {amount}")
            points[player.id] += amount

        for town in self.towns:
            for network in town.networks:
                if network.road and network.isBuilt:
                    points[network.road.owner.id] += town.getNetworkVictoryPoints()

        for tradePost in self.tradePosts:
            for network in tradePost.networks:
                if network.road and network.isBuilt:
                    points[network.road.owner.id] += tradePost.networkPoints

        return points

    def endRailEra(self):
        assert len(self.deck.cards) == 0
        for player in self.players:
            assert len(player.hand.cards) == 0

        # Calculate player points
        # Nothing to do
        return self.getVictoryPoints()

    def endCanalEra(self):
        assert len(self.deck.cards) == 0
        for player in self.players:
            assert len(player.hand.cards) == 0

        # Calculate player points
        self.playerPoints = {}

        # Shuffle draw deck
        self.deck = Deck(copy.deepcopy(STARTING_CARDS[str(self.numPlayers)]))

        # Set points to each player
        # Draw new hand
        for player_id, points in self.playerPoints.items():
            player = self.id_to_player[player_id]
            player.victoryPoints = player.countCurrentPoints()
            player.roadCount = STARTING_ROADS
            player.hand = Hand(self.deck.draw(STARTING_HAND_SIZE))
            self.playerPoints[player_id] = player.victoryPoints

        # Remove links
        for roadLocation in self.roadLocations:
            roadLocation.road = None
            roadLocation.isBuilt = False
        for town in self.towns:
            for buildLocation in town.buildLocations:
                if buildLocation.building and buildLocation.building.tier <= 1:

                    # Remove obsolete industries
                    buildLocation.building.isRetired = True
                    building = buildLocation.building
                    buildLocation.building.owner.currentBuildings.remove(building)

                    buildLocation.building = None
                    building.buildLocation = None
                    building.town = None

        for player in self.players:
            for network in player.currentNetworks:
                network.road = None
                network.isBuilt = False
            player.currentNetworks = []
            player.currentTowns = set(
                [building.town for building in player.currentBuildings]
            )

        # Reset merchant beer
        for tradepost in self.tradePosts:
            tradepost.beerAmount = tradepost.startingBeerAmount

        self.era = Era.railroad

        return self.playerPoints

```
enums.py:
```
from enum import Enum, IntEnum


class Era(Enum):
    canal = "canal"
    railroad = "railroad"


class GameState(Enum):
    CARD_CHOICE = 0
    DEVELOP1_CHOICE = 1
    BUILDING_CHOICE = 2
    TOWN_CHOICE = 3
    ROAD_CHOICE = 4
    NO_SELECTION = 5
    SCOUT_CHOICE = 6
    SECOND_ACTION = 7
    SELL_CHOICE = 8
    BEER_CHOICE = 9
    RESOURCE_CHOICE = 10
    COAL_CHOICE = 11
    IRON_CHOICE = 12
    LOAN_CHOICE = 13
    RAILROAD1_CHOICE = 14
    RAILROAD2_CHOICE = 15
    DEVELOP2_CHOICE = 16
    PASS_CHOICE = 17
    MERCHANT_CHOICE = 18
    TAKE_BEER_MERCHANT_CHOICE = 19
    FREE_DEVELOP_CHOICE = 20
    END_ACTION = 21


class PlayerId(IntEnum):
    Red = 1
    Blue = 2
    Green = 3
    Yellow = 4


class ActionTypes(IntEnum):
    PlaceCanal = 0
    PlaceRailRoad = 1
    PlaceSecondRoad = 2
    BuildIndustry = 3
    DevelopOneIndustry = 4
    DevelopTwoIndustries = 5
    Sell = 6
    Loan = 7
    Scout = 8
    Pass = 9
    Liquidate = 10

```
game.py:
```
from typing import List, Tuple, Dict
import numpy as np
import random
import copy
from collections import defaultdict, deque

from classes.buildings.industry_building import IndustryBuilding
from classes.enums import ActionTypes, Era, PlayerId
from classes.player import Player

from .board import Board


ROUNDS_PER_PLAYER_NUM = {"2": 10, "3": 9, "4": 8}

PLAYER_COLORS = ["Red", "Blue", "Green", "Yellow"]
PLAYER_NAMEES = ["Owen", "Brunel", "Arkwright", "Coade"]


class Game:
    def __init__(
        self, num_players=2, interactive=False, debug_mode=False, policies=None
    ):

        self.num_players = num_players
        self.max_turns = ROUNDS_PER_PLAYER_NUM[str(num_players)]
        self.reset()
        self.interactive = interactive
        self.debug_mode = debug_mode
        self.policies = policies
        self.players_go_index = 0
        self.winner = None
        self.playerVPS = {}

        self.canalWinner = None

        for player in self.board.players:
            self.playerVPS[player.id] = 0

        if interactive:
            self.display = self.initDisplay(interactive, debug_mode, policies)
        else:
            self.display = None

    def render(self):
        if self.display is None:
            self.display = self.initDisplay(
                self.interactive, self.debug_mode, self.policies
            )

        self.display.render()

    def initDisplay(self, interactive, debug_mode, policies):
        from classes.ui.display import Display as GameDisplay

        return GameDisplay(
            self, interactive=interactive, debug_mode=debug_mode, policies=policies
        )

    def reset(self):
        self.board = Board(self.num_players)
        self.players: Dict[PlayerId, Player] = {}
        self.action_history = defaultdict(list)
        self.turn = 1
        for color in PLAYER_COLORS[: self.num_players]:
            id = PlayerId[color]
            self.players[id] = Player(
                name=PLAYER_NAMEES[id - 1], board=self.board, playerId=id
            )
            print(f"Player {id} cards: {self.players[id].hand.cards}")

        # set player order
        self.players_go = self.board.orderPlayers(random=True)
        self.players_go_index = 0

        self.first_round = True
        self.player_has_to_liquidate = False
        self.players_to_liquidate = []

    # determine the order of the next player to go
    def change_order(self):
        self.board.players.sort(key=lambda p: p.spentThisTurn)

    def getIncomeGained(points: int) -> int:
        if points < 11:
            return 0  # No income for points less than 11
        elif points <= 30:
            # Calculate income for pairs from 11 to 30
            return (points - 10 + 1) // 2
        elif points <= 60:
            # Calculate income for triplets from 31 to 60
            # Adjust calculation to ensure 31-33 returns 11
            return 10 + (points - 31) // 3 + 1
        elif points <= 98:
            # Calculate income for quadruples from 61 to 98
            # Adjust calculation to ensure 61-64 returns 21
            return 20 + (points - 61) // 4 + 1
        else:
            # Points greater than 99 return 30
            return 30

    def do_action(self, action):
        player: Player = self.get_active_player()

        action_number = len(self.action_history[(self.turn, player.id)]) + 1
        message = {"player_id": player.id, "text": f"Action {action_number}: "}

        if "type" not in action:
            raise ValueError("Action must have a type")

        print(f"Doing action {action} for player {player.id}")
        if action["type"] == ActionTypes.Loan and "card" in action:
            player.loan(action["card"])
            message["text"] += f"{player.name} took a loan"
        elif action["type"] == ActionTypes.Pass and "card" in action:
            player.passTurn(action["card"])
            message["text"] += f"{player.name} passed"
        elif (
            action["type"] == ActionTypes.Scout
            and "card1" in action
            and "card2" in action
            and "card3" in action
        ):
            player.scout(action["card1"], action["card2"], action["card3"])
            message["text"] += f"{player.name} scouted"
        elif (
            action["type"] == ActionTypes.Sell
            and "card" in action
            and "forSale" in action
            and "freeDevelop" in action
        ):
            player.sell(action["card"], action["forSale"], action["freeDevelop"])
            message["text"] += f"{player.name} sold the following:\n"

            for building, beerSources, _ in action["forSale"]:
                soldMeessage = (
                    f"   {building.name.value.capitalize()} in {building.town.name}"
                )
                if len(beerSources) > 0:
                    soldMeessage += " with beer from:\n"
                    for beerSource in beerSources:
                        soldMeessage += "       "
                        soldMeessage += (
                            f"Brewery in {beerSource.town.name}"
                            if isinstance(beerSource, IndustryBuilding)
                            else f"Merchant in {beerSource.tradePost.name}"
                        )
                        soldMeessage += "\n"
                message["text"] += soldMeessage

        elif (
            action["type"] == ActionTypes.PlaceRailRoad
            and "card" in action
            and "road1" in action
            and "coalSource1" in action
        ):
            player.buildOneRailroad(
                action["card"], action["road1"], action["coalSource1"]
            )
            message[
                "text"
            ] += f"{player.name} built railroad: {action['road1'].towns[0].name} -- {action['road1'].towns[1].name}"
        elif (
            action["type"] == ActionTypes.PlaceSecondRoad
            and "card" in action
            and "road1" in action
            and "road2" in action
            and "coalSource1" in action
            and "coalSource2" in action
            and "beerSource" in action
        ):
            player.buildTwoRailroads(
                action["card"],
                action["road1"],
                action["road2"],
                [action["coalSource1"], action["coalSource2"]],
                action["beerSource"],
            )
            message["text"] += f"{player.name} built 2 railroads:\n "

            for road in (action["road1"], action["road2"]):
                message["text"] += f"   {road.towns[0].name} -- {road.towns[1].name}\n"
        elif (
            action["type"] == ActionTypes.BuildIndustry
            and "building" in action
            and "buildLocation" in action
            and "coalSources" in action
            and "ironSources" in action
            and "card" in action
        ):
            player.buildBuilding(
                action["building"].name,
                action["buildLocation"],
                action["card"],
                action["coalSources"],
                action["ironSources"],
            )
            message[
                "text"
            ] += f"{player.name} built {action['building'].name.value} ({action['building'].getTier()}) in {action['buildLocation'].town.name}"
        elif (
            action["type"] == ActionTypes.PlaceCanal
            and "road" in action
            and "card" in action
        ):
            player.buildCanal(
                roadLocation=action["road"],
                discard=action["card"],
            )
            message[
                "text"
            ] += f"{player.name} built canal: {action['road'].towns[0].name} -- {action['road'].towns[1].name}"
        elif (
            action["type"] == ActionTypes.DevelopOneIndustry
            and "card" in action
            and "industry1" in action
        ):

            initialTier = action["industry1"].getTier()
            player.developOneIndustry(
                action["industry1"],
                action["card"],
                action["ironSources"],
            )

            message[
                "text"
            ] += f'{player.name} developed {action["industry1"].name.value}: {initialTier} --> {action["industry1"].getTier()}'

        elif (
            action["type"] == ActionTypes.DevelopTwoIndustries
            and "card" in action
            and "industry1" in action
            and "industry2" in action
        ):
            if not "ironSources" in action:
                action["ironSources"] = []
            initialTiers = (
                action["industry1"].getTier(),
                action["industry2"].getTier(),
            )
            player.developTwoIndustries(
                action["industry1"],
                action["industry2"],
                action["card"],
                action["ironSources"],
            )
            message["text"] += f"{player.name} developed 2 industries:\n"

            for i, industry in enumerate([action["industry1"], action["industry2"]]):
                f"  {industry.name.value}: {initialTiers[i]} --> {industry.getTier()}\n"

        else:
            raise ValueError(f"Invalid action {action} for player {player.id}")
        return message

    def next_action(self, action):
        # if self.interactive:
        #     self.display.render()

        player = self.get_active_player()

        action_log = self.do_action(action)

        self.save_action(player.id, action)

        if (
            len(self.action_history[(self.turn, player.id)]) >= self.get_num_actions()
            and player.freeDevelopCount == 0
        ):
            self.players_go_index += 1
            if self.players_go_index == self.num_players:
                self.players_go_index = 0
                self.start_new_turn()
        return action_log

    def get_winner(self) -> Player:
        # Get the maximum number of victory points
        max_vps = max(self.playerVPS.values())

        # Get the players with the maximum number of victory points
        max_vps_players: List[Player] = [
            self.players[player_id]
            for player_id, vps in self.playerVPS.items()
            if vps == max_vps
        ]

        if len(max_vps_players) == 1:
            # If there is only one player with the maximum number of victory points, return that player
            return max_vps_players[0]
        else:
            # If there are multiple players with the maximum number of victory points, return the player with the most money
            return max(max_vps_players, key=lambda player: player.money)

    def start_new_turn(self):
        # check if end game/ era change
        if self.board.era == Era.canal and self.turn >= self.max_turns:
            self.playerVPS = self.board.endCanalEra()
            self.turn = 0
            return
        if self.board.era == Era.railroad and self.turn >= self.max_turns:
            self.board.endRailEra()
            for player_id, player in self.players.items():
                self.playerVPS[player_id] = player.countCurrentPoints()
            self.game_over = True
            self.winner = self.get_winner()
            return

        # determine spend order and reset
        self.players_go = self.board.orderPlayers()

        # reset spend amount and give income
        for player in self.board.players:
            player.spentThisTurn = 0
            incomeMoney = player.incomeLevel()
            if player.money + incomeMoney < 0:
                self.player_has_to_liquidate = True

                self.players_to_liquidate = player
                return
            player.money += incomeMoney

            player.hand.cards.extend(self.board.deck.draw(self.get_num_actions()))

        if self.turn == 1:
            self.first_round = False

        self.turn += 1

    # Return active player instance
    def get_active_player(self) -> Player:
        try:
            return self.board.players[self.players_go_index]
        except:
            print("Error: no active player")
            return None

    # return num actions available to the player right now
    def get_num_actions(self):
        return 1 if self.first_round else 2

    def save_current_state(self):

        state = {}

        state["player_has_to_liquidate"] = self.player_has_to_liquidate
        state["players_to_liquidate"] = copy.copy(self.players_to_liquidate)

        # state["tile_info"] = []
        # for tile in self.board.tiles:
        #     state["tile_info"].append(
        #         (tile.terrain, tile.resource, tile.value, tile.likelihood, tile.contains_robber)
        #     )

        # state["edge_occupancy"] = [edge.road for edge in self.board.edges]

        # state["corner_buildings"] = []
        # for corner in self.board.corners:
        #     if corner.building is not None:
        #         state["corner_buildings"].append((corner.building.type, corner.building.owner))
        #     else:
        #         state["corner_buildings"].append((None, None))

        # state["harbour_order"] = [harbour.id for harbour in self.board.harbours]

        # state["players"] = {}
        # for player_key, player in self.players.items():
        #     state["players"][player_key] = {"id": player.id,
        #          "player_order": copy.copy(player.player_order),
        #          "player_lookup": copy.copy(player.player_lookup),
        #          "inverse_player_lookup": copy.copy(player.inverse_player_lookup),
        #          "buildings": copy.copy(player.buildings),
        #          "roads": copy.copy(player.roads),
        #          "resources": copy.copy(player.resources),
        #          "visible_resources": copy.copy(player.visible_resources),
        #          "opponent_max_res": copy.copy(player.opponent_max_res),
        #          "opponent_min_res": copy.copy(player.opponent_min_res),
        #          "harbour_info": [(key, val.id) for key, val in player.harbours.items()],
        #          "longest_road": player.longest_road,
        #          "hidden_cards": copy.copy(player.hidden_cards),
        #          "visible_cards": copy.copy(player.visible_cards),
        #          "victory_points": player.victory_points
        #     }

        # state["players_go"] = self.players_go
        # state["player_order"] = copy.deepcopy(self.player_order)
        # state["player_order_id"] = self.player_order_id

        # state["resource_bank"] = copy.copy(self.resource_bank)
        # state["building_bank"] = copy.copy(self.building_bank)
        # state["road_bank"] = copy.copy(self.road_bank)
        # state["development_cards"] = copy.deepcopy(self.development_cards)
        # state["development_card_pile"] = copy.deepcopy(self.development_cards_pile)

        # state["largest_army"] = self.largest_army
        # state["longest_road"] = self.longest_road

        # state["initial_placement_phase"] = self.initial_placement_phase
        # state["initial_settlements_placed"] = copy.copy(self.initial_settlements_placed)
        # state["initial_roads_placed"] = copy.copy(self.initial_roads_placed)
        # state["initial_second_settlement_corners"] = copy.copy(self.initial_second_settlement_corners)

        # state["dice_rolled_this_turn"] = self.dice_rolled_this_turn
        # state["played_development_card_this_turn"] = self.played_development_card_this_turn
        # state["must_use_development_card_ability"] = self.must_use_development_card_ability
        # state["must_respond_to_trade"] = self.must_respond_to_trade
        # state["proposed_trade"] = copy.deepcopy(self.proposed_trade)
        # state["road_building_active"] = self.road_building_active
        # state["can_move_robber"] = self.can_move_robber
        # state["just_moved_robber"] = self.just_moved_robber
        # state["trades_proposed_this_turn"] = self.trades_proposed_this_turn
        # state["actions_this_turn"] = self.actions_this_turn
        # state["turn"] = self.turn
        # state["development_cards_bought_this_turn"] = self.development_cards_bought_this_turn
        # state["current_longest_path"] = copy.copy(self.current_longest_path)
        # state["current_army_size"] = copy.copy(self.current_army_size)
        # state["die_1"] = self.die_1
        # state["die_2"] = self.die_2

        # return state

    def save_action(self, player_id: str, action: dict):
        self.action_history[(self.turn, player_id)].append(action)

    def restore_state(self, state):

        state = copy.deepcopy(state)  # prevent state being changed

        self.players_to_discard = state["players_to_discard"]
        self.players_need_to_discard = state["players_need_to_discard"]

        # self.board.value_to_tiles = {}

        # for i, info in enumerate(state["tile_info"]):
        #     terrain, resource, value, likelihood, contains_robber = info[0], info[1], info[2], info[3], info[4]
        #     self.board.tiles[i].terrain = terrain
        #     self.board.tiles[i].resource = resource
        #     self.board.tiles[i].value = value
        #     self.board.tiles[i].likelihood = likelihood
        #     self.board.tiles[i].contains_robber = contains_robber

        #     if value != 7:
        #         if value in self.board.value_to_tiles:
        #             self.board.value_to_tiles[value].append(self.board.tiles[i])
        #         else:
        #             self.board.value_to_tiles[value] = [self.board.tiles[i]]
        #     if contains_robber:
        #         self.board.robber_tile = self.board.tiles[i]

        # for i, road in enumerate(state["edge_occupancy"]):
        #     self.board.edges[i].road = road

        # # for i, entry in enumerate(state["corner_buildings"]):
        # #     building, player = entry[0], entry[1]
        # #     if building is not None:
        # #         self.board.corners[i].building = Building(building, player, self.board.corners[i])
        # #     else:
        # #         self.board.corners[i].building = None

        # """have to reinitialise harbours - annoying"""
        # self.board.harbours = copy.copy([self.board.HARBOURS_TO_PLACE[i] for i in state["harbour_order"]])

        # for corner in self.board.corners:
        #     corner.harbour = None
        # for edge in self.board.edges:
        #     edge.harbour = None
        # for i, harbour in enumerate(self.board.harbours):
        #     # h_info = HARBOUR_CORNER_AND_EDGES[i]
        #     tile = self.board.tiles[h_info[0]]
        #     corner_1 = tile.corners[h_info[1]]
        #     corner_2 = tile.corners[h_info[2]]
        #     edge = tile.edges[h_info[3]]

        #     corner_1.harbour = harbour
        #     corner_2.harbour = harbour
        #     edge.harbour = harbour

        #     harbour.corners.append(corner_1)
        #     harbour.corners.append(corner_2)
        #     harbour.edge = edge

        # for key, player_state in state["players"].items():
        #     self.players[key].id = player_state["id"]
        #     self.players[key].player_order = player_state["player_order"]
        #     self.players[key].player_lookup = player_state["player_lookup"]
        #     self.players[key].inverse_player_lookup = player_state["inverse_player_lookup"]
        #     self.players[key].buildings = player_state["buildings"]
        #     self.players[key].roads = player_state["roads"]
        #     self.players[key].resources = player_state["resources"]
        #     self.players[key].visible_resources = player_state["visible_resources"]
        #     self.players[key].opponent_max_res = player_state["opponent_max_res"]
        #     self.players[key].opponent_min_res = player_state["opponent_min_res"]
        #     self.players[key].longest_road = player_state["longest_road"]
        #     self.players[key].hidden_cards = player_state["hidden_cards"]
        #     self.players[key].visible_cards = player_state["visible_cards"]
        #     self.players[key].victory_points = player_state["victory_points"]
        #     for info in player_state["harbour_info"]:
        #         key_res = info[0]; id = info[1]
        #         for harbour in self.board.harbours:
        #             if id == harbour.id:
        #                 self.players[key].harbours[key_res] = harbour

        # self.players_go = state["players_go"]
        # self.player_order = state["player_order"]
        # self.player_order_id = state["player_order_id"]

        # self.resource_bank = state["resource_bank"]
        # self.building_bank = state["building_bank"]
        # self.road_bank = state["road_bank"]
        # self.development_cards = state["development_cards"]
        # self.development_cards_pile = state["development_card_pile"]

        # self.largest_army = state["largest_army"]
        # self.longest_road = state["longest_road"]

        # self.initial_placement_phase = state["initial_placement_phase"]
        # self.initial_settlements_placed = state["initial_settlements_placed"]
        # self.initial_roads_placed = state["initial_roads_placed"]
        # self.initial_second_settlement_corners = state["initial_second_settlement_corners"]

        # self.dice_rolled_this_turn = state["dice_rolled_this_turn"]
        # self.played_development_card_this_turn = state["played_development_card_this_turn"]
        # self.must_use_development_card_ability = state["must_use_development_card_ability"]
        # self.must_respond_to_trade = state["must_respond_to_trade"]
        # self.proposed_trade = state["proposed_trade"]
        # self.road_building_active = state["road_building_active"]
        # self.can_move_robber = state["can_move_robber"]
        # self.just_moved_robber = state["just_moved_robber"]
        # self.trades_proposed_this_turn = state["trades_proposed_this_turn"]
        # self.actions_this_turn = state["actions_this_turn"]
        # self.turn = state["turn"]
        # self.development_cards_bought_this_turn = state["development_cards_bought_this_turn"]
        # self.current_longest_path = state["current_longest_path"]
        # self.current_army_size = state["current_army_size"]
        # self.die_1 = state["die_1"]
        # self.die_2 = state["die_2"]

```
player.py:
```
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

```
buildings\enums.py:
```
from enum import Enum


class BuildingName(Enum):
    goods = "goods"
    cotton = "cotton"
    pottery = "pottery"
    coal = "coal"
    beer = "beer"
    iron = "iron"


class BuildingType(Enum):
    industry = "industry"
    market = "market"

class MerchantName(Enum):
    goods = "goods"
    cotton = "cotton"
    pottery = "pottery"
    all = "all"
    blank = "blank"
```
