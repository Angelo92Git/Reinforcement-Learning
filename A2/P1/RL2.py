import numpy as np
import MDP

class RL2:
    def __init__(self,mdp,sampleReward):
        '''Constructor for the RL class

        Inputs:
        mdp -- Markov decision process (T, R, discount)
        sampleReward -- Function to sample rewards (e.g., bernoulli, Gaussian).
        This function takes one argument: the mean of the distributon and 
        returns a sample from the distribution.
        '''

        self.mdp = mdp
        self.sampleReward = sampleReward

    def sampleRewardAndNextState(self,state,action):
        '''Procedure to sample a reward and the next state
        reward ~ Pr(r)
        nextState ~ Pr(s'|s,a)

        Inputs:
        state -- current state
        action -- action to be executed

        Outputs: 
        reward -- sampled reward
        nextState -- sampled next state
        '''

        reward = self.sampleReward(self.mdp.R[action,state])
        cumProb = np.cumsum(self.mdp.T[action,state,:])
        nextState = np.where(cumProb >= np.random.rand(1))[0][0]
        return [reward,nextState]

    def epsilonGreedyBandit(self,nIterations):
        '''Epsilon greedy algorithm for bandits (assume no discount factor).  Use epsilon = 1 / # of iterations.

        Inputs:
        nIterations -- # of arms that are pulled

        Outputs: 
        empiricalMeans -- empirical average of rewards for each arm (array of |A| entries)
        '''

        empiricalMeans = np.zeros(self.mdp.nActions)
        a_count = np.zeros(self.mdp.nActions)
        iter = 0

        # Begin epsilon-greedy strategy
        for iter in range(nIterations):
            epsilon = 1/(iter + 1)
            if np.random.rand(1)[0] < epsilon:
                a = np.random.choice(range(self.mdp.nActions))
            else:
                a = empiricalMeans.argmax()

            a_count[a] += 1 
            r, _ = self.sampleRewardAndNextState(0,a)
            empiricalMeans[a] = (empiricalMeans[a]*(a_count[a]-1) + r)/a_count[a]

        return empiricalMeans

    def thompsonSamplingBandit(self,prior,nIterations,k=1):
        '''Thompson sampling algorithm for Bernoulli bandits (assume no discount factor)

        Inputs:
        prior -- initial beta distribution over the average reward of each arm (|A|x2 matrix such that prior[a,0] is the alpha hyperparameter for arm a and prior[a,1] is the beta hyperparameter for arm a)  
        nIterations -- # of arms that are pulled
        k -- # of sampled average rewards

        Outputs: 
        empiricalMeans -- empirical average of rewards for each arm (array of |A| entries)
        '''

        empiricalMeans = np.zeros(self.mdp.nActions)
        
        for iter in range(nIterations):   
            for a_sampling in range(self.mdp.nActions): 
                samples = np.random.beta(*prior[a_sampling],k) 
                empiricalMeans[a_sampling] = np.mean(samples)

            a = empiricalMeans.argmax()
            r, _ = self.sampleRewardAndNextState(0,a)
            if r == 1:
                prior[a,0] += 1
            elif r == 0:
                prior[a,1] += 1

        return empiricalMeans

    def UCBbandit(self,nIterations):
        '''Upper confidence bound algorithm for bandits (assume no discount factor)

        Inputs:
        nIterations -- # of arms that are pulled

        Outputs: 
        empiricalMeans -- empirical average of rewards for each arm (array of |A| entries)
        '''

        empiricalMeans = np.zeros(self.mdp.nActions)
        a_count = np.zeros(self.mdp.nActions)

        for a in range(self.mdp.nActions):
            empiricalMeans[a], _ = self.sampleRewardAndNextState(0,a)
            a_count[a] += 1 

        for iter in range(nIterations-self.mdp.nActions):
            ucb = empiricalMeans + np.sqrt((2*np.log(iter+self.mdp.nActions))/a_count)
            a = ucb.argmax()
            r, _ = self.sampleRewardAndNextState(0,a)
            empiricalMeans[a] = (a_count[a]*empiricalMeans[a]+r)/(a_count[a]+1)
            a_count[a] += 1 


        return empiricalMeans