"""An extractor that reads by a few fixed rules, so a test knows what it returns.

It stands in for the model wherever no network is wanted, which is every test and the
default run of the command line. It is not a classifier and does not try to be one. The
rules are short enough to read in one go.

The address is the first word with an at sign in it. The name is the last line that holds
no at sign. The awareness is the first row of `SIGNALS` with a phrase the text contains,
read from the most aware level down, and `unaware` when no row matches. A text with no
address returns no address, so the boundary refuses it the way it would refuse a model
that found none.
"""

from __future__ import annotations

import re

from fenced.domain.lead import Awareness

ADDRESS = re.compile(r"[^\s<>()\[\],]+@[^\s<>()\[\],]+")
# The phrases each level is read from, the most aware first. Written down so a reader
# argues with the table and not with the code.
SIGNALS = (
    (Awareness.READY_TO_BUY, ("ready to buy", "place an order", "send the invoice")),
    (Awareness.PRODUCT_AWARE, ("how much", "a quote", "your price")),
    (Awareness.SOLUTION_AWARE, ("compare", "options", "alternatives")),
    (Awareness.PROBLEM_AWARE, ("problem", "keeps", "losing", "struggle")),
)


def _address(text: str) -> str | None:
    """The first word with an at sign in it, without the punctuation that closes a sentence."""
    found = ADDRESS.search(text)
    return None if found is None else found.group(0).rstrip(".:!?")


def _name(text: str) -> str | None:
    """The last line that holds no at sign, which is where a person signs."""
    lines = [line.strip() for line in text.splitlines() if line.strip() and "@" not in line]
    return lines[-1] if lines else None


def _awareness(text: str) -> str:
    """The most aware level whose phrases the text contains, and `unaware` otherwise."""
    folded = text.casefold()
    for level, phrases in SIGNALS:
        if any(phrase in folded for phrase in phrases):
            return level.value
    return Awareness.UNAWARE.value


class FakeExtractor:
    """The fixed rules above, behind the shape of an extractor."""

    def extract(self, text: str) -> dict[str, object]:
        """The fields these rules find. A field they cannot find is left out."""
        fields: dict[str, object] = {"awareness": _awareness(text)}
        name, address = _name(text), _address(text)
        if name is not None:
            fields["name"] = name
        if address is not None:
            fields["email"] = address
        return fields
