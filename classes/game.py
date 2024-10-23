from typing import List, Tuple, Dict
import numpy as np
import copy
from collections import defaultdict, deque

from classes.buildings.industry_building import IndustryBuilding
from classes.enums import ActionTypes, Era, PlayerId
from classes.player import Player

from .board import Board


ROUNDS_PER_PLAYER_NUM = {"2": 10, "3": 9, "4": 8}

PLAYER_COLORS = ["Red", "Blue", "Green", "Yellow"]
PLAYER_NAMEES = ["Owen", "Brunel", "Arkwright", "Coade"]


class Game:
    def __init__(
        self, num_players=2, interactive=False, debug_mode=False, policies=None
    ):

        self.num_players = num_players
        self.max_turns = ROUNDS_PER_PLAYER_NUM[str(num_players)]
        self.reset()
        self.interactive = interactive
        self.debug_mode = debug_mode
        self.policies = policies
        self.players_go_index = 0
        self.winner = None
        self.playerVPS = {}

        self.canalWinner = None

        for player in self.board.players:
            self.playerVPS[player.id] = 0

        if interactive:
            self.display = self.initDisplay(interactive, debug_mode, policies)
        else:
            self.display = None

    def render(self):
        if self.display is None:
            self.display = self.initDisplay(
                self.interactive, self.debug_mode, self.policies
            )

        self.display.render()

    def initDisplay(self, interactive, debug_mode, policies):
        from classes.ui.display import Display as GameDisplay

        return GameDisplay(
            self, interactive=interactive, debug_mode=debug_mode, policies=policies
        )

    def reset(self):
        self.board = Board(self.num_players)
        self.players: Dict[PlayerId, Player] = {}
        self.action_history = defaultdict(list)
        self.turn = 1
        for color in PLAYER_COLORS[: self.num_players]:
            id = PlayerId[color]
            self.players[id] = Player(
                name=PLAYER_NAMEES[id - 1], board=self.board, playerId=id
            )
            print(f"Player {id} cards: {self.players[id].hand.cards}")

        # set player order
        self.players_go = self.board.orderPlayers(random=True)
        self.players_go_index = 0

        self.first_round = True
        self.player_has_to_liquidate = False
        self.players_to_liquidate = []

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

    def do_action(self, action):
        player: Player = self.get_active_player()

        action_number = len(self.action_history[(self.turn, player.id)]) + 1
        message = {"player_id": player.id, "text": f"Action {action_number}: "}

        if "type" not in action:
            raise ValueError("Action must have a type")

        print(f"Doing action {action} for player {player.id}")
        if action["type"] == ActionTypes.Loan and "card" in action:
            player.loan(action["card"])
            message["text"] += f"{player.name} took a loan"
        elif action["type"] == ActionTypes.Pass and "card" in action:
            player.passTurn(action["card"])
            message["text"] += f"{player.name} passed"
        elif (
            action["type"] == ActionTypes.Scout
            and "card1" in action
            and "card2" in action
            and "card3" in action
        ):
            player.scout(action["card1"], action["card2"], action["card3"])
            message["text"] += f"{player.name} scouted"
        elif (
            action["type"] == ActionTypes.Sell
            and "card" in action
            and "forSale" in action
            and "freeDevelop" in action
        ):
            player.sell(action["card"], action["forSale"], action["freeDevelop"])
            message["text"] += f"{player.name} sold the following:\n"

            for building, beerSources, _ in action["forSale"]:
                soldMeessage = (
                    f"   {building.name.value.capitalize()} in {building.town.name}"
                )
                if len(beerSources) > 0:
                    soldMeessage += " with beer from:\n"
                    for beerSource in beerSources:
                        soldMeessage += "       "
                        soldMeessage += (
                            f"Brewery in {beerSource.town.name}"
                            if isinstance(beerSource, IndustryBuilding)
                            else f"Merchant in {beerSource.tradePost.name}"
                        )
                        soldMeessage += "\n"
                message["text"] += soldMeessage

        elif (
            action["type"] == ActionTypes.PlaceRailRoad
            and "card" in action
            and "road1" in action
            and "coalSource1" in action
        ):
            player.buildOneRailroad(
                action["card"], action["road1"], action["coalSource1"]
            )
            message[
                "text"
            ] += f"{player.name} built railroad: {action['road1'].towns[0].name} -- {action['road1'].towns[1].name}"
        elif (
            action["type"] == ActionTypes.PlaceSecondRoad
            and "card" in action
            and "road1" in action
            and "road2" in action
            and "coalSource1" in action
            and "coalSource2" in action
            and "beerSource" in action
        ):
            player.buildTwoRailroads(
                action["card"],
                action["road1"],
                action["road2"],
                [action["coalSource1"], action["coalSource2"]],
                action["beerSource"],
            )
            message["text"] += f"{player.name} built 2 railroads:\n "

            for road in (action["road1"], action["road2"]):
                message["text"] += f"   {road.towns[0].name} -- {road.towns[1].name}\n"
        elif (
            action["type"] == ActionTypes.BuildIndustry
            and "building" in action
            and "buildLocation" in action
            and "coalSources" in action
            and "ironSources" in action
            and "card" in action
        ):
            player.buildBuilding(
                action["building"].name,
                action["buildLocation"],
                action["card"],
                action["coalSources"],
                action["ironSources"],
            )
            message[
                "text"
            ] += f"{player.name} built {action['building'].name.value} ({action['building'].getTier()}) in {action['buildLocation'].town.name}"
        elif (
            action["type"] == ActionTypes.PlaceCanal
            and "road" in action
            and "card" in action
        ):
            player.buildCanal(
                roadLocation=action["road"],
                discard=action["card"],
            )
            message[
                "text"
            ] += f"{player.name} built canal: {action['road'].towns[0].name} -- {action['road'].towns[1].name}"
        elif (
            action["type"] == ActionTypes.DevelopOneIndustry
            and "card" in action
            and "industry1" in action
        ):

            initialTier = action["industry1"].getTier()
            player.developOneIndustry(
                action["industry1"],
                action["card"],
                action["ironSources"],
            )

            message[
                "text"
            ] += f'{player.name} developed {action["industry1"].name.value}: {initialTier} --> {action["industry1"].getTier()}'

        elif (
            action["type"] == ActionTypes.DevelopTwoIndustries
            and "card" in action
            and "industry1" in action
            and "industry2" in action
        ):
            if not "ironSources" in action:
                action["ironSources"] = []
            initialTiers = (
                action["industry1"].getTier(),
                action["industry2"].getTier(),
            )
            player.developTwoIndustries(
                action["industry1"],
                action["industry2"],
                action["card"],
                action["ironSources"],
            )
            message["text"] += f"{player.name} developed 2 industries:\n"

            for i, industry in enumerate([action["industry1"], action["industry2"]]):
                f"  {industry.name.value}: {initialTiers[i]} --> {industry.getTier()}\n"

        else:
            raise ValueError(f"Invalid action {action} for player {player.id}")
        return message

    def next_action(self, action):
        # if self.interactive:
        #     self.display.render()

        player = self.get_active_player()

        action_log = self.do_action(action)

        self.save_action(player.id, action)

        if (
            len(self.action_history[(self.turn, player.id)]) >= self.get_num_actions()
            and player.freeDevelopCount == 0
        ):
            self.players_go_index += 1
            if self.players_go_index == self.num_players:
                self.players_go_index = 0
                self.start_new_turn()
        return action_log

    def get_winner(self) -> Player:
        # Get the maximum number of victory points
        max_vps = max(self.playerVPS.values())

        # Get the players with the maximum number of victory points
        max_vps_players: List[Player] = [
            self.players[player_id]
            for player_id, vps in self.playerVPS.items()
            if vps == max_vps
        ]

        if len(max_vps_players) == 1:
            # If there is only one player with the maximum number of victory points, return that player
            return max_vps_players[0]
        else:
            # If there are multiple players with the maximum number of victory points, return the player with the most money
            return max(max_vps_players, key=lambda player: player.money)

    def start_new_turn(self):
        # check if end game/ era change
        if self.board.era == Era.canal and self.turn >= self.max_turns:
            self.playerVPS = self.board.endCanalEra()
            self.turn = 0
            return
        if self.board.era == Era.railroad and self.turn >= self.max_turns:
            self.board.endRailEra()
            for player_id, player in self.players.items():
                self.playerVPS[player_id] = player.countCurrentPoints()
            self.game_over = True
            self.winner = self.get_winner()
            return

        # determine spend order and reset
        self.players_go = self.board.orderPlayers()

        # reset spend amount and give income
        for player in self.board.players:
            player.spentThisTurn = 0
            incomeMoney = player.incomeLevel()
            if player.money + incomeMoney < 0:
                self.player_has_to_liquidate = True

                self.players_to_liquidate = player
                return
            player.money += incomeMoney

            player.hand.cards.extend(self.board.deck.draw(self.get_num_actions()))

        if self.turn == 1:
            self.first_round = False

        self.turn += 1

    # Return active player instance
    def get_active_player(self) -> Player:
        try:
            return self.board.players[self.players_go_index]
        except:
            print("Error: no active player")
            return None

    # return num actions available to the player right now
    def get_num_actions(self):
        return 1 if self.first_round else 2

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

    def save_action(self, player_id: str, action: dict):
        self.action_history[(self.turn, player_id)].append(action)

    def restore_state(self, state):

        state = copy.deepcopy(state)  # prevent state being changed

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
