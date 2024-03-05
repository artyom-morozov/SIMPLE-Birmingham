
from copy import copy
import pygame
import os
import sys
from classes.board import Board
from classes.cards.industry_card import IndustryCard
from classes.cards.location_card import LocationCard
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



sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sftext/'))
class Display:
    def __init__(self, game=None, env=None, interactive=False, debug_mode=False, policies=None, test=False):
        if game is None:
            if env is None:
                raise RuntimeError("Need to provide display with either game or env")
            self.env = env
        else:
            self.env = env
            self.game = game
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
        for card in STARTING_CARDS[str(self.game.num_players)]:
            if isinstance(card, LocationCard):
                colour = card.getColor()
                self.locationCardsImg[colour] = pygame.transform.scale(pygame.image.load(f"{local_dir}/images/location_cards/{colour.value}_card.png"), (CARD_WIDTH, CARD_HEIGHT))
            elif isinstance(card, IndustryCard):
                self.industryCardsImg[card.name] = pygame.transform.scale(pygame.image.load(f"{local_dir}/images/industry_cards/{card.name.value}.png"), (CARD_WIDTH, CARD_HEIGHT))




 
        self.game_log = ""
        self.game_log_target_rect = pygame.Rect(1140, 335, 560, 120)
        self.game_log_surface = pygame.Surface(self.game_log_target_rect.size)
        self.game_log_sftext = SFText(text=self.game_log, surface=self.game_log_surface,
                                      font_path=os.path.join(os.path.dirname(__file__), "sftext/example/resources"))


        self.screen.fill(self.BACKGROUND_COLOUR)

        self.reset()

        if self.interactive:
            self.run_event_loop(test=test)
    def drawMoney(self):
        x = 10
        y = 10
        rect = pygame.Rect(5, 5, 100, 100)
        pygame.draw.rect(self.screen, WHITE, rect)
        for player in self.game.board.players:
            img =self.font.render(f"{player.name}: ${player.money}", True,  PLAYER_COLOR_MAP[player.color])
            self.screen.blit(img, (x, y))
            y += 20

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
        
        rect = pygame.Rect(x-22, y-22, 50, 50)
        
        if buildLocation.building.isFlipped:
            color = PLAYER_BUILDING_RETIRED_COLOR_MAP[buildLocation.building.owner.color]
            textColor = GREY
        else:
            color = PLAYER_COLOR_MAP[buildLocation.building.owner.color]
            textColor = WHITE

        pygame.draw.rect(self.screen, color, rect)
        img = self.font.render(f"{buildLocation.building.name.value}", True, textColor)
        self.screen.blit(img, (x-23, y-10))

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

    def drawHand(self):

        active_player: Player = self.game.players[self.game.players_go]    
        card_offset_x = 50  # Initial X offset from left; adjust as needed
        card_offset_y = self.screen.get_height() - (CARD_HEIGHT // 2)  # Adjust Y to bottom
        card_spacing = CARD_WIDTH - 30  # Overlap cards; adjust as needed

        mouse_x, mouse_y = pygame.mouse.get_pos()
        for i, card in enumerate(active_player.hand.cards):
            print(i+1, ' Card - ', card)
            card_rect = pygame.Rect(card_offset_x + i * card_spacing, card_offset_y, CARD_WIDTH, CARD_HEIGHT)

            # Draw the card image based on card type
            if isinstance(card, LocationCard):
                # Use specific color image for LocationCards
                card_image = self.locationCardsImg[card.getColor()]
                self.screen.blit(card_image, card_rect.topleft)
                # Draw card name
                name_text = self.font.render(card.name.upper(), True, WHITE)
                text_rect = name_text.get_rect(center=(card_rect.x + CARD_WIDTH // 2, card_rect.y + 10))
                # pygame.draw.rect(self.screen, PLAYER_COLOR_MAP[card.getColor().name], card_rect)
                self.screen.blit(name_text, text_rect)
            elif isinstance(card, IndustryCard):
                # Use pre-loaded image for IndustryCards
                card_image = self.industryCardsImg[card.name]
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

            print(building)
            print(building.resourcesType.name)
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

    def update_game_log(self, message):
        self.message_count += 1
        color = self.road_colours[message["player_id"]]
        message_to_add = "{style}{color "+str(color)+"}"+str(self.message_count) + ". " + message["text"] + "\n"
        self.game_log_sftext.text = message_to_add + self.game_log_sftext.text
        self.game_log_sftext.parse_text()

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
    
    def render_board(self):
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
        self.drawHand()
        pygame.display.update()
    
    def run_event_loop(self, test=False):
        run = True

        # if self.policies is not None:
        #     self.initialise_AI()

        while run:
            pygame.time.delay(150)
            Tk().wm_withdraw()
            self.screen.fill(self.BACKGROUND_COLOUR)
            # self.draw_invisible_edges()
            # if self.game.can_move_robber:
            #     self.draw_invisible_hexagons()
            # else:
            #     self.invisible_hexagons = []
            #     self.invisible_hexagon_points = []
            self.render_board()

            mouse_click = False
            over_corner = False
            over_edge = False

            # if test:
            #     players_go = self.get_players_turn()
            #     if isinstance(self.policies[players_go], str):
            #         pass
            #     else:
            #         done = self.step_AI()
            #         if done:
            #             break

            #         pygame.display.update()
            #         self.game_log_sftext.post_update()
            #         pygame.event.pump()
            #         continue

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False
                elif event.type == pygame.MOUSEBUTTONUP:
                    mouse_click = True
                    print('Click coords = ', pygame.mouse.get_pos())
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button <= 3:
                        pass
                    else:
                        mouse_pos = pygame.mouse.get_pos()
                        print('Click coords = ', mouse_pos)
                        if self.game_log_target_rect.collidepoint(*mouse_pos):
                            self.game_log_sftext.on_mouse_scroll(event)

            players_go = self.game.board.players[0]
            mouse_pos = pygame.mouse.get_pos()




            pygame.display.update()
            self.game_log_sftext.post_update()
            pygame.event.pump()