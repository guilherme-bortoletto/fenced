# 26. A draft is printed and kept nowhere

Status: accepted
Date: 2026-10-15

## Context

Issue 54 puts the reply on the path of the command line. For each lead a seller takes, a run now
renders `reply.draft` for its level of awareness and prints it under the lead as a draft for a
person to send. Nothing is sent. A lead with no seller gets no draft and a line that says why.

The issue asked for a decision on whether a draft is kept anywhere after the run, and ruled out
one place for it. The journal keeps fields and a hash and never text, which record 0018 decided,
so a draft never goes there.

## Decision

A draft is printed and kept nowhere. It does not go into the store, it does not go into the
journal, and the run writes no file of drafts beside them. A test reads both files after a run
with `--write` and finds no draft in either, and finds no third file in the folder.

A draft is computed from the level of awareness, the products the lead named, the catalog and the
roster. The store keeps the first two through the lead, and the tables sit in `examples/` or
wherever `--catalog` and `--sellers` point. So the next run renders the same draft again from what
is already kept, as long as the tables have not moved. When they have moved, the draft that comes
out is the one that matches the price and the seller as they stand, which is the draft a person
should send. A stored draft would go stale the day a price moves, the same way record 0025 says a
stored score would.

A draft is also text that leaves the building once a person sends it. Keeping it in a file would
make that file the second place a sentence about a person lives, with an undo that record 0018
never planned for.

## Consequences

A person who wants a draft reads it off the run. A run with `--write` prints the same drafts as a
run without it, because writing changes the store and not the reply.

Nothing here records whether a draft was sent, when, or by whom. That is the step after this one,
and it is the step that first needs a draft kept. It gets its own record when it comes.
