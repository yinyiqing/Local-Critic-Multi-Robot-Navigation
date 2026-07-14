import random
from collections import deque

import numpy as np


class SequenceReplayBuffer:
    GROUPS = ("standard", "pair", "three")

    def __init__(self, capacity, seed=0, group_ratios=None):
        self.capacity = int(capacity)
        self.rng = random.Random(seed)
        self.group_ratios = self._normalize_ratios(group_ratios)
        self.entries = {}
        self.group_ids = {}
        self.group_positions = {}
        self.order = deque()
        self.next_id = 0

    def add(self, history, action, reward, done, next_history, group):
        group = str(group)
        transition = (
            np.asarray(history, dtype=np.float32),
            np.asarray(action, dtype=np.float32),
            float(reward),
            float(done),
            np.asarray(next_history, dtype=np.float32),
        )
        transition_id = self.next_id
        self.next_id += 1
        self.entries[transition_id] = (group, transition)
        group_ids = self.group_ids.setdefault(group, [])
        self.group_positions[transition_id] = len(group_ids)
        group_ids.append(transition_id)
        self.order.append(transition_id)
        if len(self.order) > self.capacity:
            self._remove(self.order.popleft())

    def sample(self, batch_size):
        batch_size = min(int(batch_size), len(self))
        if batch_size <= 0:
            raise ValueError("Cannot sample an empty replay buffer")

        counts = self._sample_counts(batch_size)
        selected = []
        selected_ids = set()
        for group, count in counts.items():
            if count <= 0:
                continue
            transition_ids = self.rng.sample(self.group_ids.get(group, ()), count)
            selected.extend(transition_ids)
            selected_ids.update(transition_ids)

        shortfall = batch_size - len(selected)
        if shortfall:
            remaining = [
                transition_id
                for transition_id in self.entries
                if transition_id not in selected_ids
            ]
            selected.extend(self.rng.sample(remaining, shortfall))
        self.rng.shuffle(selected)

        groups = []
        transitions = []
        for transition_id in selected:
            group, transition = self.entries[transition_id]
            groups.append(group)
            transitions.append(transition)
        histories, actions, rewards, dones, next_histories = zip(*transitions)
        return (
            np.stack(histories),
            np.stack(actions),
            np.asarray(rewards, dtype=np.float32).reshape(-1, 1),
            np.asarray(dones, dtype=np.float32).reshape(-1, 1),
            np.stack(next_histories),
            np.asarray(groups),
        )

    def group_counts(self):
        return {group: len(ids) for group, ids in self.group_ids.items()}

    def __len__(self):
        return len(self.order)

    def state_dict(self):
        return {
            "version": 2,
            "capacity": self.capacity,
            "group_ratios": self.group_ratios,
            "buffer": [self.entries[transition_id] for transition_id in self.order],
            "rng_state": self.rng.getstate(),
        }

    def load_state_dict(self, state):
        self.capacity = int(state["capacity"])
        self.group_ratios = self._normalize_ratios(
            state.get("group_ratios", self.group_ratios)
        )
        self.entries = {}
        self.group_ids = {}
        self.group_positions = {}
        self.order = deque()
        self.next_id = 0
        for stored in state["buffer"]:
            if len(stored) == 2 and isinstance(stored[0], str):
                group, transition = stored
            else:
                group, transition = "unknown", stored
            self.add(*transition, group=group)
        self.rng.setstate(state["rng_state"])

    def _sample_counts(self, batch_size):
        available_groups = [
            group
            for group in self.GROUPS
            if self.group_ratios.get(group, 0.0) > 0.0
            and len(self.group_ids.get(group, ())) > 0
        ]
        if not available_groups:
            return {}

        ratio_sum = sum(self.group_ratios[group] for group in available_groups)
        exact = {
            group: batch_size * self.group_ratios[group] / ratio_sum
            for group in available_groups
        }
        counts = {
            group: min(int(exact[group]), len(self.group_ids[group]))
            for group in available_groups
        }
        remaining = batch_size - sum(counts.values())
        priority = sorted(
            available_groups,
            key=lambda group: (exact[group] - int(exact[group]), self.group_ratios[group]),
            reverse=True,
        )
        while remaining and priority:
            progressed = False
            for group in priority:
                if counts[group] >= len(self.group_ids[group]):
                    continue
                counts[group] += 1
                remaining -= 1
                progressed = True
                if not remaining:
                    break
            if not progressed:
                break
        return counts

    def _remove(self, transition_id):
        group, _ = self.entries.pop(transition_id)
        group_ids = self.group_ids[group]
        position = self.group_positions.pop(transition_id)
        last_id = group_ids.pop()
        if position < len(group_ids):
            group_ids[position] = last_id
            self.group_positions[last_id] = position

    @classmethod
    def _normalize_ratios(cls, ratios):
        if ratios is None:
            ratios = {group: 1.0 for group in cls.GROUPS}
        normalized = {
            group: max(float(ratios.get(group, 0.0)), 0.0) for group in cls.GROUPS
        }
        if sum(normalized.values()) <= 0.0:
            raise ValueError("At least one replay group ratio must be positive")
        return normalized
