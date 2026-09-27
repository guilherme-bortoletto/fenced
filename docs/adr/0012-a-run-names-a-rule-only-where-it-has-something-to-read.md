# 12. A run names a rule only where it has something to read

Status: accepted
Date: 2026-09-22

## Context

Record 0009 says a run says which rules it ran and which it could not, and that `clean`
never covers a rule that did not run. It was written over three rules. The suite, the text
rules and the term rules.

The hook runs two more. It reads the author and the committer address of the commit a
command is about to write, and it reads the message of that command for the line a tool
appends. Either one blocks the commit. Neither was in the line the hook printed about
itself.

    gates: ran the tests, the text rules
    gates: did not run the term rules, because no list of private terms was pointed at
    gates: clean apart from the term rules

Four rules ran and the line named two. The mistake pointed the safe way, because a reader
was told less than the run did, and the line is still called what a run says it did.

The two could drift because they were written apart. The checks ran in `run_hook`, and the
naming came back from `rules_run(True, terms)`, which took a flag and a list and knew
nothing about the command in front of it. A caller could add a rule, or pass a flag that
said something the run had not done, and no test would notice.

The hook is also the only place the identity rule is ever reported. A plain run of the gate
has no commit in front of it, so that rule has nothing to read there.

## Decision

A rule is run and named in the same place. `run_rules` collects the findings and the
accounting in one pass, so a rule cannot run without being named and cannot be named
without running.

A run names a rule only where that rule has something to read. A hook reads a command, so
it can name the identity rule and the message rule, and it names each one only where what
that rule reads is in the command.

    git commit -m 'a step'
    gates: ran the tests, the text rules, the identity rule, the message rule

A command that moves commits rather than writing one, such as a push, gives the identity
rule nothing to read. A command with no message on it gives the message rule nothing to
read, because that rule reads the words a command carries behind `-m`. Each is a rule the
run could not make, so each carries a reason like any other. A push is both.

    git push origin a-branch
    gates: did not run the identity rule, because this command writes no commit
    gates: did not run the message rule, because this command carries no message

The two are asked separately, because a command can be the one and not the other. A merge
writes a commit and usually carries no message. A commit with no message on it asks an
editor for one, and what the editor is given reaches the commit without any gate reading it.
That is the case a reader of the line is owed most.

    git commit
    gates: ran the tests, the text rules, the identity rule
    gates: did not run the message rule, because this command carries no message

A run with no command at all is a different case. `python scripts/gates.py` is not about a
commit, so the two rules that read one are not rules it skipped, and it names neither. What
that run prints does not move.

## Consequences

The hook writes up to two more names when it speaks, which is when a rule was skipped or
when it blocks. A reader of that line now finds out whether the address and the message were
read. On a command that carries no message the line says the message was not read, which is
a line no run wrote before, and a commit that asks an editor for its message is the reason
to write it.

A plain run still says nothing about the identity rule, so a reader who wants to know that
rule exists reads the hook or reads this record. Listing it as skipped on every plain run
was considered and rejected. It puts two lines about a commit in front of a person who is
not making one, and it stretches `clean apart from` over rules that were never part of that
run, which is the opposite of the reading record 0009 asks for.

A test in `tests/test_gates.py` runs the hook over a passing commit with every check
replaced by a stand in that records the call, then compares the calls with the names in the
line the hook wrote. The count of rules is written down nowhere in that test. A rule that
runs without being named fails it, and so does a name with no check behind it.

That comparison does not ask whether a rule had anything to read, because a check called
over nothing is still a call, and a rule named over nothing still matches its own name. So
the comparison is run over a command of each shape a guarded verb comes in. One that writes
a commit and carries a message, one that writes a commit and carries none, and one that does
neither.
