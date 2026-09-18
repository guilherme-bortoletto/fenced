# 8. A pull request is opened from a workflow runner, because the path out of the sandbox appends

Status: accepted
Date: 2026-09-18

## Context

Record 0006 decided that a pull request body leaves this repository through one file,
`scripts/publish.py`, which posts it with `urllib.request`. The reasoning was that the line
naming the agent and linking to its run came from a publishing tool, and that a plain REST call
would have nothing in it to do the appending.

The run on issue 17 tested that instead of believing it. The publisher posted straight at the
GitHub api from the night sandbox, read the pull request back, and found the line on the stored
body. The gate had read the file and the file was clean. The line arrived after that.

So the append is not in a publishing program. It is in the path out of that machine, which every
call from inside it travels, and no program inside it can walk around. Record 0006 named the
right route and the wrong reason.

The other half of that record holds. Nothing may edit a body that exists, because the edit is
what writes the version before it into the history of the body, and GitHub keeps that version
for good.

`.claude/settings.json` in this repository already carries an empty attribution and no session
link, and it is cloned into every run. No commit in this history carries a trailer, so that half
is obeyed. Pull request bodies were not.

## Decision

The branch carries the text. A run writes the title to `.github/pull-request/title.md` and the
body to `.github/pull-request/body.md`, commits them and pushes. It does not call the publisher.

`.github/workflows/pull-request.yml` runs on a pushed `claude/` branch. It runs the text gate
over the two files, and the job fails rather than publishing text that breaks a rule. Then it
calls `scripts/publish.py` from the runner, which is on the other side of the path that appends.
The publisher reads the pull request back and runs the gate again over the stored body, as it
did before.

The publisher asks GitHub first whether the branch already has a pull request, and publishes
nothing when it has one. A branch is pushed many times in one run and the workflow runs on each
push. The push that carries the two files opens the pull request. Every push after it does
nothing, which is what writing a body once means when the trigger repeats.

Open and closed both count as already there. A closed pull request is a decision somebody made,
and a later push that opened a second one would take that decision back without saying so.

Two other shapes were rejected. Publishing from the sandbox through a proxy that does not append,
which is a setting on one machine, and a rule this repository keeps cannot live somewhere a
stranger reading the tree cannot see. Writing the body into the first commit message and reading
it from there, which puts the text in two places and still leaves the call where the append is.

## Consequences

The body is a tracked Markdown file, so the commit hook reads it with every other text file in
the tree. Before this it was text no hook ever saw.

The two files land on `main` when the pull request merges, and the next branch writes over them.
A reader of `main` sees the body of the last pull request that merged, which is a small untidiness
in exchange for text the gate already covers.

The pull request opens on the push that carries the body, which is the last push of a run and not
the first. The branch is still pushed right after the first commit, as it always was.

A pull request opened with the token a workflow runs with starts no workflow run of its own, so
the pull request event would never fire for one of these. `ci.yml` now also runs on a pushed
`claude/` branch, so a night branch carries its checks either way. A branch whose pull request a
person opens by hand queues both, which is the rarer case and cheap.

The repository setting that lets a workflow open a pull request has to be on. When it is off the
api answers 403, the job fails red, the branch stays pushed and no pull request exists, which is
a state a person can act on.

Record 0006 keeps its status. What it decided stands, which is one route out, a gate on both
sides of the call, and no edit ever. This record says which machine makes the call and why the
reason written in that one was wrong.

Four tests plant the new cases. A branch with a pull request already on it, a branch whose pull
request is closed, the listing the publisher asks for read back as a query, and an answer that is
not a listing at all.
