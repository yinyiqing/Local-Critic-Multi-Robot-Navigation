"""Training-only labels for locally observable multi-robot interaction risk."""

import math

import numpy as np


def interaction_risk(
    position,
    velocity,
    heading,
    neighbor_positions,
    neighbor_velocities,
    visible_range=4.0,
    visible_fov=math.pi / 2.0 + 0.03,
    close_distance=1.5,
    ttc_horizon=2.0,
):
    """Return a continuous [0, 1] risk label from visible robot kinematics.

    The label supervises the gate only during simulation. At execution, the
    policy still receives only its own laser/action history.
    """
    if min(visible_range, close_distance, ttc_horizon) <= 0.0:
        raise ValueError("Interaction-risk distances and TTC horizon must be positive")

    position = np.asarray(position, dtype=np.float32)
    velocity = np.asarray(velocity, dtype=np.float32)
    neighbor_positions = np.asarray(neighbor_positions, dtype=np.float32)
    neighbor_velocities = np.asarray(neighbor_velocities, dtype=np.float32)
    if neighbor_positions.size == 0:
        return 0.0

    heading_vector = np.array(
        [math.cos(heading), math.sin(heading)], dtype=np.float32
    )
    highest_risk = 0.0
    for neighbor_position, neighbor_velocity in zip(
        neighbor_positions, neighbor_velocities
    ):
        offset = neighbor_position - position
        distance = float(np.linalg.norm(offset))
        if distance <= 1e-6 or distance > visible_range:
            continue
        direction = offset / distance
        view_angle = math.acos(
            float(np.clip(np.dot(heading_vector, direction), -1.0, 1.0))
        )
        if view_angle > visible_fov:
            continue

        proximity_risk = max(0.0, (close_distance - distance) / close_distance)
        radial_velocity = float(np.dot(neighbor_velocity - velocity, direction))
        closing_speed = max(-radial_velocity, 0.0)
        if closing_speed <= 1e-6:
            ttc_risk = 0.0
        else:
            ttc = distance / closing_speed
            ttc_risk = max(0.0, (ttc_horizon - ttc) / ttc_horizon)
        highest_risk = max(highest_risk, proximity_risk, ttc_risk)
    return float(np.clip(highest_risk, 0.0, 1.0))
