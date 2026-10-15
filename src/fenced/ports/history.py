"""The purchase history, as the one thing the command line asks of it.

The history answers what an address bought before, one past order to an item. An address
that never bought anything has an empty history, which is an answer and not a refusal.
Nothing here says where the history is kept. That belongs to an adapter.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class History(Protocol):
    """Past orders, by the address that placed them."""

    def orders(self, address: str) -> Sequence[str]:
        """The past orders of this address, and an empty sequence when there are none."""
