from collections import Counter
import numpy as np
import copy

from classes.build_location import BuildLocation
from classes.buildings.building import Building
from classes.buildings.enums import BuildingName
from classes.buildings.industry_building import IndustryBuilding
from classes.buildings.market_building import MarketBuilding
from classes.cards.industry_card import IndustryCard
from classes.cards.location_card import LocationCard
from classes.game import Game
from classes.enums import (
    ActionTypes,
    Era,
    PlayerId,
)
from classes.player import Player
from classes.town import Town
from consts import BUILDINGS, ROAD_LOCATIONS, STARTING_CARDS, TOWNS


N_BL = 76
N_ROAD_LOCATIONS = 39
N_TOWNS = 22
N_INDUSTRIES = 6
N_LEVELS = 8
N_COAL_SOURCES = 16  # 15 coal buildlocations  + 1 for coal market connection
N_IRON_SOURCES = 10  # 9 iron buildlocations + 1 for iron market connection
MAX_RESORCES = 6
MAX_TIER_BUILDINGS = 3
MAX_VPS = 250


class EnvWrapper(object):
    def __init__(
        self,
        interactive=False,
        debug_mode=False,
        win_reward=500,
        dense_reward=False,
        policies=None,
    ):
        self.game = Game(
            interactive=interactive, debug_mode=debug_mode, policies=policies
        )
        self.build_location_vector = self.generate_build_locations()

        self.win_reward = win_reward
        self.dense_reward = dense_reward
        self.reward_annealing_factor = 1.0

    # Define a generator to yield build locations from each town
    def generate_build_locations(self):
        output = []
        for town in self.game.board.towns:
            for build_location in town.buildLocations:
                for possibleBuild in build_location.possibleBuilds:
                    output.append((build_location, possibleBuild))
        return tuple(output)

    def generate_coal_sources(self):
        for bl, bname in self.build_location_vector:
            if bname == BuildingName.coal:
                yield bl

    def generate_iron_sources(self):
        for bl, bname in self.build_location_vector:
            if bname == BuildingName.iron:
                yield bl

    def get_action_masks(self):
        player = self.game.players[self.game.players_go]
        return
        num_actions = len(ActionTypes)

        valid_actions = [
            np.zeros((num_actions,)),
            np.ones(
                (
                    3,
                    N_CORNERS,
                )
            ),  # place road head
            np.ones((N_EDGES + 1,)),  # build road head
            np.ones((N_TILES,)),  # move robber head
            np.ones((len(DevelopmentCard),)),  # play dev card head
            np.ones((2,)),  # accept/reject head
            np.ones((3, 3)),  # player head
            np.ones((6,)),  # propose trade head
            np.ones((6,)),  # propose trade receive head
            np.ones((4, 5)),  # exchange this res head
            np.ones((5,)),  # receive this res head
            np.ones((5,)),  # discard resource head
        ]

        return valid_actions

    def _translate_action(self, action):
        return action

    def reset(self):
        self.game.reset()
        self.winner = None
        self.curr_vps = {player.id: 0 for player in self.game.players.values()}
        return self._get_obs()

    def step(self, action):
        translated_action = self._translate_action(action)
        message = self.game.do_action(translated_action)

        obs = self._get_obs()

        done, reward = self._get_done_and_rewards(action)

        info = {"log": message}

        return obs, reward, done, info

    def _get_obs(self):
        # TODO: Implement liquidation
        player = self.game.get_active_player()

        obs = {"player_id": player.id}

        obs["board_state"] = self._get_board_features()

        obs["road_state"] = self._get_road_features()

        obs["game_info"] = self._get_game_info()

        obs["industry_mat"] = self._get_constant_industry_mat()

        obs["player_features"] = self._get_player_features(player)

        obs["player_current_hand"] = self._get_player_hand(player)

        obs["player_current_info"], obs[f"player_current_mat"] = self._get_player_features(player)

        for i, player_id in enumerate(self.game.playerVPS.keys()):
            if player_id != player.id:
                obs[f"player_{i}_info"], obs[f"player_{i}_mat"] = self._get_player_features(player)

        return obs

    def _get_done_and_rewards(self, action):
        done = False
        rewards = {player_id: 0 for player_id in self.game.playerVPS.keys()}

        updated_vps = {}

        for player_id, player in self.game.players.items():
            updated_vps[player_id] = player.countCurrentPoints()
            if self.dense_reward:
                rewards[player_id] += 5 * (
                    updated_vps[player_id] - self.curr_vps[player_id]
                )
                # TODO: Get the rewards for SELL amount
                if action[0] == ActionTypes.Sell:
                    rewards[player_id] += len(action[2])

                if action[0] == ActionTypes.Liquidate:
                    rewards[player_id] -= 0.7

                rewards[player_id] *= self.reward_annealing_factor
        self.curr_vps = updated_vps

        if self.game.winner is not None:
            rewards[self.game.winner.id] += self.win_reward

        return done, rewards

    def _get_valid_builds(self, player: Player):
        builds, firstBuildings, availableBuildLocations = player.getAvailableBuilds()
        valid_build_locations = np.zeros((N_BL,))

        possibleIndustries = set([b.name for b in firstBuildings])

        for i, bl, industry_type in enumerate(self.build_location_vector):
            if industry_type in possibleIndustries:
                firstBuilding = player.industryMat[industry_type][-1]
                if (firstBuilding, bl) in builds:
                    valid_build_locations[i] = 1.0
        return valid_build_locations

    def _get_available_roads(self, player: Player):

        available_roads = np.zeros((N_BL,))

        availableRoads = (
            player.getAvailableNetworks()
            if self.game.board.era == Era.canal
            else player.getAvailableRailroads()
        )

        for i, road in enumerate(ROAD_LOCATIONS):
            if road in availableRoads:
                available_roads[i] = 1.0
        return available_roads

    def _get_available_industries(self, player: Player):
        available_industry = np.zeros((N_INDUSTRIES,))

        # Iterate over the enum, getting the index and value
        for i, building_name in enumerate(BuildingName):
            if len(player.industryMat[building_name.value]) > 0:
                available_industry[i] = 1.0
        return available_industry

    def _get_available_coal_sources(self, player: Player, town: Town):
        available_coal_sources = np.zeros((N_COAL_SOURCES,))

        availableCoalBuildings, connectedToMarket = (
            self.game.board.getAvailableCoalForTown(town)
        )

        coal_bl_ids = set(
            [building.buildLocation.id for building in availableCoalBuildings]
        )

        for i, build_location in enumerate(self.generate_coal_sources()):
            if build_location.id in coal_bl_ids:
                available_coal_sources[i] = 1.0
        if (
            connectedToMarket is not None
            and player.money >= self.game.board.priceForCoal(1)
        ):
            available_coal_sources[-1] = 1.0
        return available_coal_sources

    def _get_available_iron_sources_first(self, player: Player):
        available_iron_sources = np.zeros((N_IRON_SOURCES,))

        iron_bl_ids = [b for b in self.game.board.getIronBuildings()]

        for i, build_location in enumerate(self.generate_iron_sources()):
            if build_location.id in iron_bl_ids:
                available_iron_sources[i] = 1.0

        # Iron Market always available
        if player.money >= self.game.board.priceForIron(1):
            available_iron_sources[-1] = 1.0

        return available_iron_sources

    def _get_available_iron_sources_second(
        self, player: Player, firstSource: IndustryBuilding | None
    ):
        available_iron_sources = np.zeros((N_IRON_SOURCES,))

        iron_bl_ids = set(
            [
                b.buildLocation.id
                for b in self.game.board.getIronBuildings()
                if firstSource != b or (b == firstSource and b.resourceAmount > 1)
            ]
        )

        for i, build_location in enumerate(self.generate_iron_sources()):
            if build_location.id in iron_bl_ids:
                available_iron_sources[i] = 1.0

        if player.money >= self.game.board.priceForIron(1):
            available_iron_sources[-1] = 1.0

        return available_iron_sources

    # def _get_board_state(self, player: Player):
    #     tile_features = []

    #     for i, town in enumerate(TOWNS):
    #         for j, level in enumerate(town.levels):
    #             if level.building is not None and level.building.owner == player:
    #                 board_state[i, j] = 1.0
    #     return board_state

    def _get_road_features(self):
        road_features = np.zeros((N_ROAD_LOCATIONS,))

        for i, roadLocation in enumerate(self.game.board.roadLocations):
            if roadLocation.isBuilt and roadLocation.road is not None:
                road_features[i] = 1.0
        return road_features

    def _get_board_features(self):
        board_features = []

        for town in self.game.board.towns:
            for build_location in town.buildLocations:
                for possibleBuild in build_location.possibleBuilds:
                    # Industry -  one of 6 possible types
                    industry = np.zeros((N_INDUSTRIES,))
                    for i, building_name in enumerate(BuildingName):
                        if building_name == possibleBuild:
                            industry[i] = 1.0
                            break
                    # Level - 0 if no building, one of 8 levels if built
                    level = np.zeros((N_LEVELS,))
                    if build_location.building is not None:
                        level[build_location.building.tier] = 1.0

                    # Player ownership - 0 if no building, one of num_players if built
                    player = np.zeros((self.game.num_players,))
                    if build_location.building is not None:
                        player[build_location.building.owner.id - 1] = 1.0

                    # Resources Present
                    resources = np.zeros((6,))
                    if build_location.building is not None and isinstance(
                        build_location.building, IndustryBuilding
                    ):
                        resources[build_location.building.resourceAmount - 1] = 1.0

                    # Is Flipped
                    is_flipped = (
                        1.0
                        if not build_location.building is None
                        and build_location.building.isFlipped
                        else 0.0
                    )
                    flipped = np.array([is_flipped], dtype=np.float32)
                    feature = np.concatenate(
                        (industry, level, player, resources, flipped)
                    )
                    board_features.append(feature)

    def _get_constant_industry_mat(self):
        constant_mat = []

        building_lookup = {
            (building.name, building.tier): building for building in BUILDINGS
        }

        for building_name in BuildingName:
            for tier in range(1, N_LEVELS + 1):
                key = (building_name, tier)
                if not key in building_lookup:
                    continue
                building: Building = building_lookup[key]

                # Money Cost will be one of [0, 5, 7, 8, 9, 10, 12, 14, 16, 17, 18, 20, 22, 24]
                unique_costs = [0, 5, 7, 8, 9, 10, 12, 14, 16, 17, 18, 20, 22, 24]
                money_cost_vector = np.zeros((14,))
                money_cost = building.cost
                money_cost_vector[unique_costs.index(money_cost)] = 1.0

                # coal cost will be one of [0, 1, 2]
                coal_cost_vector = np.zeros((3,))
                coal_cost = building.coalCost
                coal_cost_vector[coal_cost] = 1.0

                # iron cost will be one of [0, 1, 2]
                iron_cost_vector = np.zeros((3,))
                iron_cost = building.ironCost
                iron_cost_vector[iron_cost] = 1.0

                # beer cost will be one of [0, 1, 2]
                beer_cost_vector = np.zeros((3,))
                beer_cost = (
                    building.beerCost if isinstance(building, MarketBuilding) else 0
                )
                beer_cost_vector[beer_cost] = 1.0

                # income will be one of [0, 1, 2, 3, 4, 5, 6, 7]
                unique_incomes = [0, 1, 2, 3, 4, 5, 6, 7]
                income_vector = np.zeros((8,))
                income = building.incomeGained
                income_vector[unique_incomes.index(income)] = 1.0

                # resources will be one of [0, 1, 2, 3, 4, 5, 6]
                resources_vector = np.zeros((7,))
                resources = (
                    building.resourceAmount
                    if isinstance(building, IndustryBuilding)
                    else 0
                )
                resources_vector[resources] = 1.0

                # network points will be 0, 1, or 2
                network_points_vector = np.zeros((3,))
                network_points = building.networkPoints
                network_points_vector[network_points] = 1.0

                # Flip VPS will be one of 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 20
                unique_flip_vps = [1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 20]
                flip_vps_vector = np.zeros((12,))
                flip_vps = building.victoryPointsGained
                flip_vps_vector[unique_flip_vps.index(flip_vps)] = 1.0

                mat_feature = np.concatenate(
                    (
                        money_cost_vector,
                        coal_cost_vector,
                        iron_cost_vector,
                        beer_cost_vector,
                        income_vector,
                        resources_vector,
                        network_points_vector,
                        flip_vps_vector,
                    )
                )
                constant_mat.append(mat_feature)
        return constant_mat

    def _get_players_industry_mat(self, player: Player):

        industry_mat = []

        for i, building_name in enumerate(BuildingName):
            tier = np.zeros((N_LEVELS + 1,))
            highest_tier = 0

            if (
                building_name in player.industryMat
                and len(player.industryMat[building_name]) > 0
            ):
                highest_tier = player.industryMat[building_name][-1].tier
            tier[highest_tier] = 1.0

            count_vector = np.zeros((MAX_TIER_BUILDINGS + 1,))
            count_for_building = 0
            if highest_tier > 0:
                for building in player.industryMat[building_name]:
                    if building.tier == highest_tier:
                        count_for_building += 1
            count_vector[count_for_building] = 1.0
            industry_vector = np.concatenate((tier, count_vector))
            industry_mat.append(industry_vector)

        return np.array(industry_mat)

    def _get_available_industry(self, player: Player):
        available_industry = np.zeros((N_INDUSTRIES,))

        for i, building_name in enumerate(BuildingName):
            if len(player.industryMat[building_name.value]) > 0:
                available_industry[i] = 1.0
        return available_industry

    def _get_player_hand(self, player: Player):
        starting_cards = STARTING_CARDS[str(self.game.num_players)]
        total_cards = len(starting_cards)
        all_cards_vector = np.zeros((total_cards,))
        for i, card in enumerate(starting_cards):
            all_cards_vector[i] = 1.0 if card in player.hand.cards else 0.0

        wild_cards = np.zeros((2,))

        for card in player.hand.cards:
            if not card.isWild:
                continue
            if isinstance(card, IndustryCard):
                wild_cards[0] = 1.0
            elif isinstance(card, LocationCard):
                wild_cards[1] = 1.0
        return np.concatenate((all_cards_vector, wild_cards))

    def _get_game_info(self):
        turn = np.zeros((self.game.max_turns,))
        turn[self.game.turn - 1] = 1.0

        era = np.zeros((2,))
        for i, era_val in enumerate(Era):
            if era_val == self.game.board.era:
                era[i] = 1.0
                break

        start_cards = STARTING_CARDS[str(self.game.num_players)]
        cards_left = np.zeros((len(start_cards) + 1,))
        cards_left[len(self.game.board.deck.cards)] = 1.0

        wild_industry_cards = np.zeros((self.game.num_players + 1,))
        wild_location_cards = np.zeros((self.game.num_players + 1,))

        wild_industry_cards[len(self.game.board.wildIndustryCards)] = 1.0
        wild_location_cards[len(self.game.board.wildlocationCards)] = 1.0

        return np.concatenate(
            (turn, era, cards_left, wild_industry_cards, wild_location_cards)
        )

    def _get_player_features(self, player: Player):

        # normalize value out with max being 250
        potential_vps = player.countCurrentPoints() / 250.0

        incomeLevel = player.incomeLevel() / 99.0
        money = player.money / 250.0

        turnOrder = np.zeros((self.game.num_players,))
        turnOrder[self.game.board.players.index(player)] = 1.0
        
        industryMat = self._get_players_industry_mat(player)

        spentThisTurn = player.spentThisTurn / 250.0

        start_cards = STARTING_CARDS[str(self.game.num_players)]
        players_discard = np.zeros((len(start_cards) + 1,))
        for i, card in enumerate(start_cards):
            if card.id in [card.id for card in player.hand.discard]:
                players_discard[i] = 1.0

        
        return np.concatenate(
            (
                players_discard,
                [potential_vps],
                [incomeLevel],
                [money],
                [spentThisTurn],
                turnOrder
            )
        ), industryMat
