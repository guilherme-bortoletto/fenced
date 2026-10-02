# 17. A pull request is published with a token that belongs to a person

Status: accepted
Date: 2026-09-29

## Context

Record 0008 moved the publishing call to a workflow runner, because the path out of the machine
a night run works in appends a line naming the agent and linking to its run. The call is made
from the other side of that path now, and the body reaches GitHub as it was written.

What that record did not decide is whose token makes the call. The publish step read
`secrets.GITHUB_TOKEN`, which is the token the workflow itself runs with, so GitHub recorded
`github-actions[bot]` as the author of every pull request. A squash merge takes the author of
the pull request, so seven of the nineteen commits on `main` carry the bot rather than the
person who owns the repository.

The branch was already right. A night run commits under the noreply address the gate requires,
and the gate refuses any other author or committer address. Only the publishing call was wrong,
and it was wrong because a workflow token has no person behind it. There is no way to give one
one.

## Decision

The publish step reads its token from a repository secret named `PR_TOKEN` and falls back to
the token the workflow runs with.

    GITHUB_TOKEN: ${{ secrets.PR_TOKEN || secrets.GITHUB_TOKEN }}

`PR_TOKEN` is a fine grained personal access token. It is scoped to this repository and to
nothing else. On this repository it holds pull requests, which it reads and writes, and file
contents, which it only reads. What it can do is open a pull request and read one back, which
is the whole of what the publisher does.

The read of contents is there because the create needs it. `POST /repos/{owner}/{repo}/pulls`
answered `422 Validation Failed, not all refs are readable` until `Contents: Read` was added,
because GitHub resolves the head ref and the base ref before it opens a pull request. Listing
pull requests never needed that permission. The first failure was a 404 on the listing, and
the second was a 422 on the create.

So the fence is not that the token cannot read the tree. It reads the tree and it writes none
of it, and on a public repository a read grants it nothing a stranger without a token already
lacks. The fence is that it cannot write contents, so it cannot reach `main`, it cannot reach a
branch, and it cannot reach a workflow file. It cannot reach any other repository. And it holds
nothing on this one beyond pull requests.

What the fallback covers is a secret that is absent. The expression reads the second operand
when the first is the empty string, which is what a secret nobody set is. A repository that has
no `PR_TOKEN` still opens a pull request, with the bot as its author rather than no pull request
at all.

What the fallback does not cover is an expiry. A fine grained token expires, and an expired
token is a secret that is present. The expression hands that token over, GitHub refuses it, and
the publish stops with no pull request. Covering that day means the publisher trying the
person's token, reading the refusal, and falling back to the workflow token itself. This change
does not do that. It is a decision of its own and it gets an issue of its own.

What the fallback must not do is hide that it happened. So `scripts/publish.py` asks GitHub
`GET /user` once the token is in hand, and prints the login it gets back next to what it
published. It prints it on the path that publishes nothing as well, which is the branch that
already has a pull request. A workflow token belongs to nobody and GitHub answers that read
with a refusal, and the refusal is what gets printed, because the reason a login could not be
had is the answer here and not an error.

That read never refuses the publish. A line that only names an account must not be the thing
that stops a body from reaching GitHub.

Why a pushed branch cannot reach the token. The job holds `pull-requests: write` and
`contents: read`, and it runs `main`'s copy of the gate and `main`'s copy of the publisher over
the two text files the branch carries. The branch supplies text and nothing else. A branch that
rewrote the publisher to post the token somewhere would be rewriting a file the job does not
read, and a test reads the workflow back to keep both calls pointed at the checkout of `main`.
What a push does still decide is whether this job runs at all, which record 0008 already says,
and that is not a fence this record adds to.

## Consequences

A pull request now starts a workflow run of its own, because a pull request opened with a token
that belongs to a person is a pull request a person opened as far as GitHub is concerned. A
night branch queues a push run and a pull request run once its pull request exists. Both
triggers in `ci.yml` stay, because the first push of a run has no pull request yet and the
checks on it are worth having. The comment in that file said the pull request run was the rarer
case. It is now every case, and the comment says so.

A pull request opened with a person's token is that person's pull request in places this
change did not set out to touch. The owner can no longer request changes on one or approve
one. `POST /pulls/{number}/reviews` with `REQUEST_CHANGES` answers `422, Review Can not
request changes on your own pull request`. Every review before this one went to a pull
request the bot had opened, which is why the route worked until now.

The night loop survives that. Step 3 of a run asks for a review by the owner and not for a
state, and a review posted as a comment is a review in `GET /pulls/{number}/reviews`. The
`needs-work` label is not a review and nothing here touches it. Branch protection on this
repository asks for no approvals, so nothing there breaks either.

The seven commits already on `main` stay as they are. Changing them means rewriting a published
history on a branch that refuses a force push, and a rewritten public history is a worse thing
to explain to a reader than a bot author on seven old commits.

The secret is a setting on this repository and not a file in it, the same way the private list
of terms is a file on one machine. A reader of the tree sees the name `PR_TOKEN`, what it is
scoped to, and what happens when it is absent, which is the fallback. That is as much as a
public repository can carry about a token.

When the token is present but wrong, the api answers 403 and the job fails red with no pull
request, which is the state record 0008 already describes for a repository setting that is off.
A person can act on it.

Nine tests plant the new cases. The account read and carried back on the path that published,
the same read on the path that published nothing, a body written for another run that asks
GitHub nothing at all and so names no account, a read GitHub refuses that publishes all the
same, and two answers that carried no login to read. Then the line the run prints, once for a
body that published, once for a run that published nothing, and once for the first push of a
run, which names no account because it read none.
