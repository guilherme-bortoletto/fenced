"""The extractor, as the one thing the command line asks of it.

An extractor reads the text a person wrote and returns the fields it found in it. What it
returns is not trusted. It crosses `Lead.from_fields` before anything else reads it, and that
boundary refuses rather than coerces. Nothing here says whether a model, a rule or a table
does the reading. That belongs to an adapter.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class Extractor(Protocol):
    """Something that turns free text into fields."""

    def extract(self, text: str) -> Mapping[str, object]:
        """The fields found in this text, which are a name, an address and an awareness."""
