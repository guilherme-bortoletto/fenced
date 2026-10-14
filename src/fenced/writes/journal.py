"""What one apply leaves in the journal, and how the journal is read back.

An entry has a number, the number of the entry it undoes or None, whether it is the put
back the executor wrote after a failed write, and every change the apply made with the
record before it and the record after it. A record holds the
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


class StandsForNothing(JournalError):
    """A put back, or the failed attempt it put back, which no undo can reach."""


def entry_of(
    number: int, plan: Plan, changes: Sequence[Change], *, put_back: bool = False
) -> dict[str, object]:
    """The entry for an apply, made of text, lists and mappings and nothing else.

    `put_back` is True only for the entry the executor writes to put back a failed write.
    """
    return {
        "entry": number,
        "undoes": plan.undoes,
        "put_back": put_back,
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


def put_backs(entries: Sequence[Mapping[str, object]]) -> dict[int, int]:
    """Each failed attempt that was put back, with the number of the put back.

    An entry is written before the store, so it records an attempt and not an outcome. When
    a store write fails, the executor puts the attempt back at once and marks that entry as
    a put back. The attempt and its put back then stand for nothing together. Neither can be
    undone and neither undoes anything, so the line of undos is read without them.
    """
    return {
        entry["undoes"]: entry["entry"]
        for entry in entries
        if entry.get("put_back") and entry.get("undoes") is not None
    }


def counts(entries: Sequence[Mapping[str, object]], number: int) -> bool:
    """Whether an entry stands for something, which is false for a put back and its attempt."""
    by_number = {entry.get("entry"): entry for entry in entries}
    return not by_number[number].get("put_back") and number not in put_backs(entries)


def undone(entries: Sequence[Mapping[str, object]]) -> dict[int, int]:
    """Each entry that stands undone, with the number of the entry that undoes it.

    An entry is undone when an entry that counts undoes it, and that happens once, because
    `undo_plan` refuses an entry that is already undone. So every entry is undone by one
    entry at most and the history is a line. Undoing the undo is how a thing comes back.
    """
    found: dict[int, int] = {}
    for entry in sorted(entries, key=lambda entry: entry["entry"]):
        number, target = entry["entry"], entry.get("undoes")
        if target is not None and target not in found and counts(entries, number):
            found[target] = number
    return found


def intended(entries: Sequence[Mapping[str, object]], number: int) -> tuple[Change, ...]:
    """Every change one entry set out to make, which can be more than it carries.

    An entry that undoes nothing set out to make the changes it carries. An entry that
    undoes another carries only the changes it needed, because a key that already held
    what it wanted was left out. What it set out to do is still to put back the whole
    entry it undoes, so that is the entry it undoes set out to make, turned around and in
    the reverse order.
    """
    by_number = {entry.get("entry"): entry for entry in entries}
    if number not in by_number:
        raise UnknownEntry(f"the journal carries no entry {number}")
    entry = by_number[number]
    target = entry.get("undoes")
    if target is None:
        return changes_in(entry)
    return tuple(change.inverse() for change in reversed(intended(entries, target)))


def undo_plan(journal: Journal, number: int) -> Plan:
    """The plan that puts back what one entry set out to do, read from the journal alone.

    The changes run in the reverse order, each one turned around, so the last change the
    apply made is the first one put back. For an entry that undoes another, that is the
    other entry carried out again in full, as `intended` reads it, which is how a thing
    that was undone comes back.

    Two kinds of entry are refused. A put back and the attempt it put back stand for
    nothing, so trying the attempt again is applying its plan again. And an entry that is
    already undone is refused, because an entry undone twice turns the history into a tree
    and no reading of a tree tells which branch the store followed. The store decides which
    of these changes are still needed, because the executor leaves out a key that already
    holds what it wants.
    """
    entries = journal.entries()
    by_number = {entry.get("entry"): entry for entry in entries}
    if number not in by_number:
        raise UnknownEntry(f"the journal carries no entry {number}")
    if by_number[number].get("put_back"):
        target = by_number[number].get("undoes")
        raise StandsForNothing(
            f"entry {number} puts back entry {target} after a failed write and stands for nothing"
        )
    back = put_backs(entries).get(number)
    if back is not None:
        raise StandsForNothing(
            f"entry {number} failed and entry {back} put it back, so it stands for nothing, "
            "and trying it again is applying it again"
        )
    undone_by = undone(entries).get(number)
    if undone_by is not None:
        raise AlreadyUndone(f"entry {number} is already undone by entry {undone_by}")
    changes = intended(entries, number)
    return Plan(tuple(change.inverse() for change in reversed(changes)), undoes=number)
