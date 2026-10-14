"""Reading and writing the JSON files the other adapters keep.

A file is written whole to a file beside it and then moved into place, so a reader finds
either the old file or the new one and never half of one.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


class FileError(ValueError):
    """A file an adapter cannot read as the shape it expects."""


def read_json(path: Path, default: object) -> object:
    """The JSON a file holds, or the default when there is no file."""
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as broken:
        raise FileError(f"{path} is not JSON, {broken}") from broken


def write_json(path: Path, value: object) -> None:
    """Keep this value in a file, written beside it first and then moved into place."""
    path.parent.mkdir(parents=True, exist_ok=True)
    beside = path.with_name(path.name + ".writing")
    beside.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(beside, path)
