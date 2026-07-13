"""
Data structure for implementing experience replay
Author: Patrick Emami
"""
import random
from collections import deque

import numpy as np


class ReplayBuffer(object):
    def __init__(self, buffer_size, random_seed=123):
        """
        The right side of the deque contains the most recent experiences
        """
        self.buffer_size = buffer_size
        self.count = 0
        self.buffer = deque()
        random.seed(random_seed)

    def add(self, s, a, r, t, s2):
        experience = (s, a, r, t, s2)
        if self.count < self.buffer_size:
            self.buffer.append(experience)
            self.count += 1
        else:
            self.buffer.popleft()
            self.buffer.append(experience)

    def add_local_critic(
        self,
        s,
        cs,
        a,
        r,
        t,
        s2,
        cs2,
    ):
        experience = (s, cs, a, r, t, s2, cs2)
        if self.count < self.buffer_size:
            self.buffer.append(experience)
            self.count += 1
        else:
            self.buffer.popleft()
            self.buffer.append(experience)

    def size(self):
        return self.count

    def sample_batch(self, batch_size):
        batch = []

        if self.count < batch_size:
            batch = random.sample(self.buffer, self.count)
        else:
            batch = random.sample(self.buffer, batch_size)

        s_batch = np.array([_[0] for _ in batch])
        a_batch = np.array([_[1] for _ in batch])
        r_batch = np.array([_[2] for _ in batch]).reshape(-1, 1)
        t_batch = np.array([_[3] for _ in batch]).reshape(-1, 1)
        s2_batch = np.array([_[4] for _ in batch])

        return s_batch, a_batch, r_batch, t_batch, s2_batch

    def sample_local_critic_batch(self, batch_size):
        if self.count < batch_size:
            batch = random.sample(self.buffer, self.count)
        else:
            batch = random.sample(self.buffer, batch_size)

        s_batch = np.array([_[0] for _ in batch])
        cs_batch = np.array([_[1] for _ in batch])
        a_batch = np.array([_[2] for _ in batch])
        r_batch = np.array([_[3] for _ in batch]).reshape(-1, 1)
        t_batch = np.array([_[4] for _ in batch]).reshape(-1, 1)
        s2_batch = np.array([_[5] for _ in batch])
        cs2_batch = np.array([_[6] for _ in batch])

        return s_batch, cs_batch, a_batch, r_batch, t_batch, s2_batch, cs2_batch

    def clear(self):
        self.buffer.clear()
        self.count = 0

    def state_dict(self):
        return {
            "buffer_size": self.buffer_size,
            "count": self.count,
            "buffer": list(self.buffer),
        }

    def load_state_dict(self, state):
        self.buffer_size = state["buffer_size"]
        self.count = state["count"]
        self.buffer = deque(state["buffer"], maxlen=None)
