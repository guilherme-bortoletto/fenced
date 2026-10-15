"""An extractor that reads by a few fixed rules, so a test knows what it returns.

It stands in for the model wherever no network is wanted, which is every test and the
default run of the command line. It is not a classifier and does not try to be one. The
rules are short enough to read in one go.

The address is the first word with an at sign in it. The name is the last line that holds
no at sign. The awareness is the first row of `SIGNALS` with a phrase the text contains,
read from the most aware level down, and `unaware` when no row matches.

The segment is the first row of `SEGMENTS` with a word the text has a word starting with.
The language is the row of `LANGUAGES` with the most of its words in the text, an earlier
row winning a tie. A product is a run of two or more words that each open with a capital
letter, on any line but the one the name was read from and those with an address. A text
that names none returns an empty list.

A field these rules cannot find is left out, so the boundary refuses the text the way it
would refuse a model that found none. A text with no address, no segment word or no
language word is handed back.
"""

from __future__ import annotations

import re

from fenced.domain.lead import Awareness, Language, Segment

ADDRESS = re.compile(r"[^\s<>()\[\],]+@[^\s<>()\[\],]+")
PRODUCT = re.compile(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)+\b")
WORD = re.compile(r"\w+")
# The phrases each level is read from, the most aware first. Written down so a reader
# argues with the table and not with the code.
SIGNALS = (
    (Awareness.READY_TO_BUY, ("ready to buy", "place an order", "send the invoice")),
    (Awareness.PRODUCT_AWARE, ("how much", "a quote", "your price")),
    (Awareness.SOLUTION_AWARE, ("compare", "options", "alternatives")),
    (Awareness.PROBLEM_AWARE, ("problem", "keeps", "losing", "struggle")),
)
# The words each segment is read from, in the order they are tried. A word matches a word
# of the text that starts with it, so `warehouse` finds `warehouses` and `shop` does not
# find `workshop`.
SEGMENTS = (
    (Segment.FOOD, ("bakery", "restaurant", "cafe", "kitchen")),
    (Segment.HEALTH, ("clinic", "pharmacy", "dental")),
    (Segment.MANUFACTURING, ("factory", "plant floor", "assembly")),
    (Segment.WHOLESALE, ("warehouse", "distributor", "wholesale")),
    (Segment.RETAIL, ("shop", "store", "shelves", "negozio", "loja", "tienda")),
)
# Short words that are common in one language and rare in the others, matched whole.
LANGUAGES = (
    (Language.ENGLISH, ("the", "and", "we", "our", "is", "please")),
    (Language.PORTUGUESE, ("não", "nossa", "nosso", "obrigado", "você", "uma")),
    (Language.SPANISH, ("el", "los", "nuestra", "gracias", "usted", "una")),
    (Language.FRENCH, ("le", "les", "nous", "notre", "merci", "est")),
    (Language.GERMAN, ("der", "die", "und", "wir", "unser", "bitte")),
    (Language.ITALIAN, ("il", "che", "nostro", "nostra", "grazie", "siamo")),
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


def _segment(text: str) -> str | None:
    """The first segment with a word the text has a word starting with, and None otherwise."""
    folded = text.casefold()
    for segment, words in SEGMENTS:
        if any(re.search(rf"\b{re.escape(word)}", folded) for word in words):
            return segment.value
    return None


def _language(text: str) -> str | None:
    """The language with the most of its words in the text, the earlier row on a tie."""
    words = WORD.findall(text.casefold())
    counted = [
        (sum(words.count(word) for word in table), language) for language, table in LANGUAGES
    ]
    most = max(count for count, _ in counted)
    if most == 0:
        return None
    return next(language.value for count, language in counted if count == most)


def _products(text: str, name: str | None) -> list[str]:
    """Every run of capitalised words, each once, off the lines that are not a signature."""
    found: list[str] = []
    for line in text.splitlines():
        if "@" in line or line.strip() == name:
            continue
        for product in PRODUCT.findall(line):
            if product not in found:
                found.append(product)
    return found


class FakeExtractor:
    """The fixed rules above, behind the shape of an extractor."""

    def extract(self, text: str) -> dict[str, object]:
        """The fields these rules find. A field they cannot find is left out."""
        name, address = _name(text), _address(text)
        fields: dict[str, object] = {
            "awareness": _awareness(text),
            "products": _products(text, name),
        }
        found = {
            "name": name,
            "email": address,
            "segment": _segment(text),
            "language": _language(text),
        }
        fields.update({field: value for field, value in found.items() if value is not None})
        return fields
