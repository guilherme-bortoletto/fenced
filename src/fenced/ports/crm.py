"""The record store, as the three things the write layer asks of it.

A record is a flat mapping of text to text, kept under a key. The store answers what it
holds under a key, puts a record there, and takes one away. Nothing here says where the
records live. That belongs to an adapter.

Only `fenced.writes` calls the two methods that change the store, and the third fence
refuses either call anywhere else under `src`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

Record = Mapping[str, str]


class Crm(Protocol):
    """A store of records by key."""

    def read_lead(self, key: str) -> Record | None:
        """The record under this key, or None when there is none."""

    def put_lead(self, key: str, record: Record) -> None:
        """Keep this record under this key, in place of whatever was there."""

    def remove_lead(self, key: str) -> None:
        """Take away the record under this key."""
