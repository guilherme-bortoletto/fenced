"""A lead, and the five levels of awareness a message can show.

The model reads free text and returns fields. This module decides whether those
fields are a lead at all, and it refuses rather than coerces. Everything here is
a pure function of what is passed in, so the rules can be read and tested with no
network, no file and no real clock.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

REQUIRED = ("name", "email", "message")
# Characters that take no space and are not whitespace to `str.strip`.
INVISIBLE = "\u200b\u200c\u200d\u2060\ufeff"
SEPARATORS = re.compile(r"[\s\-_]+")


class LeadError(ValueError):
    """Anything the domain refuses to accept as a lead."""


class MissingField(LeadError):
    """A field the domain needs and did not get as text."""


class InvalidEmail(LeadError):
    """An address the domain will not try to reach."""


class UnknownAwareness(LeadError):
    """A level of awareness that is not one of the five."""


class Awareness(Enum):
    """The five levels, closed on purpose.

    The model picks one of these and nothing else. What to do at each level is a
    written rule in another module, not a judgement made here.
    """

    UNAWARE = "unaware"
    PROBLEM_AWARE = "problem_aware"
    SOLUTION_AWARE = "solution_aware"
    PRODUCT_AWARE = "product_aware"
    READY_TO_BUY = "ready_to_buy"

    @classmethod
    def parse(cls, value: object) -> Awareness:
        """Turn what the model returned into one of the five, or refuse it.

        Spacing, case, hyphens and underscores are forgiven, because they are
        spelling and not meaning. A sixth level is not forgiven.
        """
        known = ", ".join(level.value for level in cls)
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise UnknownAwareness(
                f"an awareness is one of {known}, written as text, not {type(value).__name__}"
            )
        wanted = SEPARATORS.sub("_", value.strip().lower())
        for level in cls:
            if wanted == level.value:
                return level
        raise UnknownAwareness(f"{value!r} is not one of {known}")


def _as_text(value: object, field: str) -> str:
    """One field, as text and trimmed, or a refusal. Nothing is coerced here.

    A model that returns a null, a number or a list has not given a name, and
    turning it into the string "None" would hide that from everything downstream.
    """
    if not isinstance(value, str):
        raise MissingField(f"a lead needs a {field} written as text, not a {type(value).__name__}")
    trimmed = value.strip().strip(INVISIBLE).strip()
    if not trimmed:
        raise MissingField(f"a lead needs a {field}")
    return trimmed


def _refuse_unreachable(address: str) -> None:
    """A shallow rule on purpose. What a mail server accepts is not this domain's business.

    It refuses only what is certainly unreachable: a missing local part, a host
    without a dotted name, more than one at sign, and any space or control
    character, which is how a header gets smuggled into whatever sends the reply.
    """
    if any(character.isspace() or ord(character) < 32 for character in address):
        raise InvalidEmail(f"{address!r} carries a space or a control character")
    if address.count("@") != 1:
        raise InvalidEmail(f"{address!r} is not an address")
    local, _, host = address.partition("@")
    labels = host.split(".")
    if not local or len(labels) < 2 or not all(labels):
        raise InvalidEmail(f"{address!r} is not an address")


@dataclass(frozen=True)
class Lead:
    """What a person wrote, once the domain has agreed to call it a lead.

    The constructor is the boundary. Whatever route a lead is built by, the same
    refusals and the same trimming happen here, so there is one rule and not two.
    """

    name: str
    email: str
    message: str
    awareness: Awareness

    def __post_init__(self) -> None:
        for field in REQUIRED:
            object.__setattr__(self, field, _as_text(getattr(self, field), field))
        object.__setattr__(self, "awareness", Awareness.parse(self.awareness))
        _refuse_unreachable(self.email)

    @classmethod
    def from_fields(cls, fields: Mapping[str, object]) -> Lead:
        """Build a lead from what an extractor returned, refusing anything else.

        Past this point every value has a type the rest of the domain can rely on,
        and every refusal is a `LeadError`.
        """
        if not isinstance(fields, Mapping):
            raise MissingField(f"a lead is built from a mapping, not a {type(fields).__name__}")
        missing = [name for name in (*REQUIRED, "awareness") if name not in fields]
        if missing:
            raise MissingField(f"a lead needs {', '.join(missing)}")
        return cls(
            name=fields["name"],
            email=fields["email"],
            message=fields["message"],
            awareness=fields["awareness"],
        )
