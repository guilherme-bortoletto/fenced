# 18. A write is journaled first and undone from the journal alone

Status: accepted
Date: 2026-10-14

## Context

The README promises that a write is planned, shown as a diff, applied behind a flag, recorded
in a journal and undone from it. The third fence already refuses a write outside `writes/`. What
was open was the order of the steps, what the journal keeps, and what happens when the store
fails in the middle of a write.

A journal written after the store can miss a write that landed, because the process can stop
between the two. An undo that reads a second copy of the records can disagree with the journal
about what was there. And a journal that keeps the message a person wrote is a second place that
text lives, with none of the care the record store gets.

## Decision

`src/fenced/ports/` names two shapes. `Crm` reads, puts and removes a record by key. `Journal`
appends an entry and reads every entry back. Neither says where anything lives, which belongs to
an adapter.

`src/fenced/writes/plan.py` turns leads into a `Plan` by reading the store and writing nothing. A
change is a key with the record before and the record after, and a plan is shown as a diff of
those two. A record keeps the name, the address, the awareness and a SHA256 hash of the message.
It never keeps the message.

`src/fenced/writes/executor.py` simulates unless it is called with `really=True`. A real apply
first checks every change against the store and refuses the whole plan when a record is no longer
what the plan read. A key that already holds the record after is left out. Then it appends the
journal entry, then it writes the store, and only then it reports success.

`src/fenced/writes/undo.py` builds its plan from one journal entry, with every change turned around
and in the reverse order, and hands it to the same executor. So an undo is simulated by default,
journaled first and refused when the store has moved. An entry that another entry already undoes
is refused.

When a store write fails halfway, the executor undoes the entry it just wrote by that same route.
The changes that never landed already hold what the undo wants, so they are left out, and the
undo entry carries only what it put back. An apply that failed at its first write still gets an
undo entry, with no change in it, so the journal says the entry was put back.

The same fact seen from the undo side is that an entry records an attempt and not an outcome. So
the put back the executor writes after a failed write marks itself as one, in a field of its own
called `put_back`. That put back and the attempt it put back stand for nothing. Neither can be
undone and neither undoes anything. An undo of entry 1 that is written as entry 2, fails and is
put back by entry 3 leaves entry 1 free to be undone again. An apply that fails and is put back
leaves nothing to undo, and trying it again is applying its plan again.

Every other entry counts. An entry is undone when an entry that counts undoes it, and that happens
once. A second undo of the same entry is refused. Undoing the undo is how a thing comes back, and
that plan is the entry the undo undid, carried out again in full. Turning the undo around is not
enough, because an undo carries only the changes it had to make, and the executor leaves out a key
that already holds what it wants.

An entry may not be undone twice because that history cannot be read back. Two earlier versions
of this record let it happen. They said an entry stands again once the entry that undid it is
itself undone. Then entry 2 can undo entry 1, entry 3 undo entry 2, and entry 5 undo entry 2 a
second time. The history becomes a tree, and the journal no longer says which branch the store
followed. A put back that changed nothing makes this worse, because turning it around changes
nothing either. Undone once, the history is a line, and the store holds the records of entry 1
exactly when the line says entry 1 stands. A test walks that line at random with a store that
fails at random and checks the store after every step.

## Consequences

Every record the store holds through this layer is one the journal carried first. A process that
stops between the two leaves an entry for a write that did not land. Undoing that entry leaves
those keys alone, because they already hold what the undo wants.

The journal keeps no text a person wrote. The price is that the store keeps none either, since
undo has to put back exactly what the journal holds. The message itself has to live somewhere
the person who wrote it agreed to, and that is not this layer.

A key is the address in lower case. Two leads with the same address in one plan are refused
rather than merged, because a person was shown two changes and would get one.

When the putting back fails as well, the executor stops and says so. The store holds part of two
entries and the journal carries both. A third attempt against a store that has failed twice is a
guess, so this is the one case handed to a person.

The third fence now refuses `put_lead` and `remove_lead` outside `writes/`, next to the names it
already refused. A port is a set of names, and a fence that did not know them would only catch the
import.
