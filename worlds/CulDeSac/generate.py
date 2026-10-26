#!/usr/bin/env python3
"""Write the CulDeSac world folder for 7 Days to Die V3.3.

Does not write main.ttw. No public V3.3 description of that binary exists,
and a made-up file would be a guess. See CulDeSac/INSTALL.md.

Prefab sizes come from kui's 7dtd-map database (3.0+), saved here as
vanilla_prefab_sizes.json. Fetched 2026-10-26 from
https://kui.github.io/7dtd-map/prefab-mesh-sizes.json
Each value is [size x, size z, size y, YOffset].
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import layout

REPO = Path(__file__).resolve().parents[2]
WORLD = REPO / "CulDeSac"
PINE = (0, 64, 0)


def height_blocks(wx: np.ndarray, wz: np.ndarray) -> np.ndarray:
    """Block height in PNG orientation. The pad is flat; hills are gentle."""
    distance = np.hypot(wx + 0.5, wz + 0.5)
    hills = (
        46
        + 3.0 * np.sin(wx / 240.0)
        + 2.2 * np.cos(wz / 200.0)
        + 1.4 * np.sin((wx + wz) / 320.0)
    )
    blend = np.clip((distance - layout.PAD_RADIUS) / layout.BLEND_WIDTH, 0.0, 1.0)
    blend = blend * blend * (3.0 - 2.0 * blend)
    height = layout.PAD_HEIGHT * (1.0 - blend) + hills * blend
    height = np.where(distance <= layout.PAD_RADIUS, float(layout.PAD_HEIGHT), height)
    return height


def world_grid(size: int) -> tuple[np.ndarray, np.ndarray]:
    rows, cols = np.indices((size, size))
    wx = cols - size // 2
    wz = size // 2 - 1 - rows
    return wx, wz


def paint_road(wx: np.ndarray, wz: np.ndarray) -> np.ndarray:
    cx = wx + 0.5
    cz = wz + 0.5
    distance = np.hypot(cx, cz)
    ring = (distance >= layout.ROAD_INNER) & (distance <= layout.ROAD_OUTER)
    stub = (
        (np.abs(cx) <= layout.ROAD_HALF_WIDTH)
        & (cz <= -layout.ROAD_INNER)
        & (cz >= layout.APRON_NORTH_Z)
    )
    apron = (
        (np.abs(cx) <= layout.APRON_HALF_X)
        & (cz <= layout.APRON_NORTH_Z)
        & (cz >= layout.APRON_SOUTH_Z)
    )
    return ring | stub | apron


def check_layout(road: np.ndarray, wx: np.ndarray, wz: np.ndarray) -> None:
    houses = layout.placements()
    for index, house in enumerate(houses):
        for other in houses[index + 1 :]:
            if layout.boxes_overlap(house, other):
                raise SystemExit(f"{house.name} overlaps {other.name}")
        clearance = layout.min_road_clearance(house)
        if clearance < layout.YARD_CLEARANCE:
            raise SystemExit(
                f"{house.name} is only {clearance} blocks from the road "
                f"(need {layout.YARD_CLEARANCE})"
            )
        for x, z in layout.footprint_cells(house):
            px, py = layout.cell_to_pixel(x, z)
            if bool(road[py, px]) != layout.cell_is_road(x, z):
                raise SystemExit(f"road mask disagrees at {x},{z}")
            if math_dist(x, z) > layout.PAD_RADIUS - 2:
                raise SystemExit(f"{house.name} cell {x},{z} is outside the pad")
    for x, z in layout.SPAWNS:
        if not layout.cell_is_road(x, z):
            raise SystemExit(f"spawn {x},{z} is not on the apron")
        if math_dist(x, z) > layout.PAD_RADIUS - 2:
            raise SystemExit(f"spawn {x},{z} is outside the pad")
        for house in houses:
            if house.x <= x < house.x + layout.FOOTPRINT and house.z <= z < house.z + layout.FOOTPRINT:
                raise SystemExit(f"spawn {x},{z} is inside {house.name}")
    # The numpy mask and the stdlib predicate agree on a coarse grid.
    step = 7
    sample = (wx % step == 0) & (wz % step == 0) & (np.abs(wx) < 400) & (np.abs(wz) < 400)
    ys, xs = np.nonzero(sample)
    for py, px in zip(ys.tolist(), xs.tolist(), strict=True):
        x = int(wx[py, px])
        z = int(wz[py, px])
        if bool(road[py, px]) != layout.cell_is_road(x, z):
            raise SystemExit(f"road mask disagrees at {x},{z}")


def math_dist(x: int, z: int) -> float:
    return float(np.hypot(x + 0.5, z + 0.5))


def write_dtm(height: np.ndarray, path: Path) -> None:
    # PNG row 0 is north. dtm.raw row 0 is south, so flip before writing.
    raw = np.rint(height * 256.0).clip(0, 65535).astype("<u2")
    np.ascontiguousarray(np.flipud(raw)).tofile(path)


def write_radiation(path: Path) -> None:
    side = layout.SIZE // 16
    border = layout.RADIATION_BORDER_PX
    image = Image.new("RGB", (side, side), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, side - 1, border - 1], fill=(255, 0, 0))
    draw.rectangle([0, side - border, side - 1, side - 1], fill=(255, 0, 0))
    draw.rectangle([0, 0, border - 1, side - 1], fill=(255, 0, 0))
    draw.rectangle([side - border, 0, side - 1, side - 1], fill=(255, 0, 0))
    image.save(path, optimize=True)


def write_xml(path: Path) -> None:
    houses = layout.placements()
    decorations = []
    for house in houses:
        decorations.append(
            "  "
            f'<decoration type="model" name="{house.name}" '
            f'position="{house.x},{layout.PAD_HEIGHT},{house.z}" '
            f'rotation="{house.rotation}" y_is_groundlevel="true" />'
        )
    (path / "prefabs.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<prefabs>\n'
        + "\n".join(decorations)
        + "\n</prefabs>\n",
        encoding="utf-8",
    )
    spawns = []
    for x, z in layout.SPAWNS:
        spawns.append(
            f'  <spawnpoint position="{x},{layout.PAD_HEIGHT},{z}" rotation="0,0,0" />'
        )
    (path / "spawnpoints.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<spawnpoints>\n'
        + "\n".join(spawns)
        + "\n</spawnpoints>\n",
        encoding="utf-8",
    )
    (path / "water_info.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<WaterSources>\n</WaterSources>\n',
        encoding="utf-8",
    )
    (path / "map_info.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<MapInfo>
  <property name="Name" value="CulDeSac" />
  <property name="Description" value="Three pine-forest homes on a cul-de-sac." />
  <property name="Scale" value="1" />
  <property name="HeightMapSize" value="{size},{size}" />
  <property name="Modes" value="Survival,SurvivalSP,SurvivalMP,Creative" />
  <property name="FixedWaterLevel" value="false" />
  <property name="RandomGeneratedWorld" value="false" />
</MapInfo>
""".format(size=layout.SIZE),
        encoding="utf-8",
    )


def write_preview(
    height: np.ndarray, road: np.ndarray, radiation: Path, path: Path
) -> None:
    x0, x1 = -240, 240
    z0, z1 = -220, 180
    scale = 2
    width = (x1 - x0) * scale
    depth = (z1 - z0) * scale
    image = Image.new("RGB", (width, depth), (18, 55, 24))
    pixels = image.load()
    for z in range(z0, z1):
        for x in range(x0, x1):
            px, py = layout.cell_to_pixel(x, z)
            block = float(height[py, px])
            left = (x - x0) * scale
            top = (z1 - 1 - z) * scale
            if bool(road[py, px]):
                color = (55, 55, 58)
            elif math_dist(x, z) <= layout.PAD_RADIUS:
                color = (36, 110, 48)
            else:
                shade = int(max(0, min(40, (block - 40) * 4)))
                color = (20, 70 + shade, 28)
            for oy in range(scale):
                for ox in range(scale):
                    pixels[left + ox, top + oy] = color

    draw = ImageDraw.Draw(image)

    def to_image(x: float, z: float) -> tuple[float, float]:
        return (x - x0) * scale, (z1 - z) * scale

    for house in layout.placements():
        left, bottom = to_image(house.x, house.z)
        right, top = to_image(house.x + layout.FOOTPRINT, house.z + layout.FOOTPRINT)
        draw.rectangle([left, top, right, bottom], fill=(214, 176, 112), outline=(50, 28, 8))
        cx = house.x + layout.FOOTPRINT / 2
        cz = house.z + layout.FOOTPRINT / 2
        dx, dz, _facing = layout.FACING[house.rotation]
        ax, ay = to_image(cx, cz)
        bx, by = to_image(cx + dx * 18, cz + dz * 18)
        draw.line([ax, ay, bx, by], fill=(255, 255, 255), width=3)
        draw.polygon(
            [
                (bx, by),
                to_image(cx + dx * 12 + dz * 4, cz + dz * 12 - dx * 4),
                to_image(cx + dx * 12 - dz * 4, cz + dz * 12 + dx * 4),
            ],
            fill=(255, 70, 40),
        )
        label = house.name.replace("house_old_bungalow_", "")
        draw.text((left + 6, top + 6), label, fill=(30, 18, 8))

    for x, z in layout.SPAWNS:
        sx, sy = to_image(x, z)
        draw.ellipse([sx - 4, sy - 4, sx + 4, sy + 4], fill=(255, 220, 40))

    draw.rectangle([0, 0, width - 1, depth - 1], outline=(230, 230, 230))
    draw.text((8, 8), "N", fill=(255, 255, 255))
    draw.text((8, depth - 36), "arrows = front door    yellow = spawn", fill=(255, 255, 255))

    inset = Image.open(radiation).convert("RGB").resize((96, 96), Image.Resampling.NEAREST)
    image.paste(inset, (width - 104, 8))
    draw.text((width - 104, 106), "radiation", fill=(255, 255, 255))
    image.save(path, optimize=True)


def main() -> int:
    WORLD.mkdir(parents=True, exist_ok=True)
    wx, wz = world_grid(layout.SIZE)
    height = height_blocks(wx, wz)
    road = paint_road(wx, wz)
    check_layout(road, wx, wz)

    Image.new("RGB", (layout.SIZE, layout.SIZE), PINE).save(
        WORLD / "biomes.png", optimize=True
    )
    splat3 = np.zeros((layout.SIZE, layout.SIZE, 4), dtype=np.uint8)
    splat3[..., 3] = 255
    splat3[road, 0] = 255
    Image.fromarray(splat3).save(WORLD / "splat3.png", optimize=True)
    splat4 = np.zeros((layout.SIZE, layout.SIZE, 4), dtype=np.uint8)
    splat4[..., 3] = 255
    Image.fromarray(splat4).save(WORLD / "splat4.png", optimize=True)
    write_radiation(WORLD / "radiation.png")
    write_dtm(height, WORLD / "dtm.raw")
    write_xml(WORLD)
    write_preview(height, road, WORLD / "radiation.png", WORLD / "preview.png")

    for house in layout.placements():
        print(
            f"{house.name} sw={house.x},{layout.PAD_HEIGHT},{house.z} "
            f"rot={house.rotation} faces {house.facing} "
            f"clearance={layout.min_road_clearance(house)}"
        )
    print(f"Wrote {WORLD.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
