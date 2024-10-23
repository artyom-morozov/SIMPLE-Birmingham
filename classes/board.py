from __future__ import annotations
from collections import defaultdict, deque

import copy
from typing import TYPE_CHECKING, Deque, Dict, List, Set, Tuple
import random
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
    def __init__(self, numPlayers: int, test=False, seed=None):
        self.id = id()
        self.numPlayers = numPlayers
        self.era = Era.canal
        self.seed = seed
        self.deck = Deck(
            copy.deepcopy(STARTING_CARDS[str(numPlayers)]), np_shuffle=self.shuffle
        )
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
            self.shuffle(self.merchants)

        for tradePost in self.tradePosts:
            for beer in range(tradePost.beerAmount):
                tradePost.addMerchantTile(self.merchants[mechantTileId])
                mechantTileId += 1

    def shuffle(self, l):
        if self.seed:
            print("Seeds:", self.seed)
            random.seed(self.seed)
        random.shuffle(l)

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
            self.shuffle(self.players)
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
        self.deck = Deck(
            copy.deepcopy(STARTING_CARDS[str(self.numPlayers)]), np_shuffle=self.shuffle
        )

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
