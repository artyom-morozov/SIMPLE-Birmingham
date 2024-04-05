import numpy as np
import copy

from classes.game import Game
from classes.enums import ActionTypes, DevelopmentCard, Resource, BuildingType, PlayerId
from classes.player import Player

N_BUILDLOCATIONS = 54


class EnvWrapper(object):
    def __init__(
        self,
        interactive=False,
        debug_mode=False,
        win_reward=500,
        dense_reward=False,
        policies=None,
    ):
        if max_actions_per_turn is None:
            self.max_actions_per_turn = np.inf
        else:
            self.max_actions_per_turn = max_actions_per_turn
        self.max_proposed_trades_per_turn = max_proposed_trades_per_turn
        """
        can turn validate actions off to increase speed slightly. But if you send invalid
        actions it will probably fuck everything up.
        """
        self.validate_actions = validate_actions
        self.game = Game(
            interactive=interactive, debug_mode=debug_mode, policies=policies
        )

        self.win_reward = win_reward
        self.dense_reward = dense_reward
        self.reward_annealing_factor = 1.0

    def _get_valid_build_locations(self, player: Player):
        availableBuildLocations = player.getAvailableBuilds
        valid_corners = np.zeros((N_CORNERS,))
        for i, corner in enumerate(self.game.board.corners):
            if (
                corner.building is not None
                and corner.building.type == BuildingType.Settlement
            ):
                if corner.building.owner == player.id:
                    valid_corners[i] = 1.0
        return valid_corners
