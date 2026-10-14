"""The inbox, read from one JSON file that holds a list of messages.

Each message is checked here, at the edge, so the command line reads only messages that
have the three fields as text and a moment it can count from. A message that does not is
refused with the file and the position it was found at.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fenced.adapters.json_files import FileError, read_json
from fenced.ports.inbox import FIELDS


class JsonInbox:
    """The messages one file holds."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def messages(self) -> list[dict[str, str]]:
        """Every message in the file, in the order it is written there."""
        if not self.path.is_file():
            raise FileError(f"there is no inbox at {self.path}")
        held = read_json(self.path, [])
        if not isinstance(held, list):
            raise FileError(f"{self.path} holds a {type(held).__name__} and not a list")
        found = []
        seen = set()
        for position, message in enumerate(held, start=1):
            where = f"message {position} of {self.path}"
            if not isinstance(message, dict):
                raise FileError(f"{where} is not an object")
            for field in FIELDS:
                if not isinstance(message.get(field), str) or not message[field].strip():
                    raise FileError(f"{where} has no {field} written as text")
            if message["id"] in seen:
                raise FileError(f"{where} carries the id {message['id']} a second time")
            seen.add(message["id"])
            try:
                moment = datetime.fromisoformat(message["received_at"])
            except ValueError as broken:
                raise FileError(f"{where} was received at a moment that is not one") from broken
            if moment.utcoffset() is None:
                raise FileError(f"{where} was received at a moment with no offset")
            found.append({field: message[field] for field in FIELDS})
        return found
