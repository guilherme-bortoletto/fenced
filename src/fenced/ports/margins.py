"""The margin table, as the one thing the command line asks of it.

The table gives each product a margin between zero and one. The margins are handed to
scoring as they are, and scoring decides what a margin is. Nothing here says where the
table is kept. That belongs to an adapter.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class Margins(Protocol):
    """The margin of each product."""

    def margins(self) -> Mapping[str, object]:
        """Every product the table knows, by its name, with its margin."""
