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
        joint_states=None,
        joint_actions=None,
        joint_next_states=None,
        active_mask=None,
        next_active_mask=None,
        agent_index=None,
    ):
        experience = (
            s,
            cs,
            a,
            r,
            t,
            s2,
            cs2,
            joint_states,
            joint_actions,
            joint_next_states,
            active_mask,
            next_active_mask,
            agent_index,
        )
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

    def sample_local_critic_joint_batch(self, batch_size):
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
        joint_states_batch = np.array(
            [_[7] if len(_) > 7 else None for _ in batch], dtype=object
        )
        joint_actions_batch = np.array(
            [_[8] if len(_) > 8 else None for _ in batch], dtype=object
        )
        joint_next_states_batch = np.array(
            [_[9] if len(_) > 9 else None for _ in batch], dtype=object
        )
        active_mask_batch = np.array(
            [_[10] if len(_) > 10 else None for _ in batch], dtype=object
        )
        next_active_mask_batch = np.array(
            [_[11] if len(_) > 11 else None for _ in batch], dtype=object
        )
        agent_index_batch = np.array(
            [_[12] if len(_) > 12 else None for _ in batch], dtype=object
        )

        return (
            s_batch,
            cs_batch,
            a_batch,
            r_batch,
            t_batch,
            s2_batch,
            cs2_batch,
            joint_states_batch,
            joint_actions_batch,
            joint_next_states_batch,
            active_mask_batch,
            next_active_mask_batch,
            agent_index_batch,
        )

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
