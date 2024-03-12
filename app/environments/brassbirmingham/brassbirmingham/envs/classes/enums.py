from enum import Enum, IntEnum


class Era(Enum):
    canal = "canal"
    railroad = "railroad"

class GameState(Enum):
    CARD_CHOICE = 0
    DEVELOP_CHOICE = 1
    BUILDING_CHOICE = 2
    TOWN_CHOICE = 3
    ROAD_CHOICE = 4
    NO_SELECTION = 5
    SCOUT_CHOICE = 6
    SECOND_ACTION = 7

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