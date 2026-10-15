"""The roster of sellers, as the one thing the command line asks of it.

A seller comes back as the `Seller` of the domain, so the refusals and the folding that
constructor carries happen whatever the roster is read from. Nothing here says where the
roster is kept. That belongs to an adapter.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from fenced.domain.matching import Seller


class Roster(Protocol):
    """The sellers a lead can go to."""

    def sellers(self) -> Sequence[Seller]:
        """Every seller, in the order the roster keeps them, which decides nothing."""
