#!/usr/bin/env python3
"""Check every top-level 7DTD mod folder.

A mod folder needs ModInfo.xml in V2 form (<xml>) or V1 form (<ModInfo>),
with Name, DisplayName, Version, Description, and Author. Every .xml file
in the folder must be well formed.

Prints PASS or FAIL. Exits with status 1 when a mod fails.
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NamedTuple

REQUIRED_FIELDS = ("Name", "DisplayName", "Version", "Description", "Author")
ACCEPTED_ROOTS = {"xml", "ModInfo"}
# Top-level folders that are part of the repo, not mods.
RESERVED_DIRS = {"scripts", "dist", "bin", "obj"}
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
