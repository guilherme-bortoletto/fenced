# 9. A run says which rules it could not run

Status: accepted
Date: 2026-09-19

## Context

`scripts/gates.py` checks three rules. The suite, which carries the six fences. The text
rules, which read punctuation and the line a publishing tool appends. The term rules, which
refuse a private word.

The term rules need a list, and the list is not here and never will be. It is named by
`FENCED_TERMS_FILE` in `.claude/settings.local.json`, which `.gitignore` keeps out of every
clone. So a run in a sandbox has no list, the term rules do not run there, and the gate
printed `gates: clean` all the same.

`clean` is a word about every rule. Printed by a run where one rule never started, it says
something that is not true, and it says it to the one reader who has no other way to find
out. The branch on #19 changed how a term is matched, ran the gate before every commit as
the procedure says, and was told everything was fine while the new matching refused a file
already on `main`.

The gate was not lying about what it could see. It was reporting a partial run in the words
of a full one.

The same hole is in `--text`. That route never runs the suite, and it printed `clean` too.

## Decision

A run says which rules it ran and which it could not, with the reason for each, and the word
`clean` never covers a rule that did not run.

    gates: ran the tests, the text rules
    gates: did not run the term rules, because no list of private terms was pointed at
    gates: clean apart from the term rules

With a list, all three ran and the last line is `gates: clean` on its own.

The exit code does not move. A clone with no private list is the ordinary state of a clone,
not a failure, so a run without one still exits zero. This is a reporting rule and not a new
refusal. The gate that fails closed is the one that cannot read something it was given, such
as a terms file that is there and will not open, and that one already exits one.

The hook says the same thing on the same terms. It is silent when every rule ran and nothing
was found, because a hook that speaks on every command is a hook a reader stops reading, and
it writes the accounting when a rule was skipped or when it blocks.

## Consequences

A run in a sandbox is now told, on every gate, that the term rules did not run. That is the
point and it is meant to be read as a limit on what the run proved.

It follows that a change to how a term is matched is proved on a machine that holds a list.
A run can write the code and the test, and the test can carry an invented term of its own,
which is what `tests/test_gates.py` does. What a run cannot do is measure the new matching
against the real list, so the last word on that change belongs to the machine that has one.
`AGENTS.md` says so in the same place it names `FENCED_TERMS_FILE`.

Three lines of output where there was one is the cost. Reading them is cheap next to a
branch that changes a rule and is told it passed a rule that never ran.

Failing instead of reporting was considered and rejected. A missing list would then block
every commit in every clone that is not the one machine, which makes the gate unusable in
the place it is most often run, and a gate people route around is worse than a gate that
says less than they hoped.

Naming the list in this repository so that every clone has one was considered and rejected
for the reason the list exists. Writing down what you are hiding, in the place you are
hiding it from, is not a gate.
