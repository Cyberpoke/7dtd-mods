#!/usr/bin/env python3
"""Zip one mod folder to dist/<Name>-v<Version>.zip.

Name and Version come from ModInfo.xml. The mod folder is the root inside
the zip, which is what 7 Days to Die expects under Mods/.

Build output is left out: bin/, obj/, .vs/, and *.user.
"""

from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

import validate

INVALID_FILENAME_CHARS = set('<>:"/\\|?*')


def packaged_files(mod_dir: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(mod_dir):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in validate.SKIP_DIRS and not name.startswith(".")
        )
        for name in sorted(filenames):
            if name.endswith(".user"):
                continue
            files.append(Path(dirpath) / name)
    return files


def zip_filename(name: str, version: str) -> str | None:
    for label, value in (("Name", name), ("Version", version)):
        if value in {".", ".."} or any(
            char in INVALID_FILENAME_CHARS or ord(char) < 32 for char in value
        ):
            print(
                f"FAIL: ModInfo {label} {value!r} cannot be used in a zip file name.",
                file=sys.stderr,
            )
            return None
    return f"{name}-v{version}.zip"


def package_mod(mod_dir: Path, dist_dir: Path) -> int:
    if not mod_dir.is_dir():
        print(f"FAIL: {mod_dir} is not a folder.", file=sys.stderr)
        return 1

    info, errors = validate.inspect_mod(mod_dir)
    if errors or info is None:
        validate.print_result(mod_dir.name, errors or ["ModInfo.xml could not be read"])
        return 1

    filename = zip_filename(info.name, info.version)
    if filename is None:
        return 1

    dist_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dist_dir / filename
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in packaged_files(mod_dir):
            relative = path.relative_to(mod_dir).as_posix()
            archive.write(path, f"{mod_dir.name}/{relative}")

    print(f"Wrote {zip_path.relative_to(validate.repo_root())}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)
    if len(args) != 2:
        print("Usage: python scripts/package.py <mod-folder>", file=sys.stderr)
        return 1

    raw = Path(args[1])
    mod_dir = raw.resolve() if raw.is_absolute() else (Path.cwd() / raw).resolve()
    return package_mod(mod_dir, validate.repo_root() / "dist")


if __name__ == "__main__":
    sys.exit(main())
