from python.print_colors import prCyan, prGreen, prLightGray, prPurple, prRed, prYellow

from .card import Card
from .enums import CardName, CardType, Colours

# towns
LEEK = "Leek"
STOKE_ON_TRENT = "Stoke-On-Trent"
STONE = "Stone"
CANNOCK = "Cannock"
UTTOXETER = "Uttoxeter"
BELPER = "Belper"
DERBY = "Derby"
STAFFORD = "Stafford"
BURTON_UPON_TRENT = "Burton-Upon-Trent"
BEER1 = "beer1"
TAMWORTH = "Tamworth"
WALSALL = "Walsall"
DUDLEY = "Dudley"
WORCESTER = "Worcester"
COALBROOKDALE = "Coalbrookdale"
WOLVERHAMPTON = "Wolverhampton"
KIDDERMINSTER = "Kidderminster"
BEER2 = "beer2"
BIRMINGHAM = "Birmingham"
NUNEATON = "Nuneaton"
COVENTRY = "Coventry"
REDDITCH = "Redditch"


class LocationCard(Card):
    def __init__(self, name: CardName, isWild=False):
        super(LocationCard, self).__init__(CardType.location, name=name)
        self.isWild = isWild
        self.isWild = name == CardName.wild_location
        self.name = name

    def getColor(self):
        if self.name in [STOKE_ON_TRENT, LEEK, STONE, UTTOXETER]:
            return Colours.Blue
        elif self.name in [BELPER, DERBY]:
            return Colours.Green
        elif self.name in [
            STAFFORD,
            CANNOCK,
            WALSALL,
            BURTON_UPON_TRENT,
            TAMWORTH,
        ]:
            return Colours.Red
        elif self.name in [NUNEATON, BIRMINGHAM, COVENTRY, REDDITCH]:
            return Colours.Purple
        else:
            return Colours.Yellow

    def __str__(self) -> str:
        if self.isWild:
            return self.name.value

        if self.name in [STOKE_ON_TRENT, LEEK, STONE, UTTOXETER]:
            return prCyan(self.name)
        elif self.name in [BELPER, DERBY]:
            return prGreen(self.name)
        elif self.name in [
            STAFFORD,
            CANNOCK,
            WALSALL,
            BURTON_UPON_TRENT,
            TAMWORTH,
        ]:
            return prRed(self.name)
        elif self.name in [
            WOLVERHAMPTON,
            COALBROOKDALE,
            DUDLEY,
            KIDDERMINSTER,
            WORCESTER,
        ]:
            return prYellow(self.name)
        elif self.name in [NUNEATON, BIRMINGHAM, COVENTRY, REDDITCH]:
            return prPurple(self.name)
        elif self.name == BEER1 or self.name == BEER2:
            return prLightGray(self.name)
        return self.name.value

    def __repr__(self) -> str:
        return str(self)
