"""A lead, and the five levels of awareness a message can show.

The model reads free text and returns fields. This module decides whether those
fields are a lead at all. Everything here is a pure function of what is passed
in, so the rules can be tested without a network, a clock or a file.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

REQUIRED = ("name", "email", "message")


class LeadError(ValueError):
    """Anything the domain refuses to accept as a lead."""


class MissingField(LeadError):
    """A field the domain needs and did not get."""


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

        Spacing, case and hyphens are forgiven, because they are spelling and not
        meaning. A sixth level is not forgiven.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            wanted = value.strip().lower().replace(" ", "_").replace("-", "_")
            for level in cls:
                if wanted == level.value:
                    return level
        known = ", ".join(level.value for level in cls)
        raise UnknownAwareness(f"{value!r} is not one of {known}")


@dataclass(frozen=True)
class Lead:
    """What a person wrote, once the domain has agreed to call it a lead."""

    name: str
    email: str
    message: str
    awareness: Awareness

    def __post_init__(self) -> None:
        for field in REQUIRED:
            if not str(getattr(self, field)).strip():
                raise MissingField(f"a lead needs a {field}")
        local, _, host = self.email.partition("@")
        if not local or "." not in host:
            raise InvalidEmail(f"{self.email!r} is not an address")
        if not isinstance(self.awareness, Awareness):
            raise UnknownAwareness(f"{self.awareness!r} is not a level of awareness")

    @classmethod
    def from_fields(cls, fields: Mapping[str, object]) -> Lead:
        """Build a lead from what an extractor returned, refusing anything else.

        This is the boundary. Past it, every value has a type the rest of the
        domain can rely on.
        """
        missing = [name for name in REQUIRED if name not in fields]
        if missing:
            raise MissingField(f"a lead needs {', '.join(missing)}")
        if "awareness" not in fields:
            raise MissingField("a lead needs an awareness")
        return cls(
            name=str(fields["name"]).strip(),
            email=str(fields["email"]).strip(),
            message=str(fields["message"]).strip(),
            awareness=Awareness.parse(fields["awareness"]),
        )
