from typing import List
from classes.buildings.enums import BuildingName
from python.print_colors import prGreen

from .card import Card
from .enums import CardName, CardType


class IndustryCard(Card):
    def __init__(self, name: CardName):
        super(IndustryCard, self).__init__(CardType.industry, name=name)
        self.isWild = name == CardName.wild_industry
        self.name = name

    def __str__(self) -> str:
        if self.isWild:
            return self.name.value
        return prGreen(self.name)

    def __repr__(self) -> str:
        if self.isWild:
            return self.name.value
        return prGreen(self.name)

    def getBuildNames(self) -> List[BuildingName]:
        if self.name == CardName.man_goods_or_cotton:
            return [BuildingName.goods, BuildingName.cotton]
        elif self.name == CardName.brewery:
            return [BuildingName.beer]
        elif self.name == CardName.coal_mine:
            return [BuildingName.coal]
        elif self.name == CardName.iron_works:
            return [BuildingName.iron]
        elif self.name == CardName.pottery:
            return [BuildingName.pottery]
        else:
            return [
                BuildingName.pottery,
                BuildingName.beer,
                BuildingName.goods,
                BuildingName.cotton,
                BuildingName.iron,
                BuildingName.coal,
            ]
