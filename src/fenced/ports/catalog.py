"""The catalog, as the one thing the command line asks of it.

The catalog names each product it carries and the price it carries it at. The prices are
handed to scoring as they are, and scoring decides what an amount is. Nothing here says
where the catalog is kept. That belongs to an adapter.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class Catalog(Protocol):
    """The products on offer and the price of each."""

    def prices(self) -> Mapping[str, object]:
        """Every product the catalog carries, by its name, with its price."""
