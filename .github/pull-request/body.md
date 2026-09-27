Closes #33

## What

`run_rules` in `scripts/gates.py` makes the checks and writes the accounting in one pass. It
replaces `rules_run`, which took a flag and a list, knew three rules, and was asked for names by a
hook that had just run four. The hook now says it ran the identity rule and the message rule,
because it did.

    gates: ran the tests, the text rules, the identity rule, the message rule

A command that moves commits rather than writing one gives the identity rule nothing to read. That
is a rule the run could not make, so it carries a reason like every other skipped rule, and the
verdict stops covering it.

    gates: did not run the identity rule, because this command writes no commit
    gates: clean apart from the term rules, the identity rule

A run with no command in front of it is not about a commit at all, so it names neither of the two
rules that read one. What `python scripts/gates.py` prints has not moved.

`writes_a_commit` now holds the question the identity rule is asked. The rule asks it before it
runs and the accounting asks it before it names, so the two answers are one answer.

## Why

Record 0009 says a run says which rules it ran and which it could not, and that `clean` never
covers a rule that did not run. The hook broke that rule while reporting it. Four checks ran and
the line named two, so a reader who took it at its word did not know the address the commit would
carry had been read, or that the message had been read at all.

The hook is also the only place the identity rule is ever reported, because a plain run has no
commit in front of it. The one line where a reader could find out that rule exists was the line
leaving it out.

The two counts could drift because they were written apart. `run_hook` collected findings and then
asked `rules_run(True, terms)` for names. Nothing tied them together, and no test read one against
the other.

## Tests

The three tests that called `rules_run` go through `run_rules` now, with the checks replaced by
stand ins, so they still read the naming without running this suite from inside this suite.

`test_the_hook_names_every_rule_it_ran` runs the hook over a passing commit with every check
replaced by a stand in that records the call, then compares the calls with the names in the line
the hook wrote. How many rules there are is written down nowhere in it. I planted the bug the issue
describes by deleting the line that names the message rule, watched that test fail, and put the
line back.

`test_the_hook_leaves_out_the_identity_rule_when_the_command_writes_no_commit` reads the same line
over a push, then the reason under it and the verdict under that.

`test_a_run_with_no_command_names_neither_rule_that_reads_one` holds the plain run to the two rules
it makes.

273 tests pass.

## Decisions I made

A rule with nothing in front of it is not a rule the run skipped. A plain run of the gate is not
about a commit, so it names the identity rule and the message rule nowhere, rather than listing
both as skipped every time a person runs the gate by hand. The other reading puts two lines about a
commit in front of someone who is not making one, and stretches `clean apart from` over rules that
were never part of that run. A push is a different case, because there the hook does read a
command, so there the identity rule is named with its reason.

The two rules are called `the identity rule` and `the message rule`, which is what the issue calls
them.

A fence that misses a case is ordinary work, so the fix needed no record. The reading above is a
decision a reader would ask about, so it went to
`docs/adr/0012-a-run-names-a-rule-only-where-it-has-something-to-read.md` with a row in the index.

## Run notes

Quoting the text rule of `AGENTS.md` before anything else: "No dash used as punctuation and no semicolon, in Markdown or in a docstring. Short sentences. Describe what is there instead of selling it."

What I did. I took issue 33, the lowest numbered open issue labelled night with no pull request,
and read its body and not its comments. I branched from `origin/main`, because the local `main` in
this clone pointed at an older commit than the one the remote carries. One commit, pushed right
after it was made, then these two files and the push that carries them.

What I did not do. I did not touch record 0009. A record is not rewritten to match a later opinion,
so the reading that follows from it went into 0012. I did not run the term rules, because this
clone has no list of private terms to run them over, so nothing in this branch proves anything
about how a term is matched. The hook test does not watch the term rules separately either, for
the same reason. They ride inside the text rules and there is no list here to make them visible.

How long the gates took. `python -m pytest` runs 273 tests in 0.6 seconds and
`python scripts/gates.py` takes 0.8 seconds end to end. pytest was not installed in this container,
so the gate refused with `pytest is not installed, so the tests did not run` until I installed it.
That is the gate failing closed, and installing the one development dependency is not a fence
softened to get a commit through.
