"""The inbox, as the one thing the command line asks of it.

A message is a flat mapping of text to text with three fields. `id` names it, `received_at`
is the moment it arrived as ISO 8601 text with an offset, and `text` is what the person
wrote. Nothing here says where the messages are kept. That belongs to an adapter.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

Message = Mapping[str, str]
FIELDS = ("id", "received_at", "text")


class Inbox(Protocol):
    """A list of messages waiting to be read."""

    def messages(self) -> Sequence[Message]:
        """Every message, in the order it was kept."""
