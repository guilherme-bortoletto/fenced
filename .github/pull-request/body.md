Closes #44

## What

A decision record and the check it describes.

`docs/adr/0022-a-pull-request-that-carries-another-account-turns-the-job-red.md` answers the
question in the issue. The publisher compares the author GitHub stored on the pull request with
the account the repository variable `PR_ACCOUNT` names. When they differ the pull request stays
open, the publisher says which account it carries and which one was expected, and it exits 1. When
`PR_ACCOUNT` is empty it compares nothing, says so, and exits 0. The record is in the index.

`scripts/publish.py` reads the author off the pull request it already reads. On the push that
opens it, that is the read back that checks the body. On a later push, that is the listing that
finds the pull request on the branch. It asks GitHub nothing new. It never edits the pull request.

`.github/workflows/pull-request.yml` hands `${{ vars.PR_ACCOUNT }}` to the publish step as
`PR_ACCOUNT`.

What the three cases in the issue do now. An absent secret with `PR_ACCOUNT` set opens the pull
request as the bot and turns the job red. An expired token stops red with no pull request, as
before. A token that belongs to somebody else opens the pull request and turns the job red.

## Why

The publisher fenced the body and only narrated the account. Two of the three cases were green,
and a green job is a job nobody opens. The issue asked what the publisher does when the account
is not the person, and asked that the expectation come from somewhere a clone can leave empty. A
repository variable is that place. A login is public, so it is not a secret.

## Tests

`tests/test_publish.py` gains thirteen tests. The author read off a stored pull request, off a
standing one, and off an answer with no author. Then the run itself, through `main` with a fake
transport. A pull request opened as the named account is green. The same login in another case is
green. One opened as the bot, one opened as somebody else and one with no author are red, and the
one opened as the bot was posted once and not touched again. A later push on a pull request that
carries the bot stays red and sends nothing. An empty `PR_ACCOUNT` is green and says it compared
nothing. The first push of a run, which opens nothing, compares nothing. Two tests read the
workflow back, one that finds the variable handed over and one that plants its removal.

`python -m pytest` passes with 641 tests, thirteen more than on `main`. `python scripts/gates.py`
reports clean apart from the term rules, which did not run because this machine has no list.

## Decisions I made

I took the first answer the issue offers. The pull request opens and the job turns red. The second
answer, falling back to the workflow token when the person's token is refused, turns the expired
token green with the bot as author. That is the absent secret again, which is the case the issue
wants seen.

The author compared is `user.login` on the pull request and not the login from `GET /user`. The
stored author is what a squash merge takes, and a workflow token has no account `GET /user` will
name.

The check runs on every push that finds a pull request, not only on the push that opened it. A
green job on a later push would sit next to a pull request that still carries the wrong account.

Logins are compared without case, because GitHub treats them that way.

The expected account is a repository variable and not the repository owner from the event. The
owner is never empty, so a fork with no secret would turn red on every push. The issue asks for a
place a clone can leave empty.

An expired token keeps the behavior record 0017 describes, red with no pull request. Nothing in
this change reaches it, and the record says so.

## Run notes

The text rule of AGENTS.md, in one line: "No dash used as punctuation and no semicolon, in
Markdown or in a docstring. Short sentences. Describe what is there instead of selling it."

What I did. The stall check came first. The most recent merge is pull request 48 from earlier
today, and no pull request on a `claude/` branch was open, so nothing was waiting. The brake
counted zero open night pull requests, and no open issue carried `stuck`. No pull request carried
`needs-work`. Issue 44 is the only open issue labelled `night`, so I took it and read its body,
and not its comments. It has no Answers section. The branch `claude/issue-44` did not exist on
origin, so I created it from `main`. I pushed after the first commit, which added record 0022, and
again after the second, which changed the publisher, the workflow and the tests.

The session that ran this was set up with a different branch name. AGENTS.md and the run
instructions both name `claude/issue-N`, and the publisher reads the issue number off that name,
so I worked on `claude/issue-44` and pushed nothing to the other branch.

`gh` was present but its token was refused, so every read of GitHub went through the REST tools
this session has. I wrote nothing to GitHub except the pushes.

The check does nothing until a person sets the repository variable `PR_ACCOUNT`, under Settings,
Secrets and variables, Actions, Variables. Until then every publish says it compared nothing. The
publisher that runs is `main`'s copy, so this pull request itself was published by the old one and
was not checked.

What I did not do. I wrote no comment anywhere and opened no issue. I did not set `PR_ACCOUNT`. I
did not change what happens to an expired token.

The interpreter `python` resolves to here is 3.11 and the package asks for 3.12. I ran the suite
from a Python 3.13 environment outside the tree. The commit hook calls `python3`, which is the
3.11 one, so I installed `pytest` for it as well. The suite passes under both. Nothing in the tree
changed for that.

How long the gates took. `python -m pytest` took about 2.0 seconds and `python scripts/gates.py`
about 2.5 seconds on each run, four runs of the gate in all, plus the hook on each commit and push.
