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

class TestActionTypeHead(unittest.TestCase):
    def setUp(self):
        # Initialize the game environment
        self.env = EnvWrapper(interactive=False, debug_mode=False)
        self.env.reset()

        # Mock the observation module output
        self.observation_output = torch.randn(1, 512)  # Example observation output

        # Initialize the Action Type Head
        self.action_type_head = ActionHead(
            main_input_dim=512,
            output_dim=8,  # Number of action types
            mlp_size=128,
            id="action_type"
        )

    def test_action_type_selection(self):
        # Mock the action mask to allow all actions
        action_mask = torch.ones(1, 8)

        # Forward pass through the action head
        distribution = self.action_type_head(self.observation_output, action_mask, custom_inputs=None)

        # Sample an action
        action = distribution.sample()

        # Check that the action is within valid range
        self.assertTrue(action.item() in range(8), "Selected action type is invalid.")

        # Optionally, check probabilities
        probs = distribution.probs.detach().numpy()
        self.assertTrue((probs >= 0).all() and (probs <= 1).all(), "Probabilities are not valid.")
    
    async def call(self, board: Board):
        await asyncio.sleep(2)

if __name__ == '__main__':
    unittest.main()
