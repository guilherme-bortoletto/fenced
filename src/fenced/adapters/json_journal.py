"""The journal, kept as a file of JSON lines that only grows.

An entry is one line. Appending opens the file to add at the end, writes the line, and
waits for the disk before it returns, because the write layer writes the store only after
the entry is kept. Nothing here rewrites a line or takes one away.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

from fenced.adapters.json_files import FileError


class JsonJournal:
    """A journal in one file of JSON lines. The file appears with the first entry."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append(self, entry: Mapping[str, object]) -> None:
        """Keep one more entry after the last one, on disk before this returns."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(dict(entry), sort_keys=True)
        with self.path.open("a", encoding="utf-8") as kept:
            kept.write(line + "\n")
            kept.flush()
            os.fsync(kept.fileno())

    def entries(self) -> list[dict[str, object]]:
        """Every entry kept so far, oldest first."""
        if not self.path.is_file():
            return []
        found = []
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as broken:
                raise FileError(f"line {number} of {self.path} is not JSON") from broken
            if not isinstance(entry, dict) or not isinstance(entry.get("entry"), int):
                raise FileError(f"line {number} of {self.path} is not a numbered entry")
            found.append(entry)
        return found
