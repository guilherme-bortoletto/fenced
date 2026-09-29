Closes #41

## What

The publish step of `.github/workflows/pull-request.yml` reads its token from a repository
secret and falls back to the token the workflow itself runs with.

```
GITHUB_TOKEN: ${{ secrets.PR_TOKEN || secrets.GITHUB_TOKEN }}
```

A step before it says which of the two the publish will read. It reads a boolean and never the
secret, because a token that is absent and a token that is present and cannot do the work both
end in an account GitHub will not name, and a person reading a red job needs those two apart.

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
which is this repository, pull requests it reads and writes, and file contents it only reads.
It says what the fallback covers, which is a secret that is absent and not a token that expired.
And it says why a pushed branch cannot reach the token.

## Why

A squash merge takes the author of the pull request. The runner opened every pull request with
the token the workflow runs with, so GitHub recorded `github-actions[bot]`, and seven of the
nineteen commits on `main` carry the bot rather than the person who owns the repository.

The branch was already right. A night run commits under the noreply address the gate requires
and the gate refuses any other author or committer address. Only the publishing call was wrong,
and it was wrong because a workflow token has no person behind it.

The token reads file contents, and the record says so. The create answered `422 Validation
Failed, not all refs are readable` until `Contents: Read` was added, because GitHub resolves the
head ref and the base ref before it opens a pull request. Listing pull requests never needed
that permission. So the fence is not that the token cannot read the tree. It reads the tree and
it writes none of it, and on a public repository a read grants it nothing a stranger without a
token already lacks. The fence is that it cannot write contents, it cannot reach any other
repository, and it holds nothing on this one beyond pull requests.

The fallback covers a secret that is absent. The expression reads the second operand when the
first is the empty string, which is what a secret nobody set is. It does not cover an expiry. An
expired token is a secret that is present, so the expression hands that token over, GitHub
refuses it, and the publish stops with no pull request. Covering that day means the publisher
trying the person's token, reading the refusal, and falling back to the workflow token itself.
That is a decision of its own and it is not in this change.

What the fallback must not do is hide that it happened, which is what the account the run prints
is for. A run that drops back to the bot without saying so is the failure this change exists to
stop from happening twice.

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
- The line a run prints names the account for a body that published and for a run that published
  nothing, and names none for the first push of a run.

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
printed and the publish carries on. A line that only names an account must not be the thing that
stops a body from reaching GitHub.

No new fence reads the token line of the workflow back. The issue says `scripts/publish.py` is
the file with behaviour to test, and the tests that hold the workflow pointed at `main`'s copy
of the gate and of the publisher are already there. A fence that reads which secret the publish
step names is a change of its own.

The expiry sentence the answers on the issue correct sits in three more places on this branch,
and I left all three as they stand, because the answers say the code, the tests and the two
workflow files stay as they are. They are the comment above the publish step of
`.github/workflows/pull-request.yml`, the last sentence of the comment at the top of
`.github/workflows/ci.yml`, and the docstring of `account` in `scripts/publish.py`. All three
say the fallback keeps the loop running on the day the person's token expires, and the record
next to them now says it does not. A comment can be corrected in an ordinary commit and a
published body cannot be corrected at all, which is why the record and this body are the two
that had to be right on this push. Correcting the three wants an issue of its own, because the
text it would follow is the record this pull request carries.

## Run notes

The text rule of AGENTS.md, in one line: "No dash used as punctuation and no semicolon, in
Markdown or in a docstring. Short sentences. Describe what is there instead of selling it."

What I did. The stall check first, and nothing was waiting. The most recent merge is pull request
40 from earlier today and no pull request was open, so the brake counted none and no issue
carried `stuck`. Issue 41 was the only open issue labelled `night`, and its body now has an
`Answers` section, so this is a second night on a branch that was already pushed. I checked
`claude/issue-41` out and continued from it.

The branch carried five commits and no pull request, because the run before this one took the
title and the body off it, and a branch that carries neither publishes nothing and leaves the
job green. Tonight is one commit on the record, pushed on its own, and then the title and the
body, which is the push that opens this pull request.

What the answers asked for. Two statements were false. The record said the token can neither
read nor write file contents, and it reads them. The record said the fallback keeps the loop
running on the day the token expires, and what it covers is an absent secret. Both passages are
rewritten, one more sentence in the record that rested on the second one is rewritten with them,
and neither claim is in this body.

What I did not do. The seven commits already on `main` stay as they are, which the issue asks
for. No code, no test and neither workflow file changed tonight, which the answers ask for, and
the three comments that still carry the old sentence are named above. Nothing anywhere holds the
token or names a value for it.

The secret. The answers say `PR_TOKEN` exists and that `Contents: Read` was added to it after a
422 on the create, so this is the first push of a run on which the publish can authenticate as a
person. The line the job prints names the account, and that line is where a reader sees which of
the two tokens was read.

The gates. `python -m pytest` is 533 passed in 1.0 seconds. The whole run of
`python scripts/gates.py` takes 1.3 seconds, tests included. The term rules did not run, because
no list of private terms was pointed at, and the run says so rather than calling itself clean.
The interpreter in this clone carried no pytest, so pytest was installed into the machine before
the first commit. That is a machine and not this repository, and no gate was passed over.
