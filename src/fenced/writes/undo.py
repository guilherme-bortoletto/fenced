"""Undo, which reads one journal entry and nothing else.

`undo` builds the plan that turns an entry around and hands it to the executor, so an undo
is simulated by default, journaled before it writes, and refused when the store has moved
since the entry was written. Undoing an entry twice is refused by the journal itself.
"""

from __future__ import annotations

from fenced.ports.crm import Crm
from fenced.ports.journal import Journal
from fenced.writes.executor import Outcome, apply
from fenced.writes.journal import undo_plan


def undo(number: int, crm: Crm, journal: Journal, *, really: bool = False) -> Outcome:
    """Put back what one entry changed, or show what putting it back would do."""
    return apply(undo_plan(journal, number), crm, journal, really=really)
