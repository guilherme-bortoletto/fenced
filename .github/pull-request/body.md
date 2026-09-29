Closes #41

## What

The publish step of `.github/workflows/pull-request.yml` reads its token from a repository
secret and falls back to the token the workflow itself runs with.

```
GITHUB_TOKEN: ${{ secrets.PR_TOKEN || secrets.GITHUB_TOKEN }}
```

`scripts/publish.py` says which account it authenticated as. It asks GitHub `GET /user` once
the token is in hand and carries the login back with everything else it answers, and the line
a run prints names it. That happens on the path that published and on the path that published
nothing.

`.github/workflows/ci.yml` carried a comment saying that a pull request run was the rarer case.
It says what is true after this change, which is that a pull request a person's token opens
starts a run of its own, so a night branch queues a push run and a pull request run once its
pull request exists. Both triggers stay, because the first push of a run has no pull request
yet and the checks on it are worth having.

`docs/adr/0017-a-pull-request-is-published-as-a-person.md` says what the secret is scoped to,
that it can neither read nor write file contents, that it expires and what the fallback does on
that day, and why a pushed branch cannot reach it.

## Why

A squash merge takes the author of the pull request. The runner opened every pull request with
the token the workflow runs with, so GitHub recorded `github-actions[bot]`, and seven of the
nineteen commits on `main` carry the bot rather than the person who owns the repository.

The branch was already right. A night run commits under the noreply address the gate requires
and the gate refuses any other author or committer address. Only the publishing call was wrong,
and it was wrong because a workflow token has no person behind it.

The fallback is not politeness. A fine grained token expires, and on the day it does the
fallback keeps the loop running instead of stopping it. What the fallback must not do is hide
that it happened, which is what the account the run prints is for. A run that drops back to the
bot without saying so is the failure this change exists to stop from happening twice.

## Tests

Nine tests in `tests/test_publish.py`, and the transport is the fake that was already there, so
nothing in the file reaches GitHub.

- The account is read from GitHub and carried back on the path that published.
- The same read on the path that published nothing, which is a branch that already has a pull
  request.
- A body written for another run asks GitHub nothing at all, so it names no account.
- A read GitHub refuses still publishes, and the refusal is what the account says.
- An answer with no login, and an answer that is not a mapping at all, are neither of them read
  as an account.
- The line a run prints names the account for a body that published and for a run that
  published nothing, and names none for the first push of a run.

Three tests that were already there read the account field back, because the answer they assert
on word for word now carries it, and one of them reads the listing by its url rather than by
being the first call made.

`python -m pytest` is 533 passed. `python scripts/gates.py` is clean apart from the term rules.

## Decisions I made

The account is read once the token is in hand, after the text gate and before the listing of
pull requests on the branch. So the push that finds a body written for another issue names no
account, because it returns before the token is read and asks GitHub nothing. Putting a read
there would add a call to the one path whose point is that nothing reaches the wire, and a test
plants that it stays that way.

A read GitHub refuses is an answer and not an error. `GET /user` with a workflow token is a 403,
and that is precisely the case the printed line exists to name, so the refusal is what gets
printed and the publish carries on. Refusing there would stop the fallback on the one day the
fallback exists for.

No new fence reads the token line of the workflow back. The issue says `scripts/publish.py` is
the file with behaviour to test, and the tests that hold the workflow pointed at `main`'s copy
of the gate and of the publisher are already there. A fence that reads which secret the publish
step names is a change of its own.

## Run notes

The text rule of AGENTS.md, in one line: "No dash used as punctuation and no semicolon, in
Markdown or in a docstring. Short sentences. Describe what is there instead of selling it."

What I did. The stall check first, and nothing was waiting. The most recent merge was earlier
today and no pull request was open, so there was nothing for the brake to count and no issue
carried `stuck`. Issue 41 was the only open issue labelled `night`. Two commits on
`claude/issue-41`, pushed right after the first one, then the title and the body.

What I did not do. The seven commits already on `main` stay as they are, which the issue asks
for. No fence on the workflow, for the reason above. And nothing anywhere holds the token or
names a value for it.

One thing a person has to do. The secret `PR_TOKEN` is a setting on this repository and this
branch cannot create it. Until it exists the fallback runs, so this pull request is opened by
the bot and the line the job prints says which account it could not name. The change takes
effect on the first push after the secret is added.

The clone this ran in had a local `main` four commits behind `origin/main`, so the branch was
first cut from the older one. It was moved onto the fetched `main` before the first commit, and
nothing was pushed before that. None of the four commits had touched the publisher, its tests
or either workflow.

`python3` on this machine is 3.11 and carried no pytest, so the gate could not run the tests at
first. Installing pytest for it is a machine and not this repository, and the gate was never
passed over. The whole run of `python scripts/gates.py` takes 1.4 seconds, tests included. The
term rules did not run, because no list of private terms was pointed at, and the run says so
rather than calling itself clean.
