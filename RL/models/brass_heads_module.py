# action_heads_module_brass.py

import torch
import torch.nn as nn

from RL.distributions import Categorical, DiagGaussian

# Constants (you may need to adjust these based on your implementation)
ACTION_TYPE_COUNT = 8  # Number of action types in Brass Birmingham
MAX_CARDS_IN_HAND = 8
MAX_CANAL_LOCATIONS = 39
MAX_RAIL_LOCATIONS = 39
MAX_BUILD_LOCATIONS = 76
MAX_COAL_SOURCES = 16
MAX_IRON_SOURCES = 10
MAX_BEER_SOURCES = 13
MAX_INDUSTRIES = 5
MAX_MERCHANTS = 6
MAX_BUILDINGS = 41
MAX_DISCARD_CARDS_SCOUT = 3

DEFAULT_MLP_SIZE = 128  # Adjust based on your preference

class MultiActionHeadsBrass(nn.Module):
    def __init__(self, action_heads, autoregressive_map, main_input_dim, log_prob_masks={},
                 type_conditional_action_masks=None):
        super(MultiActionHeadsBrass, self).__init__()
        self.dummy_param = nn.Parameter(torch.empty(0))
        self.autoregressive_map = autoregressive_map
        self.main_input_dim = main_input_dim
        self.log_prob_masks = log_prob_masks
        self.type_conditional_action_masks = type_conditional_action_masks

        self.action_heads = nn.ModuleList()
        for head in action_heads:
            self.action_heads.append(head)

    def forward(self, main_input, masks, actions=None, custom_inputs=None, deterministic=False,
                condition_on_action_type=None, log_specific_head_probs=False):
        head_outputs = []
        action_outputs = []
        head_log_probs_filtered = []

        joint_action_log_prob = 0
        entropy = 0

        if log_specific_head_probs:
            specific_log_output = []

        if condition_on_action_type is not None:
            type_output = torch.zeros(1, 13, dtype=torch.float32, device=self.dummy_param.device)
            type_output[0, condition_on_action_type] = 1.0
            first_output = torch.tensor([[condition_on_action_type]], dtype=torch.long, device=self.dummy_param.device)
            first_filter = torch.zeros(1, 1, dtype=torch.float32, device=self.dummy_param.device)
            head_outputs.append(type_output)
            action_outputs.append(first_output)
            head_log_probs_filtered.append(first_filter)

        for i, head in enumerate(self.action_heads):
            if i==0 and condition_on_action_type is not None:
                continue

            main_head_inputs = []
            for entry in self.autoregressive_map[i]:
                if entry[0] == -1:
                    initial_input = main_input
                else:
                    initial_input = head_outputs[entry[0]]
                if entry[1] is not None:
                    initial_input = entry[1](initial_input)
                if entry[0] >= 0:
                    initial_input *= (1-head_log_probs_filtered[entry[0]]) #filter inputs that are masked out.
                main_head_inputs.append(initial_input)
            main_head_inputs = torch.cat(main_head_inputs, dim=-1)

            #get relevant action masks
            if len(self.type_conditional_action_masks[i]):
                head_mask = 1
                for prev_head_ind, head_type_to_option_map in self.type_conditional_action_masks[i].items():
                    if actions is not None:
                        masks_to_mult = masks[i][head_type_to_option_map[actions[prev_head_ind]].squeeze(),
                                     np.arange(main_head_inputs.size(0)), :]
                        if prev_head_ind == 4:
                            action_type_mask = (actions[0] != ActionTypes.PlayDevelopmentCard).squeeze()
                            masks_to_mult[action_type_mask, ...] = 1.0
                        head_mask *= masks_to_mult
                    else:
                        masks_to_mult = masks[i][head_type_to_option_map[action_outputs[prev_head_ind]].squeeze(),
                                     np.arange(main_head_inputs.size(0)), :]
                        if prev_head_ind == 4:
                            action_type_mask = (action_outputs[0] != ActionTypes.PlayDevelopmentCard).squeeze()
                            masks_to_mult[action_type_mask, ...] = 1.0
                        head_mask *= masks_to_mult
            else:
                head_mask = masks[i]

            if head.returns_distribution:
                head_distribution = head(main_head_inputs, head_mask, custom_inputs)

                if deterministic:
                    head_action = head_distribution.mode()
                else:
                    if head.type == "normal":
                        head_action = head_distribution.rsample()
                    else:
                        head_action = head_distribution.sample()

                if head.type == "categorical":
                    one_hot_head_action = torch.zeros(main_input.size(0), head.output_dim, device=self.dummy_param.device)
                    if actions is None:
                        one_hot_head_action.scatter_(-1, head_action, 1.0)
                    else:
                        one_hot_head_action.scatter_(-1, actions[i], 1.0)
                    head_outputs.append(one_hot_head_action)
                else:
                    head_outputs.append(head_action)
                action_outputs.append(head_action)

                if actions is None:
                    head_log_prob = head_distribution.log_probs(head_action)
                else:
                    head_log_prob = head_distribution.log_probs(actions[i])

                if log_specific_head_probs:
                    #This is just for logging/debugging evaluation episodes
                    if i == 0:
                        actual_action = int(head_action.squeeze().cpu().data.numpy())
                        prob_to_store = np.exp(head_log_prob.squeeze().cpu().data.numpy())
                        num_avail_acs = torch.sum(head_mask).cpu().data.numpy()
                        specific_log_output.append(
                            (None, i, prob_to_store, int(num_avail_acs), actual_action)
                        )
                    else:
                        action_type = action_outputs[0].squeeze().cpu().data.numpy()
                        store_head_prob = False
                        if (action_type == 0 or action_type == 2) and i == 1:
                            store_head_prob = True
                        elif (action_type == 1 and i == 2):
                            store_head_prob = True
                        elif (action_type == 8 and i == 3):
                            store_head_prob = True
                        elif (action_type == 4 and i == 4):
                            store_head_prob = True
                        elif (action_type == 11 and i == 6):
                            store_head_prob = True

                        if store_head_prob:
                            actual_action = int(head_action.squeeze().cpu().data.numpy())
                            prob_to_store = np.exp(head_log_prob.squeeze().cpu().data.numpy())
                            num_avail_acs = torch.sum(head_mask).cpu().data.numpy()
                            specific_log_output.append(
                                (int(action_type), i, prob_to_store, int(num_avail_acs), actual_action)
                            )

                log_prob_mask = torch.ones(main_input.size(0), 1, dtype=torch.float32, device=self.dummy_param.device)
                if self.log_prob_masks[i] is not None:
                    for prev_head_ind, head_type_mask in self.log_prob_masks[i].items():
                        if actions is None:
                            acts_to_mask = action_outputs
                        else:
                            acts_to_mask = actions
                        head_prob_mask = head_type_mask[acts_to_mask[prev_head_ind].squeeze()].view(-1, 1)
                        if prev_head_ind == 4:
                            action_type_mask = (acts_to_mask[0] != ActionTypes.PlayDevelopmentCard).squeeze()
                            head_prob_mask[action_type_mask, ...] = 1.0
                        log_prob_mask *= head_prob_mask

                    head_log_prob *= log_prob_mask
                joint_action_log_prob += head_log_prob
                head_log_probs_filtered.append((log_prob_mask==0).float().detach())

                entropy_head = log_prob_mask * (head_distribution.entropy().view(-1, 1))
                entropy += entropy_head.mean()
            else:
                if actions is None:
                    action_inp = None
                    prev_head_acs = action_outputs
                else:
                    action_inp = actions[i]
                    prev_head_acs = actions
                head_output, action_output, head_log_prob, head_entropy = \
                    head(main_head_inputs, head_mask, custom_inputs, self.log_prob_masks[i], head_log_probs_filtered,
                         prev_head_acs, actions=action_inp, deterministic=deterministic)
                head_outputs.append(head_output)
                action_outputs.append(action_output)
                joint_action_log_prob += head_log_prob
                entropy += head_entropy
                head_log_probs_filtered.append((head_log_prob==0).float().detach())

        if log_specific_head_probs:
            return action_outputs, joint_action_log_prob, entropy, specific_log_output
        return action_outputs, joint_action_log_prob, entropy, None

class ActionHead(nn.Module):
    def __init__(self, main_input_dim, output_dim, custom_inputs={}, type="categorical", mlp_size=None,
                 returns_distribution=True, custom_out_size=0, id=None):
        super(ActionHead, self).__init__()
        self.input_dim = main_input_dim + custom_out_size

        custom_in_dim = 0
        for name, size in custom_inputs.items():
            custom_in_dim += size
        self.output_dim = output_dim
        self.type = type
        self.mlp_size = mlp_size or DEFAULT_MLP_SIZE
        self.returns_distribution = returns_distribution
        self.custom_inputs = custom_inputs
        self.id = id

        if custom_in_dim > 0:
            self.custom_mlp = nn.Linear(custom_in_dim, custom_out_size)
            self.custom_norm = nn.LayerNorm(custom_out_size)

        self.mlp_1 = nn.Linear(self.input_dim, self.mlp_size)
        self.mlp_2 = nn.Linear(self.mlp_size, self.mlp_size)
        self.norm = nn.LayerNorm(self.mlp_size)
        self.relu = nn.ReLU()

        dist_input_size = self.mlp_size
        if type == "categorical":
            self.distribution = Categorical(num_inputs=dist_input_size, num_outputs=output_dim)
        elif type == "normal":
            self.distribution = DiagGaussian(num_inputs=dist_input_size, num_outputs=output_dim)
        else:
            raise NotImplementedError

    def forward(self, main_input, mask, custom_inputs):
        if custom_inputs is not None and len(self.custom_inputs) > 0:
            input_custom = torch.cat([custom_inputs[key] for key in self.custom_inputs.keys()], dim=-1)
            custom_out = self.relu(self.custom_norm(self.custom_mlp(input_custom)))
            input_full = torch.cat([main_input, custom_out], dim=-1)
        else:
            input_full = main_input

        head_input = self.mlp_2(self.relu(self.norm(self.mlp_1(input_full))))

        if self.type == "normal":
            return self.distribution(head_input)
        else:
            return self.distribution(head_input, mask)

class RecurrentActionHead(nn.Module):
    """
    Generic recurrent head for actions like 'Develop' and 'Sell' where multiple selections can be made.
    """
    def __init__(self, main_input_dim, output_dim, max_count, custom_inputs={}, mlp_size=None, id=None):
        super(RecurrentActionHead, self).__init__()
        self.dummy_param = nn.Parameter(torch.empty(0))
        self.main_input_dim = main_input_dim
        self.output_dim = output_dim
        self.max_count = max_count
        self.custom_inputs = custom_inputs
        self.mlp_size = mlp_size or DEFAULT_MLP_SIZE
        self.id = id

        self.input_dim = main_input_dim + output_dim  # Include previous selections

        self.mlp_1 = nn.Linear(self.input_dim, self.mlp_size)
        self.mlp_2 = nn.Linear(self.mlp_size, self.mlp_size)
        self.norm = nn.LayerNorm(self.mlp_size)
        self.relu = nn.ReLU()

        dist_input_size = self.mlp_size

        self.distribution = Categorical(num_inputs=dist_input_size, num_outputs=output_dim)

    def forward(self, main_inputs, mask, custom_inputs, actions=None, deterministic=False):
        actions_out = []
        output = torch.zeros(main_inputs.size(0), self.output_dim, dtype=torch.float32,
                             device=self.dummy_param.device)
        log_prob_sum = 0
        entropy_sum = 0

        for i in range(self.max_count):
            input = torch.cat((main_inputs, output), dim=-1)
            input = self.mlp_2(self.relu(self.norm(self.mlp_1(input))))
            distribution = self.distribution(input, mask)

            if deterministic:
                action = distribution.mode()
            else:
                action = distribution.sample()

            one_hot_action = torch.zeros(main_inputs.size(0), self.output_dim, dtype=torch.float32,
                                         device=self.dummy_param.device)
            if actions is None:
                one_hot_action.scatter_(-1, action, 1.0)
                log_prob = distribution.log_probs(action)
            else:
                one_hot_action.scatter_(-1, actions[:, i].view(-1, 1), 1.0)
                log_prob = distribution.log_probs(actions[:, i])

            output += one_hot_action
            mask = self.update_mask(mask, one_hot_action)  # Implement mask update logic based on action

            entropy = distribution.entropy().view(-1, 1)
            log_prob_sum += log_prob
            entropy_sum += entropy

            actions_out.append(action)

        return output, actions_out, log_prob_sum, entropy_sum.mean()

    def update_mask(self, mask, action):
        # Update the mask based on the selected action
        # This method needs to be implemented based on the game logic
        pass

# Now, define the action heads based on the actions in Brass Birmingham

def build_brass_action_heads(main_input_dim):
    # Action Type Head
    action_type_head = ActionHead(
        main_input_dim=main_input_dim,
        output_dim=ACTION_TYPE_COUNT,
        mlp_size=DEFAULT_MLP_SIZE,
        id="action_type"
    )

    # Discard Card Head (used in multiple actions)
    discard_card_head = ActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_CARDS_IN_HAND,
        mlp_size=DEFAULT_MLP_SIZE,
        id="discard_card"
    )

    # Discard Cards Head (for Scout action)
    discard_cards_head = RecurrentActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_CARDS_IN_HAND,
        max_count=MAX_DISCARD_CARDS_SCOUT,
        mlp_size=DEFAULT_MLP_SIZE,
        id="discard_cards_scout"
    )

    # Canal Location Head
    canal_location_head = ActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_CANAL_LOCATIONS,
        mlp_size=DEFAULT_MLP_SIZE,
        id="canal_location"
    )

    # Rail Location Head
    rail_location_head = ActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_RAIL_LOCATIONS,
        mlp_size=DEFAULT_MLP_SIZE,
        id="rail_location"
    )

    # Second Rail Location Head
    second_rail_location_head = ActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_RAIL_LOCATIONS,
        mlp_size=DEFAULT_MLP_SIZE,
        id="second_rail_location"
    )

    # Coal Source Head
    coal_source_head = ActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_COAL_SOURCES,
        mlp_size=DEFAULT_MLP_SIZE,
        id="coal_source"
    )

    # Beer Source Head
    beer_source_head = ActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_BEER_SOURCES,
        mlp_size=DEFAULT_MLP_SIZE,
        id="beer_source"
    )

    # Build Location Head
    build_location_head = ActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_BUILD_LOCATIONS,
        mlp_size=DEFAULT_MLP_SIZE,
        id="build_location"
    )

    # Iron Source Head
    iron_source_head = ActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_IRON_SOURCES,
        mlp_size=DEFAULT_MLP_SIZE,
        id="iron_source"
    )

    # Industry Type Head (for Develop action)
    industry_type_head = ActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_INDUSTRIES,
        mlp_size=DEFAULT_MLP_SIZE,
        id="industry_type"
    )

    # Recurrent Develop Head
    recurrent_develop_head = RecurrentActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_INDUSTRIES,
        max_count=2,  # Max 2 industries can be developed
        mlp_size=DEFAULT_MLP_SIZE,
        id="recurrent_develop"
    )

    # Recurrent Sell Head
    recurrent_sell_head = RecurrentActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_BUILDINGS,
        max_count=MAX_BUILDINGS,  # Adjust based on game rules
        mlp_size=DEFAULT_MLP_SIZE,
        id="recurrent_sell"
    )

    # Merchant Head (for Sell action)
    merchant_head = ActionHead(
        main_input_dim=main_input_dim,
        output_dim=MAX_MERCHANTS,
        mlp_size=DEFAULT_MLP_SIZE,
        id="merchant_head"
    )

    # Continue/Stop Head (for recurrent actions)
    continue_stop_head = ActionHead(
        main_input_dim=main_input_dim,
        output_dim=2,  # Continue or Stop
        mlp_size=DEFAULT_MLP_SIZE,
        id="continue_stop"
    )

    # Collect all action heads
    action_heads = [
        action_type_head,        # 0
        discard_card_head,       # 1
        discard_cards_head,      # 2
        canal_location_head,     # 3
        rail_location_head,      # 4
        second_rail_location_head,  # 5
        coal_source_head,        # 6
        beer_source_head,        # 7
        build_location_head,     # 8
        iron_source_head,        # 9
        industry_type_head,      # 10
        recurrent_develop_head,  # 11
        recurrent_sell_head,     # 12
        merchant_head,           # 13
        continue_stop_head       # 14
    ]

    return action_heads

# Now define the autoregressive map and other configurations
def build_autoregressive_map():
    # Map of dependencies between action heads
    # Each entry is a list of [previous_head_index, transformation_function]
    # For example, if head 1 depends on the output of head 0, you specify that here
    # For simplicity, here's a placeholder; you need to fill in based on your action dependencies
    autoregressive_map = [
        [[-1, None]],  # action_type_head does not depend on any previous head
        [[0, None]],   # discard_card_head depends on action_type_head
        [[0, None]],   # discard_cards_head depends on action_type_head
        [[0, None]],   # canal_location_head depends on action_type_head
        [[0, None]],   # rail_location_head depends on action_type_head
        [[4, None]],   # second_rail_location_head depends on first rail location
        [[0, None]],   # coal_source_head depends on action_type_head
        [[0, None]],   # beer_source_head depends on action_type_head
        [[1, None]],   # build_location_head depends on discard_card_head
        [[0, None]],   # iron_source_head depends on action_type_head
        [[0, None]],   # industry_type_head depends on action_type_head
        [[0, None]],   # recurrent_develop_head depends on action_type_head
        [[0, None]],   # recurrent_sell_head depends on action_type_head
        [[12, None]],  # merchant_head depends on recurrent_sell_head
        [[0, None]]    # continue_stop_head depends on action_type_head
    ]
    return autoregressive_map

# Build the action masks and other configurations as needed

def build_brass_action_module(main_input_dim):
    action_heads = build_brass_action_heads(main_input_dim)
    autoregressive_map = build_autoregressive_map()
    log_prob_masks = {}  # Define as needed
    type_conditional_action_masks = {}  # Define as needed

    action_module = MultiActionHeadsBrass(
        action_heads=action_heads,
        autoregressive_map=autoregressive_map,
        main_input_dim=main_input_dim,
        log_prob_masks=log_prob_masks,
        type_conditional_action_masks=type_conditional_action_masks
    )
    return action_module

