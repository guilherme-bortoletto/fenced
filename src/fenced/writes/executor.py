"""The one place a plan reaches the record store.

`apply` simulates unless it is told `really=True`. A simulation reads the plan and returns
its diff, and it touches neither the store nor the journal.

A real apply checks every change against the store first, then writes the journal entry,
then writes the store, and only then reports success. The entry goes first so that a
store write that lands is always one the journal already carries.

When a store write fails halfway, the executor undoes the entry it just wrote, by the
same route `undo` takes. That is a plan read from the journal alone, journaled before it
writes, and the changes that never landed are already what it wants and are left alone.
Its entry is marked as a put back, so the journal reads the attempt and the put back as
standing for nothing.
When the putting back fails as well, both entries are in the journal, the store holds
part of each, and the error says so. That is the one case handed to a person, because a
second automatic attempt against a store that has failed twice is a guess.
"""

from __future__ import annotations

from dataclasses import dataclass

from fenced.ports.crm import Crm
from fenced.ports.journal import Journal
from fenced.writes.journal import entry_of, next_number, undo_plan
from fenced.writes.plan import Change, Plan


class WriteError(RuntimeError):
    """A plan the executor did not carry out."""


class StalePlan(WriteError):
    """A plan whose record before is no longer what the store holds."""


class ApplyFailed(WriteError):
    """A store write that failed after the journal entry was written."""


@dataclass(frozen=True)
class Outcome:
    """What an apply did.

    `simulated` is True when nothing was written. `entry` is the number of the journal
    entry a real apply wrote, and None when it wrote none.
    """

    simulated: bool
    entry: int | None
    diff: tuple[str, ...]


def _write(crm: Crm, change: Change) -> None:
    """Make one change in the store."""
    if change.after is None:
        crm.remove_lead(change.key)
    else:
        crm.put_lead(change.key, change.after)


def _to_make(crm: Crm, plan: Plan) -> list[Change]:
    """The changes the store still needs, or a refusal when it holds something else.

    A key that already holds the record after is left alone and kept out of the entry,
    because an undo of a change nobody made would take away a record somebody else put
    there. A key that holds neither the record before nor the one after was changed since
    the plan was read, and the whole plan is refused before anything is written.
    """
    needed = []
    for change in plan.changes:
        held = crm.read_lead(change.key)
        held = None if held is None else dict(held)
        if held == change.after:
            continue
        if held != change.before:
            raise StalePlan(f"{change.key} changed after the plan was read")
        needed.append(change)
    return needed


def apply(plan: Plan, crm: Crm, journal: Journal, *, really: bool = False) -> Outcome:
    """Carry out a plan, or show what carrying it out would do.

    The default is to simulate. A real apply that has nothing left to change writes no
    entry and reports none, unless the plan undoes an entry. That plan always writes one,
    because its entry is what tells the journal the entry before it was put back.
    """
    if not really:
        return Outcome(simulated=True, entry=None, diff=tuple(plan.diff()))
    return _apply(plan, crm, journal, putting_back=False)


def _apply(plan: Plan, crm: Crm, journal: Journal, *, putting_back: bool) -> Outcome:
    """A real apply, and the putting back of one that failed when `putting_back` is set."""
    needed = _to_make(crm, plan)
    if not needed and plan.undoes is None:
        return Outcome(simulated=False, entry=None, diff=())
    made = Plan(tuple(needed), undoes=plan.undoes)
    number = next_number(journal)
    journal.append(entry_of(number, made, needed, put_back=putting_back))
    for position, change in enumerate(needed, start=1):
        try:
            _write(crm, change)
        except Exception as failed:
            stopped = f"entry {number} stopped at change {position} of {len(needed)}"
            if putting_back:
                raise ApplyFailed(stopped) from failed
            try:
                back = _apply(undo_plan(journal, number), crm, journal, putting_back=True)
            except Exception as also:
                raise ApplyFailed(
                    f"{stopped}, and putting it back failed too, so the store holds part of "
                    f"entry {number} and part of the entry after it, and a person reads both "
                    "before anything else is written"
                ) from also
            raise ApplyFailed(f"{stopped}, and entry {back.entry} put it back") from failed
    return Outcome(simulated=False, entry=number, diff=tuple(made.diff()))
