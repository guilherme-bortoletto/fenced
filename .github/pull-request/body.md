Closes #31

## What

The publisher now reads one number twice. It reads `claude/issue-N` off the head branch it was
given, and it reads `Closes #M` off the first line of the body. It refuses when the two differ,
and it refuses before it asks GitHub anything, so a refusal leaves no call behind.

It also refuses a body that does not open with `Closes #N` at all, and a head branch that names no
issue. Reading nothing out of a body and publishing it anyway is the shape of this bug.

Four tests read `.github/workflows/pull-request.yml` and fail when the publish step could run
without the check, which is when it names a head of its own or reads one from anywhere but the
branch that was pushed.

`docs/adr/0011-a-body-names-the-issue-its-branch-names.md` records the decision and says what the
check does not cover. `AGENTS.md` now says which push opens the pull request in the same words
record 0008 uses.

## Why

The title and the body land on `main` with every pull request that carries them. They stay there
until the next one lands, so a branch inherits the text of the run before it at the moment it is
cut. `AGENTS.md` tells a run to push right after its first commit. The workflow runs on that push,
finds the two files, and publishes.

The text gate passes, because that text was written to pass it. The publisher reads the pull
request back and gates the stored body, and that passes for the same reason. Nothing in the path
could tell that the text belonged to another issue. Pull request 30 is what that looks like, a
branch named `claude/issue-25` carrying a body that says `Closes #23`.

The number is the one thing the two texts cannot share. The branch name carries it and the first
line of the body carries it, and a body written for another run says the wrong one.

## Tests

`tests/test_publish.py` grows ten tests and the suite goes from 257 to 267.

Six plant the publisher. A body that closes the issue the branch names, a body that closes another
one, a body that opens with something else, a body with nothing in it, a number further down the
body that is not read, and a head branch that names no issue. Each refusal asserts that the fake
transport recorded no call at all.

Four read the workflow as text. That the publish step hands the publisher the branch that was
pushed, that a step naming a head of its own is refused, that a step reading no pushed branch is
refused, and that a step with no head at all is refused.

`python -m pytest` and `python scripts/gates.py` ran before every commit and both were clean, apart
from the term rules, which this clone has no list for.

## Decisions I made

A new record rather than an edit to record 0008. The index says a record is not rewritten to match
a later opinion. Record 0008 already said the pull request opens on the push that carries the body,
so the two agree once `AGENTS.md` says it as plainly. The check is a decision of its own, and it
carries its own account of what it does not cover.

A head branch that names no issue is refused rather than published. The workflow fires on every
`claude/` branch and only `claude/issue-N` carries a number. A branch of another shape leaves the
check nothing to read, and a publish with nothing to check is the publish this stops.

The number is read off the first line that has anything on it, so a body that opens with a blank
line still reads. Nothing further down is read, because a body names other issues in its prose and
a record it cites carries a number too.

The check runs before the text gate. A body written for another run is not this run's text at all,
and no text rule can tell.

The workflow file is unchanged. Its publish step already hands the publisher the branch that was
pushed through the environment, and the four new tests hold it there.

## Run notes

The text rule of `AGENTS.md`: "No dash used as punctuation and no semicolon, in Markdown or in a
docstring. Short sentences. Describe what is there instead of selling it."

Three commits. The first removed `.github/pull-request/title.md` and
`.github/pull-request/body.md`, which were the text of the run on issue 28, and pushed, so that
this run published nothing of somebody else's while it worked. The second added the check and the
ten tests. The third added record 0011, its index row and the wording in `AGENTS.md`. This commit
writes the title and the body back, and the push that carries it is the one that opens this pull
request.

What I did not do. Record 0008 was left as it stands. The workflow was left as it stands. The
publisher on `main` is what runs for this branch, so the check lands with this pull request and
guards the runs after it, not this one.

The gates. `python scripts/gates.py` took about one second on each of the three runs, of which the
suite is about six tenths of a second for 267 tests. Nothing was slow enough to time.
