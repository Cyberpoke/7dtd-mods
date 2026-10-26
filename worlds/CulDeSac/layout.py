"""CulDeSac layout for 7 Days to Die V3.3.

Stdlib only. generate.py and scripts/validate.py both import this so the
road, the houses, and the checks cannot drift apart.

World axes: +X east, +Z north, origin at the map center.
PNG row 0 is north. dtm.raw is vertically flipped, so its row 0 is south.
A prefab position is the south-west corner of the rotated footprint.
"""

from __future__ import annotations

import math
from typing import NamedTuple

# Smallest size we will ship. RWG's own slider starts at 6144, but that
# slider is only used when Game World is RWG. 1024 shows up in older World
# Editor advice and is not confirmed for V3.3. 2048 is a multiple of the
# radiation scale (16) and of the RWG step.
SIZE = 2048
PAD_HEIGHT = 48

# Asphalt ring, then a straight stub south into a spawn apron.
ROAD_INNER = 26
ROAD_OUTER = 36
ROAD_HALF_WIDTH = 5
FRONT_RADIUS = 64
APRON_HALF_X = 14
APRON_NORTH_Z = -108
APRON_SOUTH_Z = -136
PAD_RADIUS = 180
BLEND_WIDTH = 110
RADIATION_BORDER_PX = 4
YARD_CLEARANCE = 8
FOOTPRINT = 42

# Name, degrees clockwise from north, prefab rotation.
# Rotation is clockwise 90-degree turns from the prefab's authored facing.
# These three bungalows face south at rotation 0 (RotationToFaceNorth = 2).
HOUSES = (
    ("house_old_bungalow_02", 0, 0),
    ("house_old_bungalow_03", 120, 1),
    ("house_old_bungalow_04", 240, 3),
)

# Spawn on the apron, clear of the houses. Several points so players
# do not all appear on the same block.
SPAWNS = (
    (0, -118),
    (-6, -118),
    (6, -118),
    (0, -128),
)

# Clockwise from a south-facing default: 0 south, 1 west, 2 north, 3 east.
FACING = {
    0: (0, -1, "south"),
    1: (-1, 0, "west"),
    2: (0, 1, "north"),
    3: (1, 0, "east"),
}


class Placement(NamedTuple):
    name: str
    x: int
    z: int
    rotation: int
    facing: str


def cell_to_pixel(x: int, z: int, size: int = SIZE) -> tuple[int, int]:
    """Map a world cell to a PNG pixel. Row 0 of the PNG is north."""
    return x + size // 2, size // 2 - 1 - z


def pixel_to_cell(px: int, py: int, size: int = SIZE) -> tuple[int, int]:
    return px - size // 2, size // 2 - 1 - py


def dtm_index(x: int, z: int, size: int = SIZE) -> int:
    """Row-major index in dtm.raw. Row 0 of the file is south."""
    row = size // 2 + z
    col = x + size // 2
    return row * size + col


def cell_is_road(x: int, z: int) -> bool:
    """True when the block at (x, z) is asphalt."""
    cx = x + 0.5
    cz = z + 0.5
    distance = math.hypot(cx, cz)
    if ROAD_INNER <= distance <= ROAD_OUTER:
        return True
    if abs(cx) <= ROAD_HALF_WIDTH and APRON_NORTH_Z <= cz <= -ROAD_INNER:
        return True
    if abs(cx) <= APRON_HALF_X and APRON_SOUTH_Z <= cz <= APRON_NORTH_Z:
        return True
    return False


def _iround(value: float) -> int:
    return int(math.floor(value + 0.5))


def placements(footprint: int = FOOTPRINT) -> list[Placement]:
    """South-west corners of the three houses, fronts toward the circle."""
    houses: list[Placement] = []
    half = footprint // 2
    for name, degrees, rotation in HOUSES:
        angle = math.radians(degrees)
        fx = _iround(math.sin(angle) * FRONT_RADIUS)
        fz = _iround(math.cos(angle) * FRONT_RADIUS)
        if rotation == 0:  # front is the south edge
            swx, swz = fx - half, fz
        elif rotation == 1:  # front is the west edge
            swx, swz = fx, fz - half
        elif rotation == 2:  # front is the north edge
            swx, swz = fx - half, fz - footprint
        elif rotation == 3:  # front is the east edge
            swx, swz = fx - footprint, fz - half
        else:
            raise ValueError(f"rotation must be 0..3, got {rotation}")
        _dx, _dz, facing = FACING[rotation]
        houses.append(Placement(name, swx, swz, rotation, facing))
    return houses


def footprint_cells(place: Placement, footprint: int = FOOTPRINT) -> list[tuple[int, int]]:
    cells = []
    for x in range(place.x, place.x + footprint):
        for z in range(place.z, place.z + footprint):
            cells.append((x, z))
    return cells


def boxes_overlap(a: Placement, b: Placement, footprint: int = FOOTPRINT) -> bool:
    return (
        a.x < b.x + footprint
        and b.x < a.x + footprint
        and a.z < b.z + footprint
        and b.z < a.z + footprint
    )


def min_road_clearance(place: Placement, footprint: int = FOOTPRINT) -> int:
    """Smallest Chebyshev distance from a house cell to asphalt.

    Stops searching past YARD_CLEARANCE. A larger return means the yard
    is at least that wide.
    """
    best = YARD_CLEARANCE + 1
    limit = YARD_CLEARANCE
    for x, z in footprint_cells(place, footprint):
        for dz in range(-limit, limit + 1):
            for dx in range(-limit, limit + 1):
                dist = max(abs(dx), abs(dz))
                if dist >= best:
                    continue
                if cell_is_road(x + dx, z + dz):
                    best = dist
                    if best == 0:
                        return 0
    return best
