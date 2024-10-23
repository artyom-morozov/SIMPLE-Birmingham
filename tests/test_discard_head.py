# test_action_heads.py

import asyncio
import unittest
from classes.board import Board
import torch
from unittest.mock import MagicMock

# Import the action heads module and the game environment
from action_heads_module_brass import ActionHead
from env_wrapper import EnvWrapper
from classes.enums import ActionTypes

class TestDiscardCardHead(unittest.TestCase):
    def setUp(self):
        # Initialize the game environment and reset
        self.env = EnvWrapper(interactive=False, debug_mode=False)
        self.env.reset()
        self.player = self.env.game.get_active_player()

        # Mock the observation module output
        self.observation_output = torch.randn(1, 512)

        # Initialize the Discard Card Head
        self.discard_card_head = ActionHead(
            main_input_dim=512,
            output_dim=8,  # Max cards in hand
            mlp_size=128,
            id="discard_card"
        )

    def test_discard_card_selection(self):
        # Create an action mask based on the player's hand
        action_mask = torch.zeros(1, 8)
        num_cards_in_hand = len(self.player.hand.cards)
        action_mask[0, :num_cards_in_hand] = 1

        # Forward pass through the discard card head
        distribution = self.discard_card_head(self.observation_output, action_mask, custom_inputs=None)

        # Sample an action
        action = distribution.sample()

        # Check that the selected card index is valid
        self.assertTrue(action.item() in range(num_cards_in_hand), "Selected card index is invalid.")
    
    async def call(self, board: Board):
        await asyncio.sleep(2)

if __name__ == '__main__':
    unittest.main()
