"""The record store, kept as one JSON file that maps a key to a record.

Every read goes to the file, so the store is always what the file holds and never a copy
of it from earlier. A record is a flat mapping of text to text, and anything else in the
file is refused when it is read.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from fenced.adapters.json_files import FileError, read_json, write_json


class JsonCrm:
    """A record store in one file. The file appears with the first record put in it."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _records(self) -> dict[str, dict[str, str]]:
        """Every record the file holds, by key, or a refusal naming what is wrong."""
        held = read_json(self.path, {})
        if not isinstance(held, dict):
            raise FileError(f"{self.path} holds a {type(held).__name__} and not records by key")
        for key, record in held.items():
            if not isinstance(record, dict) or not all(
                isinstance(name, str) and isinstance(value, str) for name, value in record.items()
            ):
                raise FileError(f"{self.path} holds {key} as something other than text by name")
        return held

    def read_lead(self, key: str) -> dict[str, str] | None:
        """The record under this key, or None when there is none."""
        return self._records().get(key)

    def put_lead(self, key: str, record: Mapping[str, str]) -> None:
        """Keep this record under this key, in place of whatever was there."""
        records = self._records()
        records[key] = dict(record)
        write_json(self.path, records)

    def remove_lead(self, key: str) -> None:
        """Take away the record under this key."""
        records = self._records()
        records.pop(key, None)
        write_json(self.path, records)
