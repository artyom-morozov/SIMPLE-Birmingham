
from copy import copy
import math
import pygame
import os
import sys

from classes.game import Game as GameModule
from classes.board import Board
from classes.buildings.building import Building
from classes.buildings.market_building import MarketBuilding
from classes.cards.industry_card import IndustryCard
from classes.cards.location_card import LocationCard
from classes.enums import ActionTypes, GameState
from classes.town import Town
from classes.player import Player
from classes.build_location import BuildLocation
from classes.buildings.enums import BuildingName
from scipy.spatial.distance import pdist, squareform
from classes.ui.sftext.sftext import SFText
from consts import  STARTING_CARDS 
from tkinter import messagebox, Tk
import numpy as np

WIDTH = 1200
HEIGHT = 1200
WHITE = (255,255,255)
RED = (255,0,0)
GREEN = (0,255,0)
BLACK = (0,0,0)
YELLOW = (255, 255, 0)
ORANGE = (255, 153, 51)
BLUE = (87,155,252)
GREY = (100, 100, 100)
TAN = (229, 156, 91)
PURPLE = (92, 6, 186)

BEER_SIZE = 12

def printRoman(num):
    # Storing roman values of digits from 0-9
    # when placed at different places
    m = ["", "M", "MM", "MMM"]
    c = ["", "C", "CC", "CCC", "CD", "D",
         "DC", "DCC", "DCCC", "CM "]
    x = ["", "X", "XX", "XXX", "XL", "L",
         "LX", "LXX", "LXXX", "XC"]
    i = ["", "I", "II", "III", "IV", "V",
         "VI", "VII", "VIII", "IX"]
 
    # Converting to roman
    thousands = m[num // 1000]
    hundreds = c[(num % 1000) // 100]
    tens = x[(num % 100) // 10]
    ones = i[num % 10]
 
    ans = (thousands + hundreds +
           tens + ones)
 
    return ans

PLAYER_COLOR_MAP = {
	"Red": RED,
	"Blue": BLUE,
	"Green": GREEN,
	"Yellow": YELLOW,
    "Purple": PURPLE
}

#flipped building colors
PLAYER_BUILDING_RETIRED_COLOR_MAP = {
	"Red": (84, 0, 0),
	"Blue": (0, 0, 84),
	"Green": (4, 84, 0),
	"Yellow": (85, 72, 0)
}

MARGIN = 50

BUILDING_COORDS = {'Leek': [[632, 92], [687, 92]], 'Stoke-On-Trent': [[492, 125], [467, 177], [522, 177]], 'Stone': [[342, 302], [397, 302]], 'Uttoxeter': [[647, 282], [702, 282]], 'Belper': [[847, 127], [902, 127], [957, 127]], 'Derby': [[905, 255], [877, 307], [932, 307]], 'Stafford': [[452, 412], [507, 412]], 'Burton-Upon-Trent': [[787, 447], [842, 447]], 'beer1': [[357, 522]], 'Cannock': [[537, 532], [592, 532]], 'Tamworth': [[802, 597], [857, 597]], 'Walsall': [[607, 672], [662, 672]], 'Coalbrookdale': [[282, 637], [252, 697], [307, 697]], 'Wolverhampton': [[417, 642], [472, 642]], 'Dudley': [[472, 787], [527, 787]], 'Kidderminster': [[387, 912], [442, 912]], 'beer2': [[292, 997]], 'Worcester': [[402, 1062], [457, 1062]], 'Birmingham': [[722, 777], [777, 777], [722, 832], [777, 832]], 'Nuneaton': [[912, 712], [967, 712]], 'Coventry': [[967, 812], [937, 872], [992, 872]], 'Redditch': [[667, 972], [722, 972]]}

TRADE_POST_COORDS = {
	"Warrington": [
		[275, 132],
		[332, 132]
	],
	"Nottingham": [
		[1031, 204],
		[1090, 204]
	],
	"Shrewbury": [
		[77, 697]
	],
	"Oxford": [
		[934, 1009],
		[991, 1009]
	],
	"Gloucester": [
		[673, 1098],
		[723, 1098]
	],
}

BEER_COORDS = {
	"Warrington": [
		(290, 205),
		(369, 206)
	],
	"Nottingham": [
		(1049, 271),
		(1125, 275)
	],
	"Shrewbury": [
		(150, 713)
	],
	"Oxford": [
		(946, 986),
		(1023, 987),
	],
	"Gloucester": [
		(682, 1073),
		(765, 1072),
	],
}

ROAD_LOCATION_COORDS = [
	[422, 120], 	#[WARRINGTON, STOKE_ON_TRENT]
	[564, 107], 	#[STOKE_ON_TRENT, LEEK]
	[770, 92], 		#[LEEK, BELPER], False
	[918, 206], 	#[BELPER, DERBY]
	[980, 253], 	#[DERBY, NOTTINGHAM]
	[792, 305], 	#[DERBY, UTTOXETER], False
	[899, 401], 	#[DERBY, BURTON_UPON_TRENT]
	[444, 256], 	#[STOKE_ON_TRENT, STONE]
	[519, 293], 	#[STONE, UTTOXETER], False
	[383, 402], 	#[STONE, STAFFORD]
	[622, 359], 	#[STONE, BURTON_UPON_TRENT]
	[569, 469], 	#[STAFFORD, CANNOCK]
	[686, 477], 	#[CANNOCK, BURTON_UPON_TRENT], False
	[836, 527], 	#[TAMWORTH, BURTON_UPON_TRENT]
	[703, 562], 	#[WALSALL, BURTON_UPON_TRENT], canBuildRailroad=False
	[462, 520], 	#[BEER1, CANNOCK]
	[478, 577], 	#[WOLVERHAMPTON, CANNOCK]
	[645, 597], 	#[WALSALL, CANNOCK]
	[353, 644], 	#[WOLVERHAMPTON, COALBROOKDALE]
	[203, 644], 	#[SHREWBURY, COALBROOKDALE]
	[319, 827], 	#[KIDDERMINSTER, COALBROOKDALE]
	[428, 849], 	#[KIDDERMINSTER, DUDLEY]
	[545, 654], 	#[WOLVERHAMPTON, WALSALL]
	[450, 730], 	#[WOLVERHAMPTON, DUDLEY]
	[743, 661], 	#[TAMWORTH, WALSALL], False
	[930, 630], 	#[TAMWORTH, NUNEATON]
	[1025, 780], 	#[NUNEATON, COVENTRY]
	[663, 759], 	#[BIRMINGHAM, WALSALL]
	[834, 699], 	#[BIRMINGHAM, TAMWORTH]
	[856, 763], 	#[BIRMINGHAM, NUNEATON], False
	[858, 861], 	#[BIRMINGHAM, COVENTRY]
	[856, 916], 	#[BIRMINGHAM, OXFORD]
	[735, 913], 	#[BIRMINGHAM, REDDITCH], False
	[577, 948], 	#[BIRMINGHAM, WORCESTER]
	[610, 803], 	#[BIRMINGHAM, DUDLEY]
	[797, 994], 	#[REDDITCH, OXFORD]
	[604, 1025], 	#[REDDITCH, GLOUCESTER]
	[526, 1101], 	#[WORCESTER, GLOUCESTER]
	[407, 996], 	#[WORCESTER, BEER2, KIDDERMINSTER]
]

DECK_POSITION = (170, 190)
CARD_WIDTH = 130
CARD_HEIGHT = 180


ACTIONS ={
    "UNDO": (1105, 1248),
    "ROAD": (1260, 1190),
    "BUILD": (1180, 1212),
    "DEVELOP": (1342, 1185),
    "SELL": (1425, 1182),
    "LOAN": (1508, 1193),
    "SCOUT": (1593, 1210),
    "PASS": (1667, 1249)
}




PLAYER_POSITIONS = [
    (128, 806),
    (128, 806 + 98),
    (128, 806 + 98 * 2),
    (128, 806 + 98 * 3)
]
    


INDUSTRY_MAT_POSITIONS = {
    BuildingName.beer: {
        "1": (1216, 417),
        "2": (1216, 358),
        "3": (1216, 299),
        "4": (1216, 240)
    },
    BuildingName.goods: {
        "1": (1216, 151),
        "2": (1216, 92),
        "3": (1216, 33),
        "4": (1310, 33),
        "5": (1407, 33),
        "6": (1498, 33),
        "7": (1593, 33),
        "8": (1690, 33),
    },
    BuildingName.cotton: {
        "1": (1338, 318),
        "2": (1338, 260),
        "3": (1338, 201),
        "4": (1338, 142),
    },
    BuildingName.pottery: {
        "1": (1464, 318),
        "2": (1464, 260),
        "3": (1464, 201),
        "4": (1464, 142),
        "5": (1555, 142),
    },
    BuildingName.coal: {
        "1": (1369, 421),
        "2": (1464, 421),
        "3": (1559, 421),
        "4": (1654, 421),
    },
    BuildingName.iron: {
        "1": (1589, 318),
        "2": (1686, 318),
        "3": (1686, 257),
        "4": (1686, 197),
    }


}

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sftext/'))
class Display:
    def __init__(self, game: GameModule =None, env=None, interactive=False, debug_mode=False, policies=None, test=False):
        if game is None:
            if env is None:
                raise RuntimeError("Need to provide display with either game or env")
            self.env = env
        else:
            self.env = env
            self.game: GameModule = game
        self.interactive = interactive
        self.debug_mode = debug_mode

        self.policies = policies

        if self.debug_mode:
            screen_width, screen_height = 2200, 1100
        else:
            screen_width, screen_height = 1735, 1300

        

        
        pygame.init()
        pygame.font.init()
        self.font = pygame.font.Font(None, 24)
        self.top_menu_font = pygame.font.SysFont('Arial', 45)
        self.count_font = pygame.font.SysFont('Arial', 18)
        self.thinking_font = pygame.font.SysFont('Arial', 36)
        # self.construct_outer_board_polygon()
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Brass Birmingham RL environment")
        self.BACKGROUND_COLOUR = (25, 105, 158)

        local_dir = os.path.dirname(__file__)
        self.img = pygame.image.load(f'{local_dir}/render/board.jpg')
        self.goldCard = pygame.image.load(f"{local_dir}/render/gold-card.png")
        self.greyCard = pygame.image.load(f"{local_dir}/render/grey-card.png")


        self.greyCard = pygame.transform.scale(self.greyCard, (CARD_WIDTH, CARD_HEIGHT))
        self.goldCard = pygame.transform.scale(self.goldCard, (CARD_WIDTH, CARD_HEIGHT))
        self.greyCard = pygame.transform.rotate(self.greyCard, 90)
        self.goldCard = pygame.transform.rotate(self.goldCard, 90)
        self.merchantImages = {}
        for tileName in self.game.board.merchantTiles:
            self.merchantImages[tileName] = pygame.transform.scale(pygame.image.load(f"{local_dir}/images/trade_posts/merchants/merchant_{tileName.value}.png"), (48, 50))


        self.locationCardsImg = {}
        self.industryCardsImg = {}
        self.colourMapCards = {}

        self.wildIndustryImg = pygame.transform.scale(pygame.image.load(f"{local_dir}/images/wild_cards/wild_industry.png"), (CARD_WIDTH, CARD_HEIGHT))
        self.wildLocationImg = pygame.transform.scale(pygame.image.load(f"{local_dir}/images/wild_cards/wild_location.png"), (CARD_WIDTH, CARD_HEIGHT))

        self.action_menu_img = pygame.image.load(f"{local_dir}/images/components/actionMenu.png")

        for card in STARTING_CARDS[str(self.game.num_players)]:
            if isinstance(card, LocationCard):
                colour = card.getColor()
                self.locationCardsImg[colour] = pygame.transform.scale(pygame.image.load(f"{local_dir}/images/location_cards/{colour.value}_card.png"), (CARD_WIDTH, CARD_HEIGHT))
            elif isinstance(card, IndustryCard):
                self.industryCardsImg[card.name] = pygame.transform.scale(pygame.image.load(f"{local_dir}/images/industry_cards/{card.name.value}.png"), (CARD_WIDTH, CARD_HEIGHT))


        self.buildingImgs = {}
        for buildingName in BuildingName:
             self.buildingImgs[buildingName] = pygame.image.load(f"{local_dir}/images/buildings/{buildingName.value}.png")

        self.industryMatImg = pygame.image.load(f"{local_dir}/images/components/industrymat.png")
        
        
        # set build location coords
        self.buildLocationCoords = {}
        for town in self.game.board.towns:
            for i, buildLocation in enumerate(town.buildLocations):
                self.buildLocationCoords[buildLocation.id] = BUILDING_COORDS[town.name][i]

        
        self.game_log = ""
        self.game_log_target_rect = pygame.Rect(1140, 335, 560, 120)
        self.game_log_surface = pygame.Surface(self.game_log_target_rect.size)
        self.game_log_sftext = SFText(text=self.game_log, surface=self.game_log_surface,
                                      font_path=os.path.join(os.path.dirname(__file__), "sftext/example/resources"))

        self.selected_card = None
       
        self.screen.fill(self.BACKGROUND_COLOUR)

        self.reset()

        if self.interactive:
            self.run_event_loop(test=test)
    
    def drawMoney(self):
        x = 10
        y = 10
        rect = pygame.Rect(5, 5, 130, 100)
        pygame.draw.rect(self.screen, WHITE, rect)

        round_info = f"{self.game.turn}/{self.game.max_turns}"
        card_info = f"{len(self.game.board.deck)}/{len(STARTING_CARDS[str(self.game.num_players)])}"
        wild_card_info = f"{len(self.game.board.wildIndustryCards) + len(self.game.board.wildlocationCards)}/{self.game.num_players*2}"

        
        for info, value in zip(['Round', 'Cards', 'Wild Cards', 'Era'], [round_info, card_info, wild_card_info, self.game.board.era]):
            info_text = self.font.render(f"{info}: {value}", True,  BLACK)
            self.screen.blit(info_text, (x, y))
            y += 20
    
    def drawPlayers(self):
        for i, player in reversed(list(enumerate(self.game.board.players))):
            x, y = PLAYER_POSITIONS[i]

            left = 0
            top = y - 50

            rect = pygame.Rect(left, top, 170, 105)
            pygame.draw.rect(self.screen, WHITE, rect)

            text_y = top + 5

            name_text = self.font.render(f"{player.name}", True,  PLAYER_COLOR_MAP[player.color])
            vps = self.font.render(f"VPs: {player.victoryPoints}", True, PLAYER_COLOR_MAP[player.color])
            income = self.font.render(f"Income: {player.incomeLevel()}", True, PLAYER_COLOR_MAP[player.color])
            money = self.font.render(f"Money: {player.money}", True, PLAYER_COLOR_MAP[player.color])
            spending = self.font.render(f"Spent This Turn: {player.spentThisTurn}", True, PLAYER_COLOR_MAP[player.color])

            for text in [name_text, vps, income, money, spending]:
                self.screen.blit(text, (left + 10, text_y))
                text_y += 20

            # draw border if the player is active
            if player == self.game.get_active_player():
                pygame.draw.rect(self.screen, PLAYER_COLOR_MAP[player.color], rect, 3)
    
    def draw_player_industry_mat(self, mouse_click, mouse_pos):
        player: Player = self.game.get_active_player()

        # Determine the position for the action menu based on the screen size and image dimensions
        mat_width, mat_height = self.industryMatImg.get_size()
        screen_width, screen_height = self.screen.get_size()
        menu_x = screen_width - mat_width   # 10 pixels padding from the right edge
        menu_y = 0  # 10 pixels padding from the bottom edge

        # Render the action menu image at the calculated position
        self.screen.blit(self.industryMatImg, (menu_x, menu_y))
        
        
        # for name in INDUSTRY_MAT_POSITIONS:
        #     for level, coords in INDUSTRY_MAT_POSITIONS[name].items():
        #         x, y = coords
        #         img_rect = pygame.Rect(x - 25, y - 25, 50, 50)
        #         pygame.draw.rect(self.screen, PLAYER_COLOR_MAP[player.color], img_rect)
        #         lvl_text = self.font.render(f"{level}", True, BLACK)
        #         self.screen.blit(lvl_text, coords)



        # Draw action circles
        # for action, (x, y) in ACTIONS.items():
        #         pygame.draw.circle(self.screen, TAN, (x, y), 30)
        
        


        # start_x = self.screen.get_width() - 300  # Adjust as needed
        # start_y = 50  # Starting y position
        # square_size = 40  # Size of the square for each building
        # y_offset = 10  # Space between each building entry

       

        for industry_name, buildings in player.industryMat.items():
            num_buildings = 0

            for i in range(len(buildings)):
                building: Building = buildings[i]

               
                
                num_buildings += 1

                if i < len(buildings)-1 and buildings[i+1].tier == building.tier:
                    continue
                
               
                x, y = INDUSTRY_MAT_POSITIONS[building.name][str(building.tier)]
               

                # Draw the square
                img_rect = pygame.Rect(x - 25, y - 25, 50, 50)
                pygame.draw.rect(self.screen, PLAYER_COLOR_MAP[player.color], img_rect)
                
                # lvl_text = self.font.render(f"{level}", True, BLACK)
                # self.screen.blit(lvl_text, coords)

                # Draw the building image
                building_img = pygame.transform.scale(self.buildingImgs[building.name], (30, 30))
                img_width, img_height = building_img.get_size()
                img_x = x - 15
                img_y = y - 15
                self.screen.blit(building_img, (img_x, img_y))
                
                
                num_text = self.font.render(f"{num_buildings}", True, BLACK)
                self.screen.blit(num_text, (x-20, y-20))        


                if isinstance(building, MarketBuilding) and building.beerCost > 0:
                    beer_text = self.font.render(f"{building.beerCost}", True, ORANGE)
                    self.screen.blit(beer_text, (x+15, y-20))   
                
                num_buildings = 0


                # Render Resources 

                # # Display costs on the left of the square
                # iron_cost_text = self.font.render(str(building.ironCost), True, WHITE)
                # coal_cost_text = self.font.render(str(building.coalCost), True, WHITE)
                # money_cost_text = self.font.render(str(building.cost), True, WHITE)
                # self.screen.blit(iron_cost_text, (square_x - 60, square_y))
                # self.screen.blit(coal_cost_text, (square_x - 60, square_y + 15))
                # self.screen.blit(money_cost_text, (square_x - 60, square_y + 30))

                # # Display benefits on the right of the square
                # vps_text = self.font.render(f"VPs: {building.victoryPointsGained}", True, WHITE)
                # income_text = self.font.render(f"Inc: {building.incomeGained}", True, WHITE)
                # self.screen.blit(vps_text, (square_x + square_size + 5, square_y))
                # self.screen.blit(income_text, (square_x + square_size + 5, square_y + 15))

                # # Adjust the y position for the next building
                # current_y += square_size + y_offset
                # # Adjust start_y for the next industry type
                # start_y = current_y + 20  # Add some extra space between different industry types

        # Check if there was a mouse click and if it was within the bounds of the action menu
        


    def drawTradingPostBeer(self):
        for trade in self.game.board.tradePosts:
            for i, merchant in enumerate(trade.merchantTiles):
                coords = BEER_COORDS[trade.name][i]
                if merchant.hasBeer:
                    pygame.draw.circle(self.screen, TAN, coords, BEER_SIZE)


    def drawMerchantTiles(self):
        for trade in self.game.board.tradePosts:
            for i, merchant in enumerate(trade.merchantTiles):
                x, y = TRADE_POST_COORDS[trade.name][i]
                # rect = pygame.Rect(x, y, 30, 30)
                # pygame.draw.rect(self.screen, BLUE, rect)
                # img = self.font.render(f"{merchant.name.value}", True, WHITE)
                self.screen.blit(self.merchantImages[merchant.name], (x, y))

    def drawRoads(self):
        for i, road in enumerate(self.game.board.roadLocations):
            if road.isBuilt:
                coords = ROAD_LOCATION_COORDS[i]
                x, y = coords

                pygame.draw.circle(self.screen, PLAYER_COLOR_MAP[road.road.owner.color], coords, 10)
                # if i % 2 == 0:
                # 	img = self.font.render(f"{road.towns[0].name}, {road.towns[1].name}", True, WHITE)
                # else:
                # 	img = self.font.render(f"{road.towns[0].name}, {road.towns[1].name}", True, RED)
                # self.screen.blit(img, (x, y))

    def drawBuildings(self):
        for town in self.game.board.towns:
            for buildLocation in town.buildLocations:
                if buildLocation.building:
                    self.drawBuilding(buildLocation)

    #draw BUILT 
    def drawBuilding(self, buildLocation: BuildLocation):
        # print(f"{buildLocation.id=}")
        x, y = None, None
        coords = BUILDING_COORDS[buildLocation.town.name]
        for i, location in enumerate(buildLocation.town.buildLocations):
            if buildLocation.id == location.id:
                x, y = coords[i]

        # Define the building image and rect for it
        building = buildLocation.building
        if building is None or not building.isActive:
            return

        building_img = pygame.transform.scale(self.buildingImgs[building.name], (30, 30))
        img_width, img_height = building_img.get_size()
        img_x = x - 15
        img_y = y - 15
        
        
        lvl_text = self.font.render(f"{printRoman(building.tier)}", True, BLACK)


        img_rect = pygame.Rect(x - 22, y - 22, 50, 50)  # Adjust as needed for your images

        
        pygame.draw.rect(self.screen, PLAYER_COLOR_MAP[buildLocation.building.owner.color], img_rect)
        # Draw background color based on whether the building is flipped
        if buildLocation.building.isFlipped:
            black_rect = pygame.Rect(x - 22, y - 22, 50, 25)  
            pygame.draw.rect(self.screen, BLACK, black_rect)

        # render image and level text
        self.screen.blit(building_img, (img_x, img_y))  # Adjust as needed
        self.screen.blit(lvl_text, (x+17, y+12))            


    def drawCoal(self):
        for i in range(self.game.board.coalMarketRemaining):
            x = 1000
            if i % 2 == 0:
                x += 25
            y = 385 + (i//2*35.5)
            rect = pygame.Rect(x, y, 15, 15)
            pygame.draw.rect(self.screen, BLACK, rect)
        img = self.font.render(f"{self.game.board.coalMarketRemaining}", True, BLACK)
        self.screen.blit(img, (1000, 330))

    def drawIron(self):
        for i in range(self.game.board.ironMarketRemaining):
            x = 1065
            if i % 2 == 0:
                x += 25
            y = 458 + (i//2*35.5)
            rect = pygame.Rect(x, y, 15, 15)
            pygame.draw.rect(self.screen, ORANGE, rect)
        img = self.font.render(f"{self.game.board.ironMarketRemaining}", True, ORANGE)
        self.screen.blit(img, (1100, 400))

    def drawDeck(self):
        x, y = DECK_POSITION
        for i in range(len(self.game.board.deck.cards)):
            self.screen.blit(self.greyCard, (x-(i*.5)-90, y-(i*.5)-70))
            # pygame.draw.circle(self.screen, WHITE, (x, y), 5)
    def drawActionMenu(self, mouse_click, mouse_pos):
         # Determine the position for the action menu based on the screen size and image dimensions
        menu_width, menu_height = self.action_menu_img.get_size()
        screen_width, screen_height = self.screen.get_size()
        menu_x = screen_width - menu_width + 120  # 10 pixels padding from the right edge
        menu_y = screen_height - menu_height - 10  # 10 pixels padding from the bottom edge

        # Render the action menu image at the calculated position
        self.screen.blit(self.action_menu_img, (menu_x, menu_y))
        
        # Draw action circles
        # for action, (x, y) in ACTIONS.items():
        #         pygame.draw.circle(self.screen, TAN, (x, y), 30)
        
        # Check if there was a mouse click and if it was within the bounds of the action menu
        if mouse_click:
            # print(f"Pos ", mouse_pos)
            for action, (x, y) in ACTIONS.items():
                dist = ((mouse_pos[0] - x) ** 2 + (mouse_pos[1] - y) ** 2) ** 0.5
                if dist <= 30:  # Assuming the action buttons have a radius of 68 pixels
                    self.handle_action(action=action)
                    break  # Stop checking after the first match to avoid multiple actions being triggered

    def drawHand(self, mouse_click, mouse_pos):

        active_player: Player = self.game.get_active_player()   
        card_offset_x = 50  # Initial X offset from left; adjust as needed
        card_offset_y = self.screen.get_height() - (CARD_HEIGHT // 2)   # Adjust Y to bottom
        card_spacing = CARD_WIDTH - 30  # Overlap cards; adjust as needed

        mouse_x, mouse_y = pygame.mouse.get_pos()
        for i, card in enumerate(active_player.hand.cards):

            cardUsed = False
            # display possible card choices
            if self.game_state == GameState.CARD_CHOICE and self.current_action['building'] and self.current_action['buildLocation'] and active_player.canUseCardForBuilding(building=self.current_action['building'], buildLocation=self.current_action['buildLocation'], card=card):
                # print(f"Can use card {card.name} with id {card.id} for building {self.current_action['building'].name} in {self.current_action['buildLocation'].town.name}", end=' ')
                # if isinstance(card, IndustryCard):
                #     print(f"because it has the following possible builds {self.current_action['buildLocation'].possibleBuilds}", end=' ' )
                # print()
                card_offset_y = self.screen.get_height() - math.ceil(CARD_HEIGHT * 0.75) 
                cardUsed = True
            else:
                card_offset_y = self.screen.get_height() - (CARD_HEIGHT // 2)
            # print(i+1, ' Card - ', card)
            
            
            card_rect = pygame.Rect(card_offset_x + i * card_spacing, card_offset_y, CARD_WIDTH, CARD_HEIGHT)
            
            
            # Draw the card image based on card type
            if isinstance(card, LocationCard):

                # Use specific color image for LocationCards
                card_image = self.locationCardsImg[card.getColor()] if not card.isWild else self.wildLocationImg
                self.screen.blit(card_image, card_rect.topleft)
                
                if not card.isWild:
                    # Draw card name
                    name_text = self.font.render(card.name.upper(), True, WHITE)
                    text_rect = name_text.get_rect(center=(card_rect.x + CARD_WIDTH // 2, card_rect.y + 10))
                    # pygame.draw.rect(self.screen, PLAYER_COLOR_MAP[card.getColor().name], card_rect)
                    self.screen.blit(name_text, text_rect)
            elif isinstance(card, IndustryCard):
                # Use pre-loaded image for IndustryCards
                card_image = self.industryCardsImg[card.name] if not card.isWild else self.wildLocationImg
                self.screen.blit(card_image, card_rect.topleft)
                # pygame.draw.rect(self.screen, BLACK, card_rect)

            # Check for mouse hover to raise the card
            if card_rect.collidepoint(mouse_x, mouse_y):
                # Adjust card_rect's y-coordinate to raise the card
                raised_rect = card_rect.copy()
                raised_rect.y -= 20  # Raise by 20 pixels; adjust as needed
                self.screen.blit(card_image, raised_rect.topleft)
                # Redraw the name for LocationCards to ensure visibility
                if isinstance(card, LocationCard):
                    self.screen.blit(name_text, (raised_rect.x + (CARD_WIDTH - text_rect.width) // 2, raised_rect.y + 10))
            # Check for mouse click on this card
            if mouse_click and card_rect.collidepoint(mouse_pos) and self.game_state == GameState.CARD_CHOICE:
                # print(f'Clicked on card: {card.name} of type {type(card).__name__} and id {card.id}')
                if cardUsed:
                    self.current_action['card'] = card

    def drawResourcesOnBuildings(self):
        for building in self.game.board.getCoalBuildings():
            coords = BUILDING_COORDS[building.town.name]
            for i, location in enumerate(building.town.buildLocations):
                if building.buildLocation.id == location.id:
                    x, y = coords[i]
                
            startX = x

            assert building.resourcesType.name == "coal"
            for i in range(building.resourceAmount):
                if i > 0 and i % 3 == 0:
                    y += 30
                x = startX + (i % 3) * 18

                # y += i//2*18
                rect = pygame.Rect(x-23, y-23, 15, 15)
                pygame.draw.rect(self.screen, BLACK, rect)

        for building in self.game.board.getIronBuildings():
            coords = BUILDING_COORDS[building.town.name]
            for i, location in enumerate(building.town.buildLocations):
                if building.buildLocation.id == location.id:
                    x, y = coords[i]
                
            startX = x

        
            assert building.resourcesType.name == "iron"
            for i in range(building.resourceAmount):
                if i > 0 and i % 3 == 0:
                    y += 30
                x = startX + (i % 3) * 18

                # y += i//2*18
                rect = pygame.Rect(x-23, y-23, 15, 15)
                pygame.draw.rect(self.screen, ORANGE, rect)

        for building in self.game.board.getBeerBuildings():
            coords = BUILDING_COORDS[building.town.name]
            for i, location in enumerate(building.town.buildLocations):
                if building.buildLocation.id == location.id:
                    x, y = coords[i]
                
            startX = x

            assert building.resourcesType.name == "beer"
            for i in range(building.resourceAmount):
                if i > 0 and i % 3 == 0:
                    y += 30
                x = startX + (i % 3) * 18

                # y += i//2*18
                pygame.draw.circle(self.screen, TAN, (x+10, y+10), BEER_SIZE)


    def reset(self):
        self.current_action = {}
        self.active_other_player = []
        self.active_receive_res = []
        self.active_trade_res = []
        self.active_harbour = []
        self.active_harbour_receive_res = []
        self.active_harbour_trade_res = []
        self.active_development_res_boxes = []
        self.game_log_sftext.text = ""
        self.game_log_sftext.parse_text()
        self.message_count = 0
        self.game_state = GameState.NO_SELECTION

    def update_game_log(self, message):
        self.message_count += 1
        color = self.road_colours[message["player_id"]]
        message_to_add = "{style}{color "+str(color)+"}"+str(self.message_count) + ". " + message["text"] + "\n"
        self.game_log_sftext.text = message_to_add + self.game_log_sftext.text
        self.game_log_sftext.parse_text()

    

    def handle_action(self, action):
        print(f"Action {action} clicked.")
        if not self.game_state == GameState.NO_SELECTION:
            return
        


        if action == "BUILD":
            self.game_state = GameState.TOWN_CHOICE
            self.current_action = {
                'type': ActionTypes.BuildIndustry,
            }

    def apply_action(self, player: Player):
        if not self.current_action:
            return
        
        if self.current_action['type'] == ActionTypes.BuildIndustry:
            if not self.current_action['building'] or not self.current_action['buildLocation']:
                return
            player.buildBuilding(self.current_action['building'].name, self.current_action['buildLocation'], self.current_action['card'])
            same_player = self.game.next_action(self.current_action)
            if same_player:
                self.game_state = GameState.SECOND_ACTION
            else:
                self.game_state = GameState.NO_SELECTION

    # def construct_outer_board_polygon(self):
    #     base_positions = np.array([self.scaled_corner_pos[corner.id] for corner in self.game.board.corners \
    #                           if corner.adjacent_tiles_placed < 3])
    #     dists = squareform(pdist(base_positions))
    #     positions = []
    #     positions_added = []
    #     curr_pos_ind = 0
    #     while len(positions) != len(base_positions):
    #         positions.append(base_positions[curr_pos_ind])
    #         positions_added.append(curr_pos_ind)
    #         min_dist = np.inf
    #         min_dist_ind = -1
    #         for i in range(len(base_positions)):
    #             if i != curr_pos_ind and i not in positions_added:
    #                 if dists[curr_pos_ind, i] < min_dist:
    #                     min_dist_ind = i
    #                     min_dist = dists[curr_pos_ind, i]
    #         if min_dist_ind != -1:
    #             curr_pos_ind = min_dist_ind
    #     for i in range(len(positions)):
    #         positions[i][0] = positions[i][0] - 1.5*(self.outer_hexagon_width - self.hexagon_width)
    #         positions[i][1] = positions[i][1] - 2*(self.outer_hexagon_height - self.hexagon_height)
    #     self.outer_board_polygon = positions
    
    def render(self):
        self.screen.fill(self.BACKGROUND_COLOUR)
        self.render_board()
        pygame.display.update()
        self.game_log_sftext.post_update()
        pygame.event.pump()
    
    def render_board(self, mouse_click=False, mouse_pos=(0, 0)):
        self.screen.blit(self.img, (0, 0))
        self.drawCoal()
        self.drawIron()
        self.drawMerchantTiles()
        self.drawRoads()
        self.drawDeck()
        self.drawBuildings()
        self.drawTradingPostBeer()
        self.drawMoney()
        self.drawResourcesOnBuildings()
        self.drawPlayers()
        self.drawHand(mouse_click=mouse_click, mouse_pos=mouse_pos)
        self.drawActionMenu(mouse_click=mouse_click, mouse_pos=mouse_pos)
        self.draw_player_industry_mat(mouse_click=mouse_click, mouse_pos=mouse_pos)
        pygame.display.update()
    
    


    def run_event_loop(self, test=False):
        run = True
        mouse_click = False
        mouse_pos = (0, 0)  # Initialize mouse_pos

        active_player: Player = self.game.get_active_player()
        builds, firstBuildings, availableBuildLocations = active_player.getAvailableBuilds()

        turn = self.game.turn 

        next_action = False
        while run:
            pygame.time.delay(150)
            Tk().wm_withdraw()  # Hide the main tkinter window

            # Reset mouse_click at the beginning of each loop iteration
            mouse_click = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False
                elif event.type == pygame.MOUSEBUTTONUP:
                    mouse_click = True
                    mouse_pos = pygame.mouse.get_pos()  # Update mouse_pos on click
                    print(f"Mouse click at {mouse_pos}")

            


            self.screen.fill(self.BACKGROUND_COLOUR)
            # Pass mouse_click and mouse_pos to render_board
            self.render_board(mouse_click=mouse_click, mouse_pos=mouse_pos)
            
            # display info for diff player
            if next_action or self.game_state or self.game.get_active_player().id != active_player.id or self.game.turn != turn:
                active_player: Player = self.game.get_active_player()
                builds, firstBuildings, availableBuildLocations = active_player.getAvailableBuilds()
                next_action = False
            
            
            if self.game_state == GameState.TOWN_CHOICE:
                for bl in availableBuildLocations:
                    x, y = self.buildLocationCoords[bl.id]
                    blRect = pygame.Rect(x - 24, y - 24, 52, 52)
                    pygame.draw.rect(self.screen, GREEN, blRect, 3, 1)
                    if mouse_click and blRect.collidepoint(mouse_pos[0], mouse_pos[1]):
                        self.current_action['buildLocation']: BuildLocation = bl
                        self.game_state = GameState.BUILDING_CHOICE
            elif self.game_state == GameState.BUILDING_CHOICE and self.current_action['buildLocation']:
                buildLocation: BuildLocation = self.current_action['buildLocation']
                for building in firstBuildings:
                    if not building.name in buildLocation.possibleBuilds:
                        continue
                    x, y = INDUSTRY_MAT_POSITIONS[building.name][str(building.tier)]
               
                    # Draw the square
                    building_selection_rect = pygame.Rect(x - 25, y - 25, 50, 50)
                    pygame.draw.rect(self.screen, GREEN, building_selection_rect, 3, 1)
                    if mouse_click and building_selection_rect.collidepoint(mouse_pos[0], mouse_pos[1]):
                        self.current_action['building'] = building
                        self.game_state = GameState.CARD_CHOICE
            elif self.game_state == GameState.CARD_CHOICE and 'card' in self.current_action:
                print(f"Should apply action now")
                print(f"{self.current_action}")
                self.apply_action(active_player)
                next_action = True

            pygame.display.update()
            self.game_log_sftext.post_update()
            pygame.event.pump()