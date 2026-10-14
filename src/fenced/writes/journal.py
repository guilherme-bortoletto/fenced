"""What one apply leaves in the journal, and how the journal is read back.

An entry has a number, the number of the entry it undoes or None, and every change the
apply made with the record before it and the record after it. A record holds the
extracted fields and a hash of the text, as `plan.record_of` builds it, so an entry holds
no text a person wrote.

The entry is the only thing an undo reads. There is no copy of a record anywhere else for
it to read instead, so the journal and the undo cannot disagree about what was there.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from fenced.ports.journal import Journal
from fenced.writes.plan import Change, Plan


class JournalError(ValueError):
    """A journal the write layer cannot read an entry from."""


class UnknownEntry(JournalError):
    """A number no entry in the journal carries."""


class AlreadyUndone(JournalError):
    """An entry another entry already puts back."""


def entry_of(number: int, plan: Plan, changes: Sequence[Change]) -> dict[str, object]:
    """The entry for an apply, made of text, lists and mappings and nothing else."""
    return {
        "entry": number,
        "undoes": plan.undoes,
        "changes": [
            {
                "key": change.key,
                "before": None if change.before is None else dict(change.before),
                "after": None if change.after is None else dict(change.after),
            }
            for change in changes
        ],
    }


def changes_in(entry: Mapping[str, object]) -> tuple[Change, ...]:
    """The changes an entry carries, in the order the apply made them."""
    written = entry.get("changes")
    if not isinstance(written, list):
        raise JournalError(f"entry {entry.get('entry')} carries no list of changes")
    return tuple(Change(row["key"], row["before"], row["after"]) for row in written)


def next_number(journal: Journal) -> int:
    """The number the next entry carries, which is one more than the last."""
    numbers = [entry["entry"] for entry in journal.entries()]
    return max(numbers, default=0) + 1


def undo_plan(journal: Journal, number: int) -> Plan:
    """The plan that puts back what one entry changed, read from the journal alone.

    The changes run in the reverse order, each one turned around, so the last change the
    apply made is the first one put back. An entry that another entry already undoes is
    refused, because undoing it twice would put back a state nobody asked for.
    """
    entries = journal.entries()
    found = [entry for entry in entries if entry.get("entry") == number]
    if not found:
        raise UnknownEntry(f"the journal carries no entry {number}")
    undone_by = [entry["entry"] for entry in entries if entry.get("undoes") == number]
    if undone_by:
        raise AlreadyUndone(f"entry {number} is already undone by entry {undone_by[0]}")
    changes = changes_in(found[0])
    return Plan(tuple(change.inverse() for change in reversed(changes)), undoes=number)
