"""The clock, as the one thing the command line asks of it.

The moment comes back as ISO 8601 text with its offset, so this port names no module that
reads a clock. Turning the text into a moment is the caller's work, and the caller is
outside the pure core.
"""

from __future__ import annotations

from typing import Protocol


class Clock(Protocol):
    """Something that says what time it is."""

    def now(self) -> str:
        """The moment now, as ISO 8601 text with an offset."""
