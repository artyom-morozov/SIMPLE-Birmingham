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
