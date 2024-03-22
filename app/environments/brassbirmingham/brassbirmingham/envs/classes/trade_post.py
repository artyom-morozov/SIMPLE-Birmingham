from collections import defaultdict
from typing import List, Set, Tuple
from classes.buildings.building import Building
from classes.buildings.enums import BuildingName, MerchantName
from classes.buildings.market_building import MarketBuilding

from python.id import id
from python.print_colors import prLightPurple

from .road_location import RoadLocation
from .town import Town


class Merchant:
    def __init__(
        self,
        name: MerchantName,
    ):
        self.id = id()
        self.type = "TradePost Merchant"
        self.name = name
        self.hasBeer = True if self.name != MerchantName.blank else False
        self.tradePost: TradePost = None

    def canSellHere(self, buildingName: BuildingName):
        answer = self.name.value == buildingName.value or self.name == MerchantName.all
        return answer

    def consumeBeer(self):
        self.hasBeer = False

    def __str__(self) -> str:
        return f"Merchant({prLightPurple(self.name)})"

    def __repr__(self) -> str:
        return str(self)


class TradePost:
    """
    TradePost

    :param name: name
    :param beerAmount: amount of starting beer
    :param moneyGained: money gained from first trade
    :param victoryPointsGained: victory points gained from first trade
    :param incomeGained: income gained from first trade
    :param networkPoints: amount of points each road gets during counting step
    :param canDevelop: can develop after first trade
    """

    def __init__(
        self,
        name: str,
        beerAmount: int,
        moneyGained: int,
        victoryPointsGained: int,
        incomeGained: int,
        networkPoints: int,
        canDevelop: bool,
    ):
        self.id = id()
        self.type = "TradePost"
        self.name = name
        self.startingBeerAmount = beerAmount
        self.beerAmount = beerAmount
        self.moneyGained = moneyGained
        self.victoryPointsGained = victoryPointsGained
        self.incomeGained = incomeGained
        self.merchantTiles: List[Merchant] = []  # merchant tiles and beer at each slot
        self.networkPoints = networkPoints
        self.canDevelop = canDevelop
        self.networks: List[RoadLocation] = []
        self.supportedBuildings: Set[BuildingName] = set()

    # get Available canals to build
    def getAvailableCanals(self) -> List[RoadLocation]:
        return [rLocation for rLocation in self.networks if rLocation.isBuilt == False]

    # get Available railroads to build
    def getAvailableRailroads(self) -> List[RoadLocation]:
        return [rLocation for rLocation in self.networks if rLocation.isBuilt == False]

    """
    addMerchantTile
    game init use only
    trades which are possible to make, array any of ['blank', 'all', 'pottery', 'cotton', 'goods']

    :param merchantTile: merchantTile
    """

    def addMerchantTile(self, merchant: Merchant):

        self.merchantTiles.append(merchant)
        merchant.tradePost = self

        if merchant.name == MerchantName.all:
            self.supportedBuildings.update(
                [BuildingName.goods, BuildingName.pottery, BuildingName.cotton]
            )
        elif merchant.name == MerchantName.goods:
            self.supportedBuildings.add(BuildingName.goods)
        elif merchant.name == MerchantName.pottery:
            self.supportedBuildings.add(BuildingName.pottery)
        elif merchant.name == MerchantName.cotton:
            self.supportedBuildings.add(BuildingName.cotton)

    def canSellHere(self, buildingName: BuildingName):
        return buildingName in self.supportedBuildings

    """
    addRoadLocation
    game init use only

    :param roadLocation: roadLocation
    """

    def addRoadLocation(self, roadLocation: RoadLocation):
        roadLocation.addTown(self)
        self.networks.append(roadLocation)

    def __str__(self) -> str:
        return f"TP({prLightPurple(self.name)})"

    def __repr__(self) -> str:
        return str(self)
