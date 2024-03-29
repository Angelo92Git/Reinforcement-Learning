from math import log
import gym
import numpy as np
import utils.envs, utils.seed, utils.buffers, utils.torch
import torch, random
from torch import nn
import copy
import tqdm
import matplotlib.pyplot as plt
import warnings
import argparse

warnings.filterwarnings("ignore")

# Proximal Policy Optimization

parser = argparse.ArgumentParser()

#either:
# cartpole - default cartpole environment
# mountain_car - default mountain car environment
# mountain_car_mod - mountain car environment with modified reward
parser.add_argument('--mode', type=str, default="cartpole") 

args = parser.parse_args()


# Constants
SEED = 1
t = utils.torch.TorchHelper()
DEVICE = t.device

#for cartpole
if args.mode == "cartpole":
    OBS_N = 4               # State space size
    ACT_N = 2               # Action space size
    ENV_NAME = "CartPole-v0"
    GAMMA = 1.0               # Discount factor in episodic reward objective
    LEARNING_RATE1 = 5e-4     # Learning rate for value optimizer
    LEARNING_RATE2 = 5e-4     # Learning rate for actor optimizer
    POLICY_TRAIN_ITERS = 10   # Training epochs

elif "mountain_car" in args.mode:
    OBS_N = 2
    ACT_N = 3
    ENV_NAME = "MountainCar-v0"
    GAMMA = 0.9               # Discount factor in episodic reward objective
    LEARNING_RATE1 = 1e-3     # Learning rate for value optimizer
    LEARNING_RATE2 = 1e-3     # Learning rate for actor optimizer
    POLICY_TRAIN_ITERS = 5   # Training epochs
   
EPOCHS = 150              # Total number of epochs to learn over
EPISODES_PER_EPOCH = 1    # Episodes per epoch
TEST_EPISODES = 10        # Test episodes
HIDDEN = 32               # Hidden size
CLIP_PARAM = 0.1          # Clip parameter


# Create environment
utils.seed.seed(SEED)
env = gym.make(ENV_NAME)
env.reset(seed=SEED)

# Networks
V = torch.nn.Sequential(
    torch.nn.Linear(OBS_N, HIDDEN), torch.nn.ReLU(),
    torch.nn.Linear(HIDDEN, HIDDEN), torch.nn.ReLU(),
    torch.nn.Linear(HIDDEN, 1)
).to(DEVICE)
pi = torch.nn.Sequential(
    torch.nn.Linear(OBS_N, HIDDEN), torch.nn.ReLU(),
    torch.nn.Linear(HIDDEN, HIDDEN), torch.nn.ReLU(),
    torch.nn.Linear(HIDDEN, ACT_N)
).to(DEVICE)

# Optimizers
OPT1 = torch.optim.Adam(V.parameters(), lr = LEARNING_RATE1)
OPT2 = torch.optim.Adam(pi.parameters(), lr = LEARNING_RATE2)

# Policy
def policy(env, obs):
    probs = torch.nn.Softmax(dim=-1)(pi(t.f(obs)))
    return np.random.choice(ACT_N, p = probs.cpu().detach().numpy())

# Training function
# S = tensor of states observed in the episode/ batch of episodes
# A = tensor of actions taken in episode/ batch of episodes
# return = tensor where nth element is \sum^{T-n}_0 gamma^n * reward (return at step n of episode)
# old_log_probs = tensor of pi(a | s) for policy the trajectory was collected under
def train(S,A,returns, old_log_probs):

    ###############################
    # YOUR CODE HERE:

    # Implement the training of the value function
    # Use the same implementation you did in REINFORCE_Baseline.py for estimating the advantage function
    # (instead of following the PPO slides)

    delta = np.zeros(len(S))
    for step in range(len(S)):
        OPT1.zero_grad()
        with torch.no_grad():
            delta[step] = returns[step] - V(S[step]).detach()
        objective1 = -(delta[step])*V(S[step])
        objective1.backward()
        OPT1.step()

    # PPO 
    # gradient ascent for POLICY_TRAIN_ITERS steps
    for i in range(POLICY_TRAIN_ITERS):
        # implement objective and update for policy
        # follow the slides for this

        OPT2.zero_grad()
        Adv = torch.tensor(delta).detach()
        new_log_probs = torch.nn.LogSoftmax(dim=-1)(pi(S)).gather(1, A.view(-1,1)).view(-1)
        prob_ratio = torch.exp(new_log_probs - old_log_probs)
        objective = -torch.mean(torch.min(prob_ratio*Adv, torch.clip(prob_ratio, min=1-CLIP_PARAM, max=1+CLIP_PARAM)*Adv))
        objective.backward()
        OPT2.step()



        
    #################################

# Play episodes
Rs = [] 
last25Rs = []
print("Training:")
pbar = tqdm.trange(EPOCHS)
for epi in pbar:

    all_S, all_A = [], []
    all_returns = []
    for epj in range(EPISODES_PER_EPOCH):
        
        # Play an episode and log episodic reward
        S, A, R = utils.envs.play_episode(env, policy)
        
        # modify the reward for "mountain_car_mod" mode
        # replace reward with the height of the car (which is first component of state)
        if args.mode == "mountain_car_mod":
            R = [s[0] for s in S[:-1]]
            

        all_S += S[:-1] # ignore last state
        all_A += A
        
        # Create returns 
        discounted_rewards = copy.deepcopy(R)
        for i in range(len(R)-1)[::-1]:
            discounted_rewards[i] += GAMMA * discounted_rewards[i+1]
        discounted_rewards = t.f(discounted_rewards)
        all_returns += [discounted_rewards]

    Rs += [sum(R)]
    S, A = t.f(np.array(all_S)), t.l(np.array(all_A))
    returns = torch.cat(all_returns, dim=0).flatten()

    # pi(a |s) for trajectories observed above
    log_probs = torch.nn.LogSoftmax(dim=-1)(pi(S)).gather(1, A.view(-1, 1)).view(-1)

    # train
    train(S, A, returns, log_probs.detach())

    # Show mean episodic reward over last 25 episodes
    last25Rs += [sum(Rs[-25:])/len(Rs[-25:])]
    pbar.set_description("R25(%g, mean over 10 episodes)" % (last25Rs[-1]))
  
pbar.close()
print("Training finished!")

# Plot the reward
N = len(last25Rs)
plt.plot(range(N), last25Rs, 'b')
plt.xlabel('Episode')
plt.ylabel('Reward (averaged over last 25 episodes)')
plt.title("PPO, mode: " + args.mode)
plt.savefig("images/ppo-"+args.mode+".png")
print("Episodic reward plot saved!")

# Play test episodes
print("Testing:")
testRs = []
for epi in range(TEST_EPISODES):
    S, A, R = utils.envs.play_episode(env, policy, render = False)
    
    # modify the reward for "mountain_car_mod" mode
    # replace reward with the height of the car (which is first component of state)
    if "mountain_car" in args.mode:
        R = [s[0] for s in S[:-1]]

    testRs += [sum(R)]
    print("Episode%02d: R = %g" % (epi+1, sum(R)))

if "mountain_car" in args.mode:
    print("Height achieved: %.2f ± %.2f" % (np.mean(testRs), np.std(testRs)))
else:
    print("Eval score: %.2f ± %.2f" % (np.mean(testRs), np.std(testRs)))
env.close()