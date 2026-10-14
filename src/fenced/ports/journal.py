"""The journal, as the two things the write layer asks of it.

An entry is a mapping the write layer builds out of text, lists and mappings, so an
adapter can keep it as one line of JSON. The journal only ever grows. Nothing here takes
an entry back or changes one, because the undo of an entry is an entry of its own.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol


class Journal(Protocol):
    """A list of entries that only grows."""

    def append(self, entry: Mapping[str, object]) -> None:
        """Keep one more entry after the last one."""

    def entries(self) -> Sequence[Mapping[str, object]]:
        """Every entry kept so far, oldest first."""
