"""Two clocks. One reads the machine and one says the moment it was given.

The second one is how a test, or a person replaying a run, holds the time still.
"""

from __future__ import annotations

from datetime import UTC, datetime


class ClockError(ValueError):
    """A moment a clock will not keep."""


class SystemClock:
    """The time on this machine, in UTC."""

    def now(self) -> str:
        """The moment now, as ISO 8601 text with an offset."""
        return datetime.now(UTC).isoformat(timespec="seconds")


class FixedClock:
    """A clock that always says the moment it was given."""

    def __init__(self, moment: str) -> None:
        try:
            parsed = datetime.fromisoformat(moment)
        except ValueError as broken:
            raise ClockError(f"{moment!r} is not a moment") from broken
        if parsed.utcoffset() is None:
            raise ClockError(f"{moment!r} has no offset, so it is no moment in particular")
        self.moment = parsed.isoformat(timespec="seconds")

    def now(self) -> str:
        """The moment this clock was given."""
        return self.moment
