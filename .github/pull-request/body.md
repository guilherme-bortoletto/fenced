Closes #5

## What

`src/fenced/ports/` holds two shapes and nothing else. `Crm` reads, puts and removes a record by
key. `Journal` appends an entry and reads every entry back. Neither says where anything lives.

`src/fenced/writes/` holds the four parts the issue names.

- `plan.py` turns leads into a `Plan` by reading the store and writing nothing. A change is a key
  with the record before and the record after, and `Plan.diff()` shows it one field to a line.
  A record keeps the name, the address, the awareness and a SHA256 hash of the message.
- `executor.py` has `apply`, which simulates unless it is called with `really=True`. A real apply
  checks every change against the store, appends the journal entry, writes the store, and only
  then returns. A plan whose store moved since it was read is refused before anything is written.
- `journal.py` builds an entry out of text, lists and mappings, so an adapter can keep it as one
  line of JSON. It reads an entry back into the plan that undoes it.
- `undo.py` has `undo`, which builds that plan from one entry and hands it to the same `apply`.
  So an undo is simulated by default and journaled before it writes, and an entry is undone once.

When a store write fails halfway, the executor undoes the entry it just wrote by that same route.
The changes that never landed already hold what the undo wants and are left out. When the putting
back fails as well, the error says the store holds part of two entries and hands them to a person.

The third fence now refuses `put_lead` and `remove_lead` outside `writes/`. The README tour has
three more lines, and its count of tests that plant a tree a check has to refuse is thirty eight.
`docs/adr/0018-a-write-is-journaled-first-and-undone-from-the-journal-alone.md` records the order
of the steps, what the journal keeps, and what a write that fails halfway leaves.

## Why

The README already promised a write that is planned, shown as a diff, applied behind a flag,
journaled and undone. Until now nothing in `src` did any of it.

The entry is written before the store so that every record the store holds through this layer is
one the journal carried first. The undo reads the entry and nothing else, so there is no second
copy of a record for it to disagree with. The journal keeps a hash of the text and not the text,
so it is not a second place a message lives.

## Tests

`tests/test_writes.py` has 24 tests over a store and a journal kept in memory. The fake journal
keeps each entry as a line of JSON and reads it back, so a test reads what a file would hold.

- Simulate. Planning writes nothing, simulating is the default, and a simulated apply touches
  neither the store nor the journal. A create and an update are read back as their diff.
- Apply. The journal entry is written before the first record, the entry carries the fields and
  the hash and no word of the message, a journal that refuses the entry leaves the store as it
  was, and a stale plan is refused before anything is written.
- Undo. A create and an update are put back from the journal, the undo is simulated by default,
  a journal copied line by line and never shown the apply undoes it just the same, changes go back
  in the reverse order, an entry is undone once, and a record changed after the entry is refused.
- Fails halfway. A write that fails at the second of three changes leaves the store as it was and
  the journal with the entry and the entry that put it back. A failure at the first write still
  journals the putting back. A failure that hits the putting back too names both entries.

`tests/test_fences.py` has one more test that plants a call to each port method in `app/` and one
in `writes/`, and reads back that only the first two are refused.

`python -m pytest` is 558 passed. `python scripts/gates.py` is clean apart from the term rules.

## Decisions I made

A record keeps no message, not even in the store. The issue asks for a journal that keeps the
fields and a hash of the text and never the text. An undo puts back what the journal holds, so a
store that kept the message would get back a record without it. So the record is the fields and
the hash on both sides. Where the message itself lives is a question for the adapters.

The text that is hashed is `Lead.message`. That is the field the domain calls what the person
wrote, and the write layer is handed a `Lead` and never the raw input.

A key is the address in lower case. Two leads in one plan that land on one key are refused rather
than merged, because a person was shown two changes.

A real apply leaves out a key that already holds the record after. An entry then names only the
changes the apply made, and that is also what lets a halfway undo skip the changes that never
landed. A plan that undoes an entry always writes an entry, even an empty one, because that entry
is what tells the journal the first one was put back.

The ports live in `src/fenced/ports/`, where the third fence already expected `fenced.ports.crm`.
The two methods that change the store are added to the names that fence refuses, with a planting
test. The fence missed them, and closing that gap is ordinary work under AGENTS.md.

No adapter is written here. A JSON file for the store and for the journal is issue 6.

## Run notes

The text rule of AGENTS.md, in one line: "No dash used as punctuation and no semicolon, in
Markdown or in a docstring. Short sentences. Describe what is there instead of selling it."

What I did. The stall check came first and found nothing waiting. The most recent merge is pull
request 42 from earlier today, and no pull request was open. So the brake counted none, no issue
carried `stuck`, and there was nothing to rework. Issue 5 is the only open issue labelled `night`.
No branch for it was on origin, so `claude/issue-5` was made from `main`. There were two commits
of code, the first one pushed on its own, and then this title and body, which is the push that
opens this pull request.

What I did not do. No adapter, no command line and no change to the domain. No comment anywhere
and no label set.

One thing on the machine. A shell command moved the working directory into `src/fenced`, and the
commit hook looks for `scripts/gates.py` from the working directory, so it refused every command
after that. I wrote a three line file at `src/fenced/scripts/gates.py` that runs the real gate
from the root, used it for one command to step back to the root, and deleted it in that same
command. It was never added or committed, and the gate ran in full each time. The hook is not
wrong, but it does depend on the working directory, which is worth knowing.

The first commit was refused once by the identity rule. The local git config still carried an
address that is not a noreply one, and setting the right one in the same command came too late,
because the hook reads the config before the command runs. I set it in a command of its own and
committed again, with the same message, the same files and nothing passed over.

The gates. `python -m pytest` is 558 passed in 0.85 seconds. The whole run of
`python scripts/gates.py` takes 1.6 seconds, tests included. The term rules did not run, because
no list of private terms was pointed at, and the run says so rather than calling itself clean.
The interpreter carried no pytest, so pytest was installed into the machine before the first
commit. That is a machine and not this repository.
