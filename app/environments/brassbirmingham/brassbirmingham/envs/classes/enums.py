from enum import Enum, IntEnum


class Era(Enum):
    canal = "canal"
    railroad = "railroad"


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
    Discard = 9
    Pass = 10
    Liquidate = 11