from __future__ import annotations

from typing import TYPE_CHECKING
from python.id import id

if TYPE_CHECKING:
    from ..player import Player

from .enums import BuildingName, BuildingType, MerchantName


def printRoman(num):
    # Storing roman values of digits from 0-9
    # when placed at different places
    m = ["", "M", "MM", "MMM"]
    c = ["", "C", "CC", "CCC", "CD", "D", "DC", "DCC", "DCCC", "CM "]
    x = ["", "X", "XX", "XXX", "XL", "L", "LX", "LXX", "LXXX", "XC"]
    i = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]

    # Converting to roman
    thousands = m[num // 1000]
    hundreds = c[(num % 1000) // 100]
    tens = x[(num % 100) // 10]
    ones = i[num % 10]

    ans = thousands + hundreds + tens + ones

    return ans


class Building:
    """
    Building object

    :param name: any of [goods, cotton, pottery]
    :param tier: ex: 3
    :param cost: cost
    :param coalCost: ex: 1
    :param ironCost: ironCost
    :param victoryPointsGained: victory points gained from selling
    :param incomeGained: income gained from selling
    :param networkPoints: amount of points each road gets during counting step
    :param canBeDeveloped=True:
    :param onlyPhaseOne=False:
    :param onlyPhaseTwo=False:
    """

    def __init__(
        self,
        type: BuildingType,
        name: BuildingName,
        tier: int,
        cost: int,
        coalCost: int,
        ironCost: int,
        victoryPointsGained: int,
        incomeGained: int,
        networkPoints: int,
        canBeDeveloped: bool,
        onlyPhaseOne: bool,
        onlyPhaseTwo: bool,
    ):
        self.id = id()
        self.type = type
        self.name = name
        self.tier = tier
        self.cost = cost
        self.coalCost = coalCost
        self.ironCost = ironCost
        self.victoryPointsGained = victoryPointsGained
        self.incomeGained = incomeGained
        self.networkPoints = networkPoints
        self.canBeDeveloped = canBeDeveloped
        self.onlyPhaseOne = onlyPhaseOne  # can only be built during phase 1
        self.onlyPhaseTwo = onlyPhaseTwo  # can only be built during phase 2

        self.buildLocation = None
        self.town = None
        self.isSold = False  # is sold/ran out of resources
        self.isActive = False  # is on the board i.e., not bought yet
        self.isRetired = False  # only used for retired buildings (tier 1's) in second phase (pieces 'put back in the box')
        self.isFlipped = False

    """
    addOwner - add player/owner to building
    game init use only

    :param owner: player
    """

    def addOwner(self, owner: Player):
        self.owner = owner

    def build(self, buildLocation):
        self.isActive = True
        self.buildLocation = buildLocation
        self.town = buildLocation.town

    def getBuildingNamesByMechant(merchantName: MerchantName):
        if merchantName == MerchantName.cotton:
            return [BuildingName.cotton]
        elif merchantName == MerchantName.goods:
            return [BuildingName.goods]
        elif merchantName == MerchantName.pottery:
            return [BuildingName.pottery]
        elif merchantName == MerchantName.all:
            return [BuildingName.cotton, BuildingName.goods, BuildingName.pottery]
        else:
            return []

    # Is beer building
    def isBeerBuilding(self) -> bool:
        isBeer = self.type == BuildingType.industry and self.name == BuildingName.beer
        hasBeer = (
            self.isActive
            and not self.isFlipped
            and not self.isRetired
            and self.resourceAmount > 0
        )
        return isBeer and hasBeer

    def getTier(self):
        return printRoman(self.tier)

    def __repr__(self) -> str:
        if self.isActive and self.town:
            return f"\nLevel {self.tier} {self.name.value} in {self.town} :: Owner: {self.owner}"

        return f"\nBuilding Level {self.getTier()}:{self.name.value}:: Owner: {self.owner}, Bought: {self.isActive}, Sold: {self.isSold} Retired: {self.isRetired}\n"
