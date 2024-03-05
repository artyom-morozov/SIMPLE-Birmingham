import numpy as np
import random
import copy
from collections import defaultdict, deque

from classes.enums import Era, PlayerId
from classes.player import Player
from classes.ui.display import Display

from .board import Board


ROUNDS_PER_PLAYER_NUM = {
    '2': 10,
    '3': 9,
    '4':  8
}

PLAYER_COLORS = ["Red", "Blue", "Green", "Yellow"]
PLAYER_NAMEES = ["Owen", "Brunel", "Arkwright", "Coade"]

class Game:
    def __init__(self, num_players=2, interactive=False, debug_mode=False, policies=None):


        self.num_players = num_players
        self.max_turns = ROUNDS_PER_PLAYER_NUM[str(num_players)]
        self.reset()
        self.interactive = interactive
        self.debug_mode = debug_mode
        self.policies = policies
        if interactive:
            self.display = Display(self, interactive=interactive, debug_mode=debug_mode, policies=policies)
        else:
            self.display = None

    def render(self):
        if self.display is None:
            self.display = Display(self, interactive=self.interactive, debug_mode=self.debug_mode)

        self.display.render()
    
    def reset(self):
        self.board = Board(self.num_players)
        self.players = {}


        for color in PLAYER_COLORS[:self.num_players]:
            id = PlayerId[color]
            self.players[id] = Player(name=PLAYER_NAMEES[id-1], board=self.board, playerId=id)


        # set player order
        self.players_go = self.board.orderPlayers(random=True)
        
        self.first_round = True
        self.player_has_to_liquidate = False
        self.players_to_liquidate = []
        self.turn = 0



    # determine the order of the next player to go
    def change_order(self):
        self.board.players.sort(key=lambda p: p.spentThisTurn)

    def getIncomeGained(points: int) -> int:
        if points < 11:
            return 0  # No income for points less than 11
        elif points <= 30:
            # Calculate income for pairs from 11 to 30
            return (points - 10 + 1) // 2
        elif points <= 60:
            # Calculate income for triplets from 31 to 60
            # Adjust calculation to ensure 31-33 returns 11
            return 10 + (points - 31) // 3 + 1
        elif points <= 98:
            # Calculate income for quadruples from 61 to 98
            # Adjust calculation to ensure 61-64 returns 21
            return 20 + (points - 61) // 4 + 1
        else:
            # Points greater than 99 return 30
            return 30

    def start_new_turn(self):
        # check if end game/ era change
        if self.board.era == Era.canal and self.turn >= self.max_turns:
            self.board.endCanalEra()
            self.turn = 0
            return
        if self.board.era == Era.railroad and self.turn >= self.max_turns:
            self.board.endRailEra()
            self.turn = 0
            return


        # determine spend order and reset 
        self.players_go = self.board.orderPlayers()

        # reset spend amount and give income 
        for player in self.board.players:
            player.spentThisTurn = 0
            incomeMoney = player.incomeLevel()
            if player.money + incomeMoney < 0 :
                self.player_has_to_liquidate = True

                self.players_to_liquidate = player
                return
            player.money += incomeMoney

            num_cards_to_draw = 1 if self.first_round else 2
            player.hand.draw(num_cards_to_draw)
                



        


        self.turn += 1
        
    
    def save_current_state(self):

        state = {}

        state["player_has_to_liquidate"] = self.player_has_to_liquidate
        state["players_to_liquidate"] = copy.copy(self.players_to_liquidate)

        # state["tile_info"] = []
        # for tile in self.board.tiles:
        #     state["tile_info"].append(
        #         (tile.terrain, tile.resource, tile.value, tile.likelihood, tile.contains_robber)
        #     )

        # state["edge_occupancy"] = [edge.road for edge in self.board.edges]

        # state["corner_buildings"] = []
        # for corner in self.board.corners:
        #     if corner.building is not None:
        #         state["corner_buildings"].append((corner.building.type, corner.building.owner))
        #     else:
        #         state["corner_buildings"].append((None, None))

        # state["harbour_order"] = [harbour.id for harbour in self.board.harbours]

        # state["players"] = {}
        # for player_key, player in self.players.items():
        #     state["players"][player_key] = {"id": player.id,
        #          "player_order": copy.copy(player.player_order),
        #          "player_lookup": copy.copy(player.player_lookup),
        #          "inverse_player_lookup": copy.copy(player.inverse_player_lookup),
        #          "buildings": copy.copy(player.buildings),
        #          "roads": copy.copy(player.roads),
        #          "resources": copy.copy(player.resources),
        #          "visible_resources": copy.copy(player.visible_resources),
        #          "opponent_max_res": copy.copy(player.opponent_max_res),
        #          "opponent_min_res": copy.copy(player.opponent_min_res),
        #          "harbour_info": [(key, val.id) for key, val in player.harbours.items()],
        #          "longest_road": player.longest_road,
        #          "hidden_cards": copy.copy(player.hidden_cards),
        #          "visible_cards": copy.copy(player.visible_cards),
        #          "victory_points": player.victory_points
        #     }

        # state["players_go"] = self.players_go
        # state["player_order"] = copy.deepcopy(self.player_order)
        # state["player_order_id"] = self.player_order_id

        # state["resource_bank"] = copy.copy(self.resource_bank)
        # state["building_bank"] = copy.copy(self.building_bank)
        # state["road_bank"] = copy.copy(self.road_bank)
        # state["development_cards"] = copy.deepcopy(self.development_cards)
        # state["development_card_pile"] = copy.deepcopy(self.development_cards_pile)

        # state["largest_army"] = self.largest_army
        # state["longest_road"] = self.longest_road

        # state["initial_placement_phase"] = self.initial_placement_phase
        # state["initial_settlements_placed"] = copy.copy(self.initial_settlements_placed)
        # state["initial_roads_placed"] = copy.copy(self.initial_roads_placed)
        # state["initial_second_settlement_corners"] = copy.copy(self.initial_second_settlement_corners)

        # state["dice_rolled_this_turn"] = self.dice_rolled_this_turn
        # state["played_development_card_this_turn"] = self.played_development_card_this_turn
        # state["must_use_development_card_ability"] = self.must_use_development_card_ability
        # state["must_respond_to_trade"] = self.must_respond_to_trade
        # state["proposed_trade"] = copy.deepcopy(self.proposed_trade)
        # state["road_building_active"] = self.road_building_active
        # state["can_move_robber"] = self.can_move_robber
        # state["just_moved_robber"] = self.just_moved_robber
        # state["trades_proposed_this_turn"] = self.trades_proposed_this_turn
        # state["actions_this_turn"] = self.actions_this_turn
        # state["turn"] = self.turn
        # state["development_cards_bought_this_turn"] = self.development_cards_bought_this_turn
        # state["current_longest_path"] = copy.copy(self.current_longest_path)
        # state["current_army_size"] = copy.copy(self.current_army_size)
        # state["die_1"] = self.die_1
        # state["die_2"] = self.die_2

        # return state

    def restore_state(self, state):

        state = copy.deepcopy(state) #prevent state being changed

        self.players_to_discard = state["players_to_discard"]
        self.players_need_to_discard = state["players_need_to_discard"]

        # self.board.value_to_tiles = {}

        # for i, info in enumerate(state["tile_info"]):
        #     terrain, resource, value, likelihood, contains_robber = info[0], info[1], info[2], info[3], info[4]
        #     self.board.tiles[i].terrain = terrain
        #     self.board.tiles[i].resource = resource
        #     self.board.tiles[i].value = value
        #     self.board.tiles[i].likelihood = likelihood
        #     self.board.tiles[i].contains_robber = contains_robber

        #     if value != 7:
        #         if value in self.board.value_to_tiles:
        #             self.board.value_to_tiles[value].append(self.board.tiles[i])
        #         else:
        #             self.board.value_to_tiles[value] = [self.board.tiles[i]]
        #     if contains_robber:
        #         self.board.robber_tile = self.board.tiles[i]

        # for i, road in enumerate(state["edge_occupancy"]):
        #     self.board.edges[i].road = road

        # # for i, entry in enumerate(state["corner_buildings"]):
        # #     building, player = entry[0], entry[1]
        # #     if building is not None:
        # #         self.board.corners[i].building = Building(building, player, self.board.corners[i])
        # #     else:
        # #         self.board.corners[i].building = None

        # """have to reinitialise harbours - annoying"""
        # self.board.harbours = copy.copy([self.board.HARBOURS_TO_PLACE[i] for i in state["harbour_order"]])

        # for corner in self.board.corners:
        #     corner.harbour = None
        # for edge in self.board.edges:
        #     edge.harbour = None
        # for i, harbour in enumerate(self.board.harbours):
        #     # h_info = HARBOUR_CORNER_AND_EDGES[i]
        #     tile = self.board.tiles[h_info[0]]
        #     corner_1 = tile.corners[h_info[1]]
        #     corner_2 = tile.corners[h_info[2]]
        #     edge = tile.edges[h_info[3]]

        #     corner_1.harbour = harbour
        #     corner_2.harbour = harbour
        #     edge.harbour = harbour

        #     harbour.corners.append(corner_1)
        #     harbour.corners.append(corner_2)
        #     harbour.edge = edge


        # for key, player_state in state["players"].items():
        #     self.players[key].id = player_state["id"]
        #     self.players[key].player_order = player_state["player_order"]
        #     self.players[key].player_lookup = player_state["player_lookup"]
        #     self.players[key].inverse_player_lookup = player_state["inverse_player_lookup"]
        #     self.players[key].buildings = player_state["buildings"]
        #     self.players[key].roads = player_state["roads"]
        #     self.players[key].resources = player_state["resources"]
        #     self.players[key].visible_resources = player_state["visible_resources"]
        #     self.players[key].opponent_max_res = player_state["opponent_max_res"]
        #     self.players[key].opponent_min_res = player_state["opponent_min_res"]
        #     self.players[key].longest_road = player_state["longest_road"]
        #     self.players[key].hidden_cards = player_state["hidden_cards"]
        #     self.players[key].visible_cards = player_state["visible_cards"]
        #     self.players[key].victory_points = player_state["victory_points"]
        #     for info in player_state["harbour_info"]:
        #         key_res = info[0]; id = info[1]
        #         for harbour in self.board.harbours:
        #             if id == harbour.id:
        #                 self.players[key].harbours[key_res] = harbour

        # self.players_go = state["players_go"]
        # self.player_order = state["player_order"]
        # self.player_order_id = state["player_order_id"]

        # self.resource_bank = state["resource_bank"]
        # self.building_bank = state["building_bank"]
        # self.road_bank = state["road_bank"]
        # self.development_cards = state["development_cards"]
        # self.development_cards_pile = state["development_card_pile"]

        # self.largest_army = state["largest_army"]
        # self.longest_road = state["longest_road"]

        # self.initial_placement_phase = state["initial_placement_phase"]
        # self.initial_settlements_placed = state["initial_settlements_placed"]
        # self.initial_roads_placed = state["initial_roads_placed"]
        # self.initial_second_settlement_corners = state["initial_second_settlement_corners"]

        # self.dice_rolled_this_turn = state["dice_rolled_this_turn"]
        # self.played_development_card_this_turn = state["played_development_card_this_turn"]
        # self.must_use_development_card_ability = state["must_use_development_card_ability"]
        # self.must_respond_to_trade = state["must_respond_to_trade"]
        # self.proposed_trade = state["proposed_trade"]
        # self.road_building_active = state["road_building_active"]
        # self.can_move_robber = state["can_move_robber"]
        # self.just_moved_robber = state["just_moved_robber"]
        # self.trades_proposed_this_turn = state["trades_proposed_this_turn"]
        # self.actions_this_turn = state["actions_this_turn"]
        # self.turn = state["turn"]
        # self.development_cards_bought_this_turn = state["development_cards_bought_this_turn"]
        # self.current_longest_path = state["current_longest_path"]
        # self.current_army_size = state["current_army_size"]
        # self.die_1 = state["die_1"]
        # self.die_2 = state["die_2"]
