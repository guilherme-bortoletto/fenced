"""A write, planned before anything is written.

A plan is a list of changes, and a change is one key with the record it holds now and the
record it will hold after. Planning reads the store and writes nothing, so a plan can be
shown to a person as a diff and thrown away.

A record keeps what was extracted from a message and a hash of the message, and never the
message itself. So the journal that keeps a record before and after a change keeps no text
a person wrote, and an undo that puts a record back puts back no text either.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from fenced.domain.lead import Lead
from fenced.ports.crm import Crm, Record

TEXT_HASH = "text_sha256"


class PlanError(ValueError):
    """A plan the write layer refuses to build."""


class DuplicateKey(PlanError):
    """Two leads in one plan that land on the same record."""


def key_of(lead: Lead) -> str:
    """The key a lead is kept under, which is its address in lower case."""
    return lead.email.lower()


def text_hash(text: str) -> str:
    """The hash a record keeps in place of the text a person wrote."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record_of(lead: Lead) -> dict[str, str]:
    """The record a lead becomes. The message is kept as its hash and nothing else."""
    return {
        "name": lead.name,
        "email": lead.email,
        "awareness": lead.awareness.value,
        TEXT_HASH: text_hash(lead.message),
    }


def _frozen(record: Mapping[str, str] | None) -> Mapping[str, str] | None:
    """A copy of a record the caller cannot change under the plan."""
    return None if record is None else dict(record)


@dataclass(frozen=True)
class Change:
    """One key, the record it holds before and the record it holds after.

    A change with no record before creates one, and a change with no record after takes
    one away. A change with neither is nothing and is refused.
    """

    key: str
    before: Record | None
    after: Record | None

    def __post_init__(self) -> None:
        if self.before is None and self.after is None:
            raise PlanError(f"a change to {self.key} needs a record before or after it")
        object.__setattr__(self, "before", _frozen(self.before))
        object.__setattr__(self, "after", _frozen(self.after))

    def inverse(self) -> Change:
        """The change that puts this key back the way it was."""
        return Change(self.key, self.after, self.before)

    def diff(self) -> list[str]:
        """The change as lines a person reads, one field to a line.

        A field that goes away starts with a minus, a field that arrives starts with a
        plus, and a field that stays the same starts with two spaces.
        """
        verb = "create" if self.before is None else "remove" if self.after is None else "update"
        before = self.before or {}
        after = self.after or {}
        lines = [f"{verb} {self.key}"]
        for name in sorted(set(before) | set(after)):
            old, new = before.get(name), after.get(name)
            if old == new:
                lines.append(f"  {name}: {old}")
                continue
            if old is not None:
                lines.append(f"- {name}: {old}")
            if new is not None:
                lines.append(f"+ {name}: {new}")
        return lines


@dataclass(frozen=True)
class Plan:
    """The changes one apply makes, in the order it makes them.

    `undoes` names the journal entry this plan puts back, and is None for a plan that
    puts nothing back.
    """

    changes: tuple[Change, ...] = field(default_factory=tuple)
    undoes: int | None = None

    def diff(self) -> list[str]:
        """Every change as lines, with an empty line between two changes."""
        lines: list[str] = []
        for change in self.changes:
            if lines:
                lines.append("")
            lines += change.diff()
        return lines


def plan(crm: Crm, leads: Iterable[Lead]) -> Plan:
    """The plan that keeps these leads, read against what the store holds now.

    A lead whose record the store already holds as it stands makes no change. Two leads
    that land on one key are refused, because the second would quietly replace the first
    inside a plan a person was shown as two changes.
    """
    changes = []
    seen = set()
    for lead in leads:
        key = key_of(lead)
        if key in seen:
            raise DuplicateKey(f"two leads in one plan land on {key}")
        seen.add(key)
        before = crm.read_lead(key)
        after = record_of(lead)
        if before is not None and dict(before) == after:
            continue
        changes.append(Change(key, before, after))
    return Plan(tuple(changes))
