#!/usr/bin/env python3
"""Check every top-level 7DTD mod folder.

A mod folder needs ModInfo.xml in V2 form (<xml>) or V1 form (<ModInfo>),
with Name, DisplayName, Version, Description, and Author. Every .xml file
in the folder must be well formed.

Prints PASS or FAIL. Exits with status 1 when a mod fails.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NamedTuple

REQUIRED_FIELDS = ("Name", "DisplayName", "Version", "Description", "Author")
ACCEPTED_ROOTS = {"xml", "ModInfo"}
# Top-level folders that are part of the repo, not mods.
# worlds/ holds generators such as CulDeSac. The playable folder is CulDeSac/.
RESERVED_DIRS = {"scripts", "dist", "bin", "obj", "worlds"}
# Build output inside a mod. Not part of the modlet, and not packaged.
SKIP_DIRS = {"bin", "obj", ".vs", "__pycache__"}


class ModInfo(NamedTuple):
    name: str
    display_name: str
    version: str
    description: str
    author: str


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def mod_folders(root: Path) -> list[Path]:
    folders = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_dir():
            continue
        if path.name.startswith(".") or path.name in RESERVED_DIRS:
            continue
        folders.append(path)
    return folders


def xml_files(mod_dir: Path) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(mod_dir):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in SKIP_DIRS and not name.startswith(".")
        ]
        for name in filenames:
            if name.lower().endswith(".xml"):
                found.append(Path(dirpath) / name)
    return sorted(found)


def inspect_mod(mod_dir: Path) -> tuple[ModInfo | None, list[str]]:
    """Return the parsed ModInfo, or None plus a list of problems."""
    errors: list[str] = []
    parsed: dict[Path, ET.Element] = {}

    modinfo_path = mod_dir / "ModInfo.xml"
    if not modinfo_path.is_file():
        errors.append("ModInfo.xml is missing")

    for path in xml_files(mod_dir):
        relative = path.relative_to(mod_dir).as_posix()
        try:
            parsed[path] = ET.parse(path).getroot()
        except (ET.ParseError, OSError, UnicodeError) as exc:
            errors.append(f"{relative} is not well-formed XML: {exc}")

    info: ModInfo | None = None
    if modinfo_path.is_file() and modinfo_path in parsed:
        info, field_errors = read_modinfo(mod_dir, parsed[modinfo_path])
        errors.extend(field_errors)
    if (mod_dir / "map_info.xml").is_file() and modinfo_path in parsed:
        errors.extend(world_errors(mod_dir))
    return info, errors


def read_modinfo(mod_dir: Path, root: ET.Element) -> tuple[ModInfo | None, list[str]]:
    if root.tag not in ACCEPTED_ROOTS:
        return None, [
            f"ModInfo.xml root is <{root.tag}>; expected <xml> (V2) or <ModInfo> (V1)"
        ]

    errors: list[str] = []
    values: dict[str, str] = {}
    for field in REQUIRED_FIELDS:
        matches = [child for child in list(root) if child.tag == field]
        if not matches:
            errors.append(f'ModInfo.xml is missing <{field} value="..."/>')
            continue
        if len(matches) > 1:
            errors.append(f"ModInfo.xml has more than one <{field}>")
            continue
        raw = matches[0].get("value")
        if raw is None or raw.strip() == "":
            errors.append(
                f"ModInfo.xml <{field}> needs a non-empty value attribute"
            )
            continue
        values[field] = raw.strip()

    name = values.get("Name")
    if name is not None and name != mod_dir.name:
        errors.append(
            f"folder name '{mod_dir.name}' does not match ModInfo Name '{name}'"
        )

    if errors:
        return None, errors

    return ModInfo(
        name=values["Name"],
        display_name=values["DisplayName"],
        version=values["Version"],
        description=values["Description"],
        author=values["Author"],
    ), []


def load_layout(mod_dir: Path):
    path = repo_root() / "worlds" / mod_dir.name / "layout.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"world_layout_{mod_dir.name}", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def world_errors(mod_dir: Path) -> list[str]:
    """Check a hand-built world folder sitting in a mod directory."""
    layout = load_layout(mod_dir)
    if layout is None:
        return [f"worlds/{mod_dir.name}/layout.py is missing"]
    try:
        from PIL import Image
    except ImportError:
        return [
            "Pillow is required to check world images "
            f"(pip install -r worlds/{mod_dir.name}/requirements.txt)"
        ]

    errors: list[str] = []
    size = read_world_size(mod_dir / "map_info.xml", errors)
    if size is None:
        return errors
    if size != layout.SIZE:
        errors.append(
            f"map_info HeightMapSize is {size}, layout.SIZE is {layout.SIZE}"
        )

    for name in ("biomes.png", "splat3.png", "splat4.png"):
        check_image(mod_dir / name, size, size, errors)
    check_image(mod_dir / "radiation.png", size // 16, size // 16, errors)

    dtm_path = mod_dir / "dtm.raw"
    expected_bytes = size * size * 2
    if not dtm_path.is_file():
        errors.append("dtm.raw is missing")
        dtm = None
    else:
        dtm = dtm_path.read_bytes()
        if len(dtm) != expected_bytes:
            errors.append(
                f"dtm.raw is {len(dtm)} bytes; expected {expected_bytes} "
                f"({size}*{size}*2)"
            )
            dtm = None

    sizes = load_prefab_sizes(mod_dir, errors)
    prefab_path = mod_dir / "prefabs.xml"
    if not prefab_path.is_file():
        errors.append("prefabs.xml is missing")
        placed = []
    else:
        placed = read_prefabs(prefab_path, errors)
    if sizes is not None and dtm is not None and size == layout.SIZE and prefab_path.is_file():
        errors.extend(check_prefabs(mod_dir, layout, size, dtm, sizes, placed))
        errors.extend(check_play_area(mod_dir, layout, size, dtm))
    return errors


def read_world_size(path: Path, errors: list[str]) -> int | None:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError, UnicodeError) as exc:
        errors.append(f"map_info.xml is not well-formed XML: {exc}")
        return None
    if root.tag != "MapInfo":
        errors.append(f"map_info.xml root is <{root.tag}>; expected <MapInfo>")
        return None
    values = {
        child.get("name"): (child.get("value") or "").strip()
        for child in root
        if child.tag == "property"
    }
    raw = values.get("HeightMapSize", "")
    parts = raw.split(",")
    if len(parts) != 2 or parts[0].strip() != parts[1].strip():
        errors.append(f"HeightMapSize {raw!r} is not a square")
        return None
    try:
        size = int(parts[0].strip())
    except ValueError:
        errors.append(f"HeightMapSize {raw!r} is not a number")
        return None
    if size <= 0 or size % 16 != 0:
        errors.append(f"HeightMapSize {size} must be a positive multiple of 16")
        return None
    if values.get("RandomGeneratedWorld", "").lower() != "false":
        errors.append('map_info RandomGeneratedWorld should be "false" for this world')
    return size


def check_image(path: Path, width: int, height: int, errors: list[str]) -> None:
    from PIL import Image

    if not path.is_file():
        errors.append(f"{path.name} is missing")
        return
    with Image.open(path) as image:
        if image.size != (width, height):
            errors.append(
                f"{path.name} is {image.size[0]}x{image.size[1]}; "
                f"expected {width}x{height}"
            )


def load_prefab_sizes(mod_dir: Path, errors: list[str]) -> dict | None:
    path = repo_root() / "worlds" / mod_dir.name / "vanilla_prefab_sizes.json"
    if not path.is_file():
        errors.append(f"{path.relative_to(repo_root())} is missing")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"vanilla_prefab_sizes.json is not valid JSON: {exc}")
        return None
    if not isinstance(data, dict) or not data:
        errors.append("vanilla_prefab_sizes.json has no prefab names")
        return None
    return data


def read_prefabs(path: Path, errors: list[str]) -> list[dict]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError, UnicodeError) as exc:
        errors.append(f"prefabs.xml is not well-formed XML: {exc}")
        return []
    placed = []
    for child in root:
        if child.tag != "decoration":
            continue
        name = child.get("name") or ""
        position = child.get("position") or ""
        try:
            x_str, y_str, z_str = (part.strip() for part in position.split(","))
            x, y, z = int(x_str), int(y_str), int(z_str)
            rotation = int(child.get("rotation") or "0")
        except ValueError:
            errors.append(f"prefab {name or '?'} has a bad position or rotation")
            continue
        placed.append(
            {
                "name": name,
                "x": x,
                "y": y,
                "z": z,
                "rotation": rotation,
                "ground": child.get("y_is_groundlevel"),
            }
        )
    return placed


def check_prefabs(mod_dir, layout, size: int, dtm: bytes, sizes: dict, placed: list[dict]) -> list[str]:
    errors: list[str] = []
    if len(dtm) != size * size * 2:
        return errors
    order = sys.byteorder
    # Stored little-endian. array uses the machine endian, so swap on big-endian.
    import array

    heights = array.array("H")
    heights.frombytes(dtm)
    if order != "little":
        heights.byteswap()

    def terrain(x: int, z: int) -> int | None:
        if not (-size // 2 <= x < size // 2 and -size // 2 <= z < size // 2):
            return None
        return heights[layout.dtm_index(x, z, size)] >> 8

    boxes: list[tuple[str, int, int, int, int]] = []
    expected = {
        (house.name, house.x, house.z, house.rotation)
        for house in layout.placements()
    }
    found = set()
    for prefab in placed:
        name = prefab["name"]
        if name not in sizes:
            errors.append(f"prefab {name} is not in the vanilla prefab list")
            continue
        entry = sizes[name]
        if not (isinstance(entry, list) and len(entry) >= 2):
            errors.append(f"vanilla size for {name} is unusable")
            continue
        span_x, span_z = int(entry[0]), int(entry[1])
        if prefab["rotation"] & 1:
            span_x, span_z = span_z, span_x
        if prefab["rotation"] not in range(4):
            errors.append(f"{name} rotation {prefab['rotation']} is outside 0..3")
        if prefab["ground"] != "true":
            errors.append(f"{name} needs y_is_groundlevel=\"true\"")
        found.add((name, prefab["x"], prefab["z"], prefab["rotation"]))
        boxes.append((name, prefab["x"], prefab["z"], span_x, span_z))
        for x in range(prefab["x"], prefab["x"] + span_x):
            for z in range(prefab["z"], prefab["z"] + span_z):
                ground = terrain(x, z)
                if ground is None:
                    errors.append(f"{name} cell {x},{z} is outside the map")
                    return errors
                if ground != prefab["y"]:
                    errors.append(
                        f"{name} at {x},{z} sits on height {ground}, "
                        f"not the prefab Y {prefab['y']}"
                    )
                    return errors
    if found != expected:
        errors.append(
            "prefabs.xml does not match the generator layout "
            f"(found {sorted(found)}, expected {sorted(expected)})"
        )
    for index, box in enumerate(boxes):
        for other in boxes[index + 1 :]:
            if _overlap(box, other):
                errors.append(f"{box[0]} overlaps {other[0]}")

    from PIL import Image

    radiation_path = mod_dir / "radiation.png"
    biomes_path = mod_dir / "biomes.png"
    if radiation_path.is_file() and biomes_path.is_file():
        with Image.open(radiation_path) as radiation, Image.open(biomes_path) as biomes:
            for name, x, z, span_x, span_z in boxes:
                for cx in (x, x + span_x // 2, x + span_x - 1):
                    for cz in (z, z + span_z // 2, z + span_z - 1):
                        px, py = layout.cell_to_pixel(cx, cz, size)
                        rx, ry = px // 16, py // 16
                        if radiation.getpixel((rx, ry))[:3] != (0, 0, 0):
                            errors.append(f"radiation covers {name} at {cx},{cz}")
                        if biomes.getpixel((px, py))[:3] != (0, 64, 0):
                            errors.append(f"biome at {name} {cx},{cz} is not pine forest")
    return errors


def check_play_area(mod_dir: Path, layout, size: int, dtm: bytes) -> list[str]:
    """Spawns sit on the pad, the play area is pine forest, and radiation is only a border."""
    import array

    from PIL import Image

    errors: list[str] = []
    heights = array.array("H")
    heights.frombytes(dtm)
    if sys.byteorder != "little":
        heights.byteswap()

    def terrain(x: int, z: int) -> int:
        return heights[layout.dtm_index(x, z, size)] >> 8

    try:
        root = ET.parse(mod_dir / "spawnpoints.xml").getroot()
    except (ET.ParseError, OSError, UnicodeError) as exc:
        return [f"spawnpoints.xml is not well-formed XML: {exc}"]
    spawns = []
    for child in root:
        if child.tag != "spawnpoint":
            continue
        raw = child.get("position") or ""
        try:
            x_str, y_str, z_str = (part.strip() for part in raw.split(","))
            spawns.append((int(x_str), int(y_str), int(z_str)))
        except ValueError:
            errors.append(f"spawn position {raw!r} is not three integers")
    expected = {(x, layout.PAD_HEIGHT, z) for x, z in layout.SPAWNS}
    if set(spawns) != expected:
        errors.append(f"spawn points {spawns} do not match the layout")
    for x, y, z in spawns:
        if terrain(x, z) != y:
            errors.append(f"spawn {x},{y},{z} is not on terrain height {y}")
        for house in layout.placements():
            if house.x <= x < house.x + layout.FOOTPRINT and house.z <= z < house.z + layout.FOOTPRINT:
                errors.append(f"spawn {x},{z} is inside {house.name}")

    water = ET.parse(mod_dir / "water_info.xml").getroot()
    if any(child.tag == "Water" for child in water):
        errors.append("water_info.xml has water; this world should be dry")

    with Image.open(mod_dir / "biomes.png") as biomes:
        colors = biomes.getcolors(maxcolors=4)
        pine = (0, 64, 0)
        if colors != [(size * size, pine)]:
            errors.append(f"biomes.png is not solid pine forest {pine}")
    with Image.open(mod_dir / "radiation.png") as radiation:
        side = size // 16
        if radiation.getpixel((0, 0))[:3] != (255, 0, 0):
            errors.append("radiation.png border is not red")
        if radiation.getpixel((side // 2, side // 2))[:3] != (0, 0, 0):
            errors.append("radiation.png center is not clear")
    with Image.open(mod_dir / "splat3.png") as roads, Image.open(mod_dir / "splat4.png") as water_splat:
        rx, ry = layout.cell_to_pixel(0, -layout.ROAD_OUTER + 4)
        if roads.getpixel((rx, ry))[:3] != (255, 0, 0):
            errors.append("splat3.png has no asphalt on the cul-de-sac ring")
        ix, iy = layout.cell_to_pixel(0, 0)
        if roads.getpixel((ix, iy))[:3] != (0, 0, 0):
            errors.append("splat3.png paints the middle of the circle as road")
        if water_splat.getpixel((ix, iy))[2] != 0:
            errors.append("splat4.png has blue water in the play area")
    return errors


def _overlap(a: tuple, b: tuple) -> bool:
    _an, ax, az, aw, ad = a
    _bn, bx, bz, bw, bd = b
    return ax < bx + bw and bx < ax + aw and az < bz + bd and bz < az + ad


def print_result(name: str, errors: list[str]) -> None:
    if errors:
        print(f"FAIL: {name}")
        for error in errors:
            print(f"  - {error}")
    else:
        print(f"PASS: {name}")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)
    if len(args) > 2:
        print("Usage: python scripts/validate.py [repo-root]", file=sys.stderr)
        return 1
    root = repo_root() if len(args) == 1 else Path(args[1]).resolve()
    if not root.is_dir():
        print(f"FAIL: {root} is not a directory.", file=sys.stderr)
        return 1

    mods = mod_folders(root)
    if not mods:
        print("PASS: no mod folders found.")
        return 0

    failed = 0
    for mod_dir in mods:
        _info, errors = inspect_mod(mod_dir)
        if errors:
            failed += 1
        print_result(mod_dir.name, errors)

    total = len(mods)
    label = "mod" if total == 1 else "mods"
    if failed:
        print(f"FAIL: {failed} of {total} {label} failed.")
        return 1
    print(f"PASS: {total} {label} checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
