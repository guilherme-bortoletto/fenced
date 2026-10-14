Closes #7

## What

Two new decision records and three tests.

`docs/adr/0020-the-model-returns-fields-and-nothing-else.md` says why the model is asked for a
name, an address and a level of awareness and for nothing else. It links record 0016 for the
outgoing half and covers what that record leaves out. It also says what happens to an answer that
is not the fields. The extractor refuses an answer it cannot read as a JSON object and the run
stops before the plan. An answer that is an object crosses `Lead.from_fields`, which hands that
one message back and lets the rest go on. A key the boundary does not ask for is never read.

`docs/adr/0021-no-secret-enters-the-tree.md` says what the sixth fence catches and what it misses,
and names the test behind each claim. It describes the second layer outside the tree, which is the
private list of terms on the machine that writes the code and the repository secret the publisher
reads, without naming a term or a value.

`tests/test_fences.py` gains three tests marked `admits`, which plant a tree the secret fence
accepts. A `.env.example`, a workflow that pins an action by commit, and a key assembled from
pieces at run time. The README count of such tests goes from two to five.

Both records are in the index.

## Why

Issue 7 asked for three records a reader will ask about. The Answers section of the issue says
the numbers it named are taken, that a new record takes the next number, and that the record on
writes already exists as 0018. It also asks that the record on secrets claim only what a test
proves. Before this change no test proved anything the fence lets through. The three new tests
are what lets the record name a miss rather than guess at one.

## Tests

`python -m pytest` passes with 628 tests, three more than on `main`.
`python scripts/gates.py` reports clean apart from the term rules, which did not run because this
machine has no list. The README check reads the new count back, so the line that says five is a
test.

## Decisions I made

The record on writes is not written. Record 0018 already says why a write is planned, recorded and
reversible, as the Answers section says.

The two new records are 0020 and 0021, the next numbers after 0019.

I added three `admits` tests rather than describe the two exemptions written into the fence from
the code alone. The Answers section asks for claims a test proves, and the `.env.example`
exemption and the pinned action exemption had no test. The assembled key had an indirect proof,
because the planting test builds its shapes from pieces and the whole tree passes. It now has a
test of its own that says so.

The record on secrets claims only the three shapes a test plants. The other shapes in the table
are named as written and not claimed.

The second layer is described as the private list and the repository secret, as the Answers
section names them. A comment in the tests mentions push protection on GitHub. I did not count it
as part of the second layer, because nothing in this run could confirm it is on.

Record 0020 says the run stops before the plan when the extractor refuses an answer. That is read
off `src/fenced/app/cli.py`. The seven refused answers are tested on the extractor, and no test of
the command line plants one.

## Run notes

The text rule of AGENTS.md, in one line: "No dash used as punctuation and no semicolon, in
Markdown or in a docstring. Short sentences. Describe what is there instead of selling it."

What I did. The stall check came first. The most recent merge is pull request 47 from earlier
today, and no pull request on a `claude/` branch was open, so nothing was waiting. The brake
counted zero open night pull requests and no issue carried `stuck`. No pull request carried
`needs-work`. Issue 7 is the only open issue labelled `night`, so I took it, read its body and its
Answers section, and did not read its comments. The branch `claude/issue-7` did not exist on
origin, so I created it from `main`. I pushed after the first commit, which added record 0020,
and again after the second, which added record 0021 and the three tests.

The session that ran this was set up with a different branch name. AGENTS.md and the run
instructions both name `claude/issue-N`, and the publisher reads the issue number off that name,
so I worked on `claude/issue-7` and pushed nothing to the other branch.

What I did not do. I wrote no comment anywhere and opened no issue. I did not touch record 0018.
I did not add a test of the command line for an extractor that refuses an answer.

`pytest` was not installed for the interpreter `python` resolves to here. I installed it, and the
package in editable mode, before the first run. Nothing in the tree changed for that.

How long the gates took. `python -m pytest` took about 2.4 seconds and `python scripts/gates.py`
about 2.7 seconds on each run, three runs of the gate in all.
