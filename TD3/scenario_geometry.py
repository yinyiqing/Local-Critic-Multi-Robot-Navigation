import math


MAP_LIMIT = 4.5


def is_valid_map_position(x, y):
    if -6.2 < x < -3.8 and 3.8 < y < 6.2:
        return False
    if -2.7 < x < -1.3 and -0.2 < y < 4.7:
        return False
    if -4.2 < x < -0.3 and 1.3 < y < 2.7:
        return False
    if -4.2 < x < -0.8 and -4.2 < y < -2.3:
        return False
    if -3.7 < x < -1.3 and -2.7 < y < -0.8:
        return False
    if 0.8 < x < 4.2 and -3.2 < y < -1.8:
        return False
    if 2.5 < x < 4.0 and -3.2 < y < 0.7:
        return False
    if 3.8 < x < 6.2 and -4.2 < y < -3.3:
        return False
    if 1.3 < x < 4.2 and 1.5 < y < 3.7:
        return False
    if -7.2 < x < -3.0 and -1.5 < y < 0.5:
        return False
    return -MAP_LIMIT <= x <= MAP_LIMIT and -MAP_LIMIT <= y <= MAP_LIMIT


def has_map_clearance(point, clearance, samples=16):
    x, y = float(point[0]), float(point[1])
    if not is_valid_map_position(x, y):
        return False
    if clearance <= 0:
        return True
    for index in range(samples):
        angle = 2.0 * math.pi * index / samples
        if not is_valid_map_position(
            x + clearance * math.cos(angle),
            y + clearance * math.sin(angle),
        ):
            return False
    return True
