Here's an article that explains how to implement an reinforcement learning module for the board game Settlers of Catan:
```
Dealing with the Action Space
The key ideas to deal with the action space was to use a combination of different action heads for different types of actions, and to have the simulator generate a corresponding set of masks that prevent invalid actions from ever being selected. The use of different action heads imposes some structure on the action space, which in principle should make training more efficient.
The idea is that the first head will output the action type whilst the other heads will output the quantities that are needed for the particular type of action which is selected. These outputs can then be combined into "composite" actions (when necessary). So if we go back to the "year of plenty" development card example - the first head will output the action type (play development card), then a development card head will output the development card type (year of plenty), and then two separate resource heads will output the two desired resources. This allows us to break down the composite decision into components, with each head free to focus entirely on its part of the decision (conditional on the input from the other heads - so for example the resource heads will be given the context of the decision made by the development card head). This has the advantage of allowing composite actions to be chosen as part of a single "decision" (one pass through the neural network), as well as potentially allowing for much better generalisation since the feedback from the action (in terms of estimated values/advantages) can be applied to each head separately. In the example mentioned, this means that playing the "year of plenty" card can be reinforced directly via the development card head regardless of which resources are actually chosen - which in principle should make the learning process significantly more efficient.

As a quick technical aside, the RL algorithm used (PPO 8 ) requires you to calculate the log-probability of the action taken. Note that this can easily be done with when using multiple action heads. For example imagine a composite action made up of an action type $a_{type}$ and a secondary output from another head that depends on the action type, $a_{head two}$ . We can write the probability of the composite action as:
\[
    P(a_{type}, a_{head two}) = P(a_{head two} | a_{type})P(a_{type})
\]
The first head outputs $P(a_{type})$ and if we feed in the sampled $a_{type}$ to the second head then the second head outputs $P(a_{head two} | a_{type})$. Then the log probability follows simply as:
\[
    logP(a_{type}, a_{head two}) = logP(a_{head two} | a_{type})+logP(a_{type})
\]

So we get the log probability of the composite action simply by summing the log probabilities of each relevant action head!

Having said all of this, using multiple action heads in this way is not trivial, and I will now try and explain in detail how this was implemented in practice. To get started with, I broke the basic actions down into the 13 types described in the table below:

Place Settlement Place Road Upgrade To City Buy DevCard Play DevCard Exchange Resources Propose Trade Respond To Trade Move Robber Roll Dice End Turn Steal Resource Discard Resource

The reinforcement learning agent will operate at the level of these base actions - i.e. each decision the agent makes will correspond to one of these action types. In general a player's turn will be made up of multiple of these base actions which they can take one after the other until they choose the "end turn" action (at which point control will pass to the next player).

As mentioned, the first action head is the one that chooses the type of action (one of the 13 listed above).

The diagram below illustrates what happens. The output from the "observation" module is provided as input to the action head (a two layer fully connected neural network), which outputs a vector of logits (one for each action type). Before turning this into a probability distribution over actions we apply the relevant action mask provided by the simulation. This is a vector of 1s and 0s representing which types of actions are possible in the current state (valid actions are represented by 1.0, invalid actions by 0.0). What we do is then take the log of these action masks (so valid actions are mapped to 0, whilst invalid actions are mapped to negative infinity) and add them to the logits. For the valid action types this will have no effect, but invalid actions will be set to minus infinity. This means that when the softmax is applied their probabilities will be set to zero, ensuring that invalid actions are never selected.



The next head is the "corner" head, which outputs a categorical distribution over the 54 possible corner locations where settlements can in principle be placed (or upgraded to cities). This is only required for the "place settlement" and "upgrade to city" action types (the same head is used for both and the action type is provided as input to the head along with the output of the observation module - so it knows whether it's placing a settlement or upgrading to a city). For all other action types the output of this head will be masked out (note that because we have to train on large batches of data this head always has to be processed, but the output can be masked out depending on the action type chosen). The simulation environment also provides separate action masks for each of the two action types this head can be used for to mask out any invalid actions.

After that we have the "edge" head, which outputs a distribution over the 72 possible edges a road can be placed on. This is obviously only used for the "place road" action type, and is masked out otherwise. The input is simply the observation output (it doesn't explicitly need to receive the action type output because it is only ever used for one type of action and masked out otherwise).

The third head is the "tile" head - giving a distribution over the 19 tiles. This is only ever used with the moving the robber action type. Again its only input is the observation module output.

The fourth head in the "development card" head - giving a distribution over the 5 types of development card (obviously cards that the player does not own are masked out). This is only used with the play development card action type, and again its input is the observation module output.

The fifth head is the "accept/reject deal" head, which is used when the player has been offered a trade by another player. In this case it takes as input both the observation module output and a representation of the proposed trade and outputs a 2-dimensional categorical distribution over the two options (accept or reject).

The sixth head is the "choose player" head. This is used for the steal action type (after the player has moved the robber and is allowed to steal a resource from a player) and also for the propose trade action type (in this case the output of this head will be combined with the outputs of the "trade: to give" head and the "trade: to receive" head). So in this case the head takes both the observation module output and the action type (steal or propose trade) as inputs and outputs a categorical distribution over the available players (ordered clockwise from the decision-making player).

The next two heads are "resource" heads. The first resource head is used for the exchange resource action type (representing the resource to trade) and the play development card action type but only when the development card is "monopoly" or "year of plenty", otherwise it is masked out. The second resource head is also used for the exchange resource action type (representing the resource to receive) and the "year of plenty" development card. As such, these heads take the observation module output, the action type and the development card type (if applicable) as inputs, and output a categorical distribution over the 5 resources in the game.

The next two heads are the most complicated since they represent proposing the resources for a trade. The first of these outputs the resources the player is proposing to give away. The main difficulty here is that in general the trade to be proposed can contain a variable number of resources (on both sides) and so the agent needs a way to be able to choose a variable number of resources (ideally without just considering every possible combination of resources as different actions). The way I decided to approach this was by using a recurrent action head where each pass of the head outputs a probability distribution over the five possible resources plus an additional stop adding resources action. The output of this head is then sampled and added to the "currently proposed trade". Provided the action chosen wasn't the "stop adding resources" action, this updated proposed trade is then fed back into the same action head along with the other inputs (the observation module output and the player's current resources, which is also updated based on the previous output). This allows the agent to iteratively add resources to the proposed trade as many times as it wants (although in practice I set a maximum of 4 resources on each side of the trade). The player's current resources can also be used here as the action mask for this head - ensuring the player never proposes to give away resources they do not actually have. The basic procedure for how this head operates is shown in the figure below:



The secondary trading head operates in a very similar way, with the main difference being that it doesn't need to use the player's current resources as an action mask because this head models the resources the player is proposing to receive. In fact, for simplicity I decided not to use action masks on this head at all - so player's can request any number of resources from the player they are proposing the trade to even if they do not have those resources (in which case they will have to reject the trade). On reflection this is potentially quite inefficient, and especially as learning to trade is potentially one of the most challenging things for an RL Catan agent to learn I do wish I'd done this differently (the reason it's not straightforward is that the mask to use would depend on the output of the "choose player" head which gets a bit fiddly, especially when processing a batch of data. However, given that I'd already gone to the effort of making e.g. the mask used for the corner head depend on the output of the "action type" head this was definitely quite doable).

So the full composite "propose trade" action consists of the output of the action type head, the choose player head and the recurrent "trade: to give" and "trade: to receive" heads.

The final head is the "discard resource" head. Whenever a player has 8 or more resources and a 7 is rolled (by any player) they must discard resources until they only have 7 left. I did consider using a recurrent head here as well - so that a player could choose all of the resources to discard in a single decision (if they had to discard more than one resource). I didn't do this in the end primarily because I thought it would probably be easier to use in the forward search planner (see later section) if each action only involved discarding a single resource, but also because it was a lot simpler to implement this way. The downside is that obviously this leads to the agent having to potentially carry out a large number of decisions if they get into a situation where they need to discard a lot of resources. I'm still unsure as to whether this was a good decision, and this is one of a number of design choices I would have liked to evaluate more thoroughly if I had access to more computational resources!
```
Here's the code for the rl modules modeling the action heads and the whole agent model.

build_agent_model.py
```
"""build and configure the agent neural network module"""

import torch

from RL.models.observation_module import ObservationModule
from RL.models.action_heads_module import ActionHead, RecurrentResourceActionHead, MultiActionHeadsGeneralised
from RL.models.policy import SettlersAgentPolicy

"""constants"""
ACTION_TYPE_COUNT = 13
N_CORNERS = 54
N_EDGES = 72
N_TILES = 19
RESOURCE_DIM = 6
PLAY_DEVELOPMENT_CARD_DIM = 5
N_PLAYERS = 4

"""default values"""
tile_in_dim = 60
tile_model_dim = 64
curr_player_in_dim = 152
other_player_in_dim = 159
dev_card_embed_dim = 16
tile_model_num_heads = 4
observation_out_dim = 512
include_lstm = False
lstm_dim = 256
proj_dev_card_dim = 25
dev_card_model_num_heads = 4
tile_encoder_num_layers = 2
proj_tile_dim = 25
action_mlp_sizes = [128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128]
max_propose_res = 4 #maximum resources to include in proposition


def build_agent_model(tile_in_dim=tile_in_dim, tile_model_dim = tile_model_dim, curr_player_in_dim = curr_player_in_dim,
                      other_player_in_dim=other_player_in_dim, dev_card_embed_dim=dev_card_embed_dim,
                      tile_model_num_heads=tile_model_num_heads, observation_out_dim=observation_out_dim,
                      lstm_dim=lstm_dim, proj_dev_card_dim=proj_dev_card_dim,
                      dev_card_model_num_heads=dev_card_model_num_heads, tile_encoder_num_layers=tile_encoder_num_layers,
                      proj_tile_dim=proj_tile_dim, action_mlp_sizes=action_mlp_sizes,
                      max_propose_res=max_propose_res, device="cpu"):

    observation_module = ObservationModule(tile_in_dim=tile_in_dim, tile_model_dim=tile_model_dim,
                                           curr_player_main_in_dim=curr_player_in_dim,
                                           other_player_main_in_dim=other_player_in_dim,
                                           dev_card_embed_dim=dev_card_embed_dim, dev_card_model_dim=dev_card_embed_dim,
                                           observation_out_dim=observation_out_dim, tile_model_num_heads=tile_model_num_heads,
                                           proj_dev_card_dim=proj_dev_card_dim,
                                           dev_card_model_num_heads=dev_card_model_num_heads,
                                           tile_encoder_num_layers=tile_encoder_num_layers, proj_tile_dim=proj_tile_dim)

    action_head_in_dim = observation_out_dim
    if include_lstm:
        action_head_in_dim += lstm_dim

    """set up action heads"""
    action_type_head = ActionHead(action_head_in_dim, ACTION_TYPE_COUNT, mlp_size=action_mlp_sizes[0], id="action_type")
    corner_head = ActionHead(action_head_in_dim + 2, N_CORNERS, mlp_size=action_mlp_sizes[1], id="corner_head")# plus 2 for type
    edge_head = ActionHead(action_head_in_dim, N_EDGES + 1, mlp_size=action_mlp_sizes[2], id="edge_head")
    tile_head = ActionHead(action_head_in_dim, N_TILES, mlp_size=action_mlp_sizes[3], id="tile_head")
    play_development_card_head = ActionHead(action_head_in_dim, PLAY_DEVELOPMENT_CARD_DIM, mlp_size=action_mlp_sizes[4],
                                            id="development_card_head")
    accept_reject_head = ActionHead(action_head_in_dim, 2, custom_inputs={"proposed_trade": 2 * RESOURCE_DIM},
                                    mlp_size=action_mlp_sizes[5], id="accept_reject_head", custom_out_size=32)
    player_head = ActionHead(action_head_in_dim + 2, N_PLAYERS - 1, mlp_size=action_mlp_sizes[6], id="player_head")
    propose_give_res_head = RecurrentResourceActionHead(action_head_in_dim, RESOURCE_DIM, max_count=max_propose_res,
                                                        mlp_size=action_mlp_sizes[7], id="propose_give_head",
                                                        mask_based_on_curr_res=True)
    propose_receive_res_head = RecurrentResourceActionHead(action_head_in_dim + RESOURCE_DIM, RESOURCE_DIM,
                                                           max_count=max_propose_res, mlp_size=action_mlp_sizes[8],
                                                           id="propose_receive_head", mask_based_on_curr_res=False)
    exchange_res_head = ActionHead(action_head_in_dim + 4, RESOURCE_DIM - 1, mlp_size=action_mlp_sizes[9], id="exchange_res_head")
    receive_res_head = ActionHead(action_head_in_dim + 4 + RESOURCE_DIM - 1, RESOURCE_DIM - 1, mlp_size=action_mlp_sizes[10],
                                  id="receive_res_head")
    discard_head = ActionHead(action_head_in_dim, RESOURCE_DIM - 1, mlp_size=action_mlp_sizes[10], id="discard_res_head")

    action_heads = [action_type_head, corner_head, edge_head, tile_head, play_development_card_head, accept_reject_head,
                    player_head, propose_give_res_head, propose_receive_res_head, exchange_res_head, receive_res_head,
                    discard_head]

    """action maps - will hopefully write up full details of how this all works because it's confusing."""
    autoregressive_map = [
        [[-1, None]],
        [[-1, None], [0, lambda x: torch.cat((x[:, 0].view(-1, 1) > 0, x[:, 2].view(-1, 1) > 0), dim=-1).float()]],
        [[-1, None]],
        [[-1, None]],
        [[-1, None]],
        [[-1, None]],
        [[-1, None], [0, lambda x: torch.cat((x[:, 6].view(-1, 1) > 0, x[:, 11].view(-1, 1) > 0), dim=-1).float()]],
        [[-1, None]],
        [[-1, None], [7, None]],
        [[-1, None], [0, lambda x: torch.cat((x[:, 4].view(-1, 1) > 0, x[:, 5].view(-1, 1) > 0), dim=-1).float()],
         [4, lambda x: torch.cat((x[:, 2].view(-1, 1) > 0, x[:, 4].view(-1, 1) > 0), dim=-1).float()]],
        [[-1, None], [0, lambda x: torch.cat((x[:, 4].view(-1, 1) > 0, x[:, 5].view(-1, 1) > 0), dim=-1).float()],
         [4, lambda x: torch.cat((x[:, 2].view(-1, 1) > 0, x[:, 4].view(-1, 1) > 0), dim=-1).float()], [9, None]],
        [[-1, None]]
    ]

    """
    action-conditional masks:

    corner:
    [[settlement], [city], [dummy]] (action type)

    player:
    [[propose trade], [steal]] (action type)

    exchange res:
    [[exchange res], [dummy], [monopoly], [year of plenty]]

    """
    type_conditional_action_masks = [
        {},
        {0: torch.tensor([0, 2, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2], dtype=torch.long, device=device)},
        {},
        {},
        {},
        {},
        {0: torch.tensor([2, 2, 2, 2, 2, 2, 0, 2, 2, 2, 2, 1, 2], dtype=torch.long, device=device)},
        {},
        {},
        {0: torch.tensor([1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1], dtype=torch.long, device=device),
         4: torch.tensor([1, 1, 3, 1, 2], dtype=torch.long, device=device)},
        {},
        {}
    ]

    """
    Log-prob masks
    """
    log_prob_masks = [
        None,
        {0: torch.tensor([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=torch.long, device=device)},
        {0: torch.tensor([0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=torch.long, device=device)},
        {0: torch.tensor([0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0], dtype=torch.long, device=device)},
        {0: torch.tensor([0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0], dtype=torch.long, device=device)},
        {0: torch.tensor([0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0], dtype=torch.long, device=device)},
        {0: torch.tensor([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0], dtype=torch.long, device=device)},
        {0: torch.tensor([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0], dtype=torch.long, device=device)},
        {0: torch.tensor([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0], dtype=torch.long, device=device)},
        {0: torch.tensor([0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0], dtype=torch.long, device=device),
         4: torch.tensor([0, 0, 1, 0, 1], dtype=torch.long, device=device)},
        {0: torch.tensor([0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0], dtype=torch.long, device=device),
         4: torch.tensor([0, 0, 1, 0, 0], dtype=torch.long, device=device)},
        {0: torch.tensor([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1], dtype=torch.long, device=device)}
    ]

    multi_action_head = MultiActionHeadsGeneralised(action_heads, autoregressive_map, lstm_dim, log_prob_masks,
                                                    type_conditional_action_masks).to(device)


    """Full model"""
    agent = SettlersAgentPolicy(observation_module, multi_action_head, include_lstm=include_lstm,
                          observation_out_dim=observation_out_dim, lstm_size=lstm_dim).to(device)
    return agent
```
action_heads_module.py:
```
import math
import numpy as np
import torch
import torch.nn as nn

from RL.distributions import Categorical, DiagGaussian
from game.enums import ActionTypes

DEFAULT_MLP_SIZE = 64

class MultiActionHeadsGeneralised(nn.Module):
    def __init__(self, action_heads, autoregressive_map, main_input_dim, log_prob_masks={},
                 type_conditional_action_masks=None):
        super(MultiActionHeadsGeneralised, self).__init__()
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
        self.mlp_size = mlp_size
        self.returns_distribution = returns_distribution
        self.custom_inputs = custom_inputs
        self.id = id

        if custom_in_dim > 0:
            self.custom_mlp = nn.Linear(custom_in_dim, custom_out_size)
            self.custom_norm = nn.LayerNorm(custom_out_size)

        self.mlp_1 = nn.Linear(self.input_dim, mlp_size)
        self.mlp_2 = nn.Linear(mlp_size, mlp_size)
        self.norm = nn.LayerNorm(mlp_size)
        self.relu = nn.ReLU()

        dist_input_size = mlp_size
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



class RecurrentResourceActionHead(nn.Module):
    """specific to the Settler's environment. For trading resources. Assume zeroth entry is stop."""
    def __init__(self, main_input_dim, available_resources_dim, max_count=4, custom_inputs={}, mlp_size=None,
                 id=None, mask_based_on_curr_res=True):
        super(RecurrentResourceActionHead, self).__init__()
        self.dummy_param = nn.Parameter(torch.empty(0))
        self.main_input_dim = main_input_dim
        self.available_resources_dim = available_resources_dim
        self.max_count = max_count
        self.custom_inputs = custom_inputs
        self.mlp_size = mlp_size
        self.returns_distribution = False
        self.mask_based_on_curr_res = mask_based_on_curr_res
        self.input_dim = main_input_dim + available_resources_dim
        self.id = id


        self.mlp_1 = nn.Linear(self.input_dim, mlp_size)
        self.mlp_2 = nn.Linear(mlp_size, mlp_size)
        self.norm = nn.LayerNorm(mlp_size)
        self.relu = nn.ReLU()

        dist_input_size = mlp_size

        self.distribution = Categorical(num_inputs=dist_input_size, num_outputs=available_resources_dim)

    def forward(self, main_inputs, head_mask, custom_inputs, log_prob_masks, filtered_heads, prev_head_action_outs,
                actions=None, deterministic=False, count=None):
        """head mask here is just a placeholder. mask is based on available resources"""
        actions_out = []
        output = torch.zeros(main_inputs.size(0), self.available_resources_dim, dtype=torch.float32,
                             device=self.dummy_param.device)
        log_prob_sum = 0
        entropy_sum = 0
        current_resources = custom_inputs["current_resources"]  # in one-hot encoded form where first entry is 0 and represents stop/no res
        if self.mask_based_on_curr_res:
            mask = (current_resources > 0).float()
        else:
            mask = torch.ones_like(current_resources, dtype=torch.float32, device=self.dummy_param.device)
        res_sum = torch.sum(current_resources, dim=-1)
        zero_res_mask = (res_sum == 0)
        mask[:, 0] = 0.0
        mask[zero_res_mask, 0] = 1.0 #allow no res as first res if sum of current res = 0 (logits will be masked out anyway but leads to error o/w)
        if count is None:
            count = self.max_count
        for i in range(count):
            input = torch.cat((main_inputs, output), dim=-1)
            input = self.mlp_2(self.relu(self.norm(self.mlp_1(input))))
            distribution = self.distribution(input, mask)

            if deterministic:
                action = distribution.mode()
            else:
                action = distribution.sample()

            one_hot_action = torch.zeros(main_inputs.size(0), self.available_resources_dim, dtype=torch.float32,
                                         device=self.dummy_param.device)
            if actions is None:
                one_hot_action.scatter_(-1, action, 1.0)
                log_prob = distribution.log_probs(action)
            else:
                one_hot_action.scatter_(-1, actions[:, i].view(-1, 1), 1.0)
                log_prob = distribution.log_probs(actions[:, i])
            output += one_hot_action
            current_resources = torch.clamp(current_resources - one_hot_action, 0, math.inf)

            if self.mask_based_on_curr_res:
                mask = (current_resources > 0).float()
            else:
                mask = torch.ones_like(current_resources, dtype=torch.float32, device=self.dummy_param.device)
            mask[:, 0] = 1.0

            entropy = distribution.entropy().view(-1, 1)

            if i > 0:
                if actions is not None:
                    log_prob_mask = (actions[:, i-1] > 0).float().view(-1, 1)
                else:
                    log_prob_mask = (actions_out[-1][:, 0] > 0).float().view(-1, 1)
                log_prob *= log_prob_mask
                entropy *= log_prob_mask

            log_prob_sum += log_prob
            entropy_sum += entropy

            actions_out.append(action)

            output[:, 0] = 0.0

        #now apply log_prob_mask from other heads
        log_prob_mask = 1
        for prev_head_ind, head_type_mask in log_prob_masks.items():
            head_prob_mask = head_type_mask[prev_head_action_outs[prev_head_ind].squeeze()].view(-1, 1)
            log_prob_mask *= head_prob_mask
        log_prob_sum *= log_prob_mask
        entropy_sum *= log_prob_mask

        return output, actions_out, log_prob_sum, entropy_sum.mean()
```


Your task is to implement a similar structure for the Brass Burmingham game environment. 
Consider the following constirctions specific to Brass Burmingham. 

The game has two phases Canal and Railroad.
Players always have 2 actions to take each round of the game except for the very first round where they have only one action of the game.
Each round they have to spend a card from their hand (usually 8 cards before they start running out) and take new ones from the deck (42 cards in the deck total). When players run out of cards the phase ends. 
You have to take note of the action types that players can take and choices for each action when designing the structure of action heads. 

Here are the potential actions the players can take:
```
## PlaceCanal 
place a road during canal phase
Inputs: 
- Any of the 8 possible cards in hand.
- Number of available road locations out of 39 (total for canal and rail).
- Any of the 8 possible cards in hand to discard for the action.

## PlaceRailRoad 
Inputs: 
- Number of available road locations out of 39 (total for canal and rail).
- Coal source - Total 16 choices. 15 for all possible coal source building and 1 for market. Should be masked based on the location of the road as the coal source has to be connected to the road.
- Any of the 8 possible cards in hand to discard for the action.

## PlaceSecondRoad 
Can be done as a continuation of PlaceRailRoad action so doesnt need a card for it. Considering the player has enough resources available for it.
Inputs:
- Number of available road locations out of 39 (total for canal and rail). The one selected in PlaceRailRoad action should be masked 
- Coal source - Total 16 choices. 15 for all possible coal source building and 1 for market. Should be masked based on the location of the road as the coal source has to be connected to the second road. 
- Beer source - Total 12 choices for all possible locations of beer (masked with beer that is build and has beer and  belongs to the player) + 1 beer for merchant which will always be masked out in this case. Will be masked wit hbeer that is connected to the road.


## BuildIndustry
Inputs: 
- Build Location - some of 76 build locations where build is available.
- Coal source - Total 16 choices. 15 for all possible coal source building and 1 for market. Should be masked based on the location of the build as the coal source has to be connected to the building.
- Iron source - Total 10 choices. 9 for all possible iron source building with iron on it and 1 for market. Iron doesnt have to be connected to the bulding so can choose between all buildings with iron on it or market if has money. 
- cards in hand masked with the ones that can be used for that build location.

## DevelopOneIndustry 
Inputs: 
- Any of the 5 potential industries that could be  developed. Masked with the ones that can be developed right now. 
- Iron source - Total 10 choices. 9 for all possible iron source building with iron on it and 1 for market. Can choose from from all buildings with iron on it or market if has money. 
- Any of the 8 possible cards in hand to discard for action
## DevelopTwoIndustries
Can be done as a continuation of DevelopOneIndustry action. Considering the player has enough resources available for it. Does not need to discard a card for it
Inputs: 
- Any of the 5 potential industries that could be  developed. Masked with the ones that can be developed right now. 
- Iron source - Total 10 choices. 9 for all possible iron source building with iron on it and 1 for market. Can choose from from all buildings with iron on it or market if has money. 
## Sell
This might need to be  recurrent as the player can select multiple tuples  of (Building, Merchant, BeerSource) to sell in one action and the model will be encouraged in the policy to do multiiple sell actions at once.
Inputs:
- Building - One of potential 41 market buildings masked with the ones available for selling. 
- Merchant - One of 6 total merchants. Masked with the ones the building selected is connected to.
- BeerSource - Total 12 choices for all possible locations of beer (masked with beer that is build and has beer and  belongs to the player) + 1 potential beer from the merchant. Will be masked based on selected building and the merchant selected.
- Any of 8 cards in hand to discard for the whole action. Should be at the end.

## Loan
- Any of 8 cards in hand to discard for the whole action.
## Scout = 8
- Select 3 out of 8 possible cards in hand to discard for action
```

Use this information to design the action heads structure for Brass Burmingham RL agent.