# 11. A pull request body names the issue its branch names, or it is not published

Status: accepted
Date: 2026-09-21

## Context

Record 0008 put the text of a pull request on the branch. A run writes
`.github/pull-request/title.md` and `.github/pull-request/body.md`, commits them and pushes, and
`.github/workflows/pull-request.yml` opens the pull request from a runner.

Those two files land on `main` when the pull request that carried them merges. They stay there
until the next one lands, so every branch inherits them at the moment it is cut. `AGENTS.md` tells
a run to push right after its first commit. The workflow runs on every pushed `claude/` branch,
finds the two files, and publishes.

So the first push of a run published the text of the run before it. The text gate passed, because
that text was written to pass it. The publisher read the pull request back and gated the stored
body, and that passed for the same reason. Nothing in the path could tell that the text belonged
to another issue.

That is pull request 30. The branch is `claude/issue-25` and it carries the title of issue 23 and
a body that says `Closes #23`. The run wrote its own title and body in a later commit, and that
push published nothing, because a branch that already has a pull request gets none. The work on
the branch is fine and the pull request describing it belongs to another run.

## Decision

The publisher reads one number twice. It reads `claude/issue-N` off the head branch it was given,
and it reads `Closes #M` off the first line of the body. It refuses when N and M differ, and it
refuses before it asks GitHub anything, so a refusal leaves no call behind.

It also refuses a body whose first line is not `Closes #N` at all. Reading nothing out of a body
and publishing it anyway is the shape of the failure this record is about.

The number is read off the first line and nowhere else. A body names other issues in its prose,
and a record it cites carries a number too. The line a body opens with is the one that says what
it closes, which is what `AGENTS.md` already asks for.

A head branch that names no issue is refused. The workflow fires on every `claude/` branch and
only `claude/issue-N` carries a number. A branch of another shape leaves the check nothing to
read, and a publish with nothing to check is the publish this record stops.

A test reads the workflow and fails when the publish step could run without the check. The check
lives in the publisher and it reads the issue off the head it is handed. A step that names a head
of its own, or reads one from anywhere but the branch that was pushed, would leave the publisher
comparing a body against a number nobody pushed.

## Consequences

The pull request opens on the push that carries this run's own body, which is the last push of a
run. The branch is still pushed right after the first commit, as record 0008 says and as
`AGENTS.md` says. What changed is that the pushes before that one publish nothing, and the reason
they publish nothing is written down rather than hoped for.

A run that writes a body and forgets `Closes #N` gets a red job and no pull request. That is
louder than a body with no closing line, which merges and leaves the issue open.

Six tests plant the new cases. A body that closes the issue the branch names, a body that closes
another one, a body that opens with something else, a body with nothing in it, a number further
down the body that is not read, and a head branch that names no issue. Four more read the
workflow, so that the publish step keeps handing the publisher the branch that was pushed.

## What this does not cover

A body on `main` whose issue is the issue of the branch being pushed would pass without having
been written for that run. The check reads a number, not an author and not a date, and two texts
about one issue look alike to it. Reaching that state needs the same issue picked again after its
own pull request merged, which is not a state a run reaches, because the issue is closed by then.

The check says the text names this issue. It does not say the text describes the work on the
branch. A body with the right first line and the wrong content underneath passes.

The workflow file comes from the branch that was pushed, as record 0008 already says. A branch
still says whether this job runs at all and what steps it has. Reading the two scripts from `main`
keeps the rules of the publish out of reach of the branch being published, and it is not a fence
against a branch written to defeat it.
