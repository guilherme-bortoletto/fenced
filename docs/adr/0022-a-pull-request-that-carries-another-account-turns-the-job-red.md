# 22. A pull request that carries another account is opened and then turns the job red

Status: accepted
Date: 2026-10-14

## Context

Record 0017 made the publish read its token from the secret `PR_TOKEN` and fall back to the
workflow token. It made `scripts/publish.py` ask GitHub which account the token belongs to and
print the login. The publisher fences the body. It reads the pull request back and refuses when
the stored body disagrees with what it sent. The account it only narrates.

A squash merge takes the author of the pull request. So the account that opens one is the account
a commit on `main` carries. Three cases end with that account not being the person.

- The secret is absent. The expression falls back to the workflow token, the publish is green, and
  the author is the bot. Nothing turns red.
- The token expired. The expression hands it over, GitHub refuses it, and the publish stops red
  with no pull request. The work waits until a person renews the token.
- The token belongs to somebody else. The publish is green and the pull request carries that
  somebody.

The first and the third are green. A green job is a job nobody opens, so the line that names the
account is a line nobody reads.

## Decision

The publisher compares the author GitHub stored on the pull request with the account a person
said to expect. When they differ it says so and exits nonzero, after the pull request is open.

The account to expect comes from the environment variable `PR_ACCOUNT`. The workflow fills it from
the repository variable of the same name, `${{ vars.PR_ACCOUNT }}`. A variable is a setting and
not a secret, because a login is public. A clone that never set it reads the empty string.

The author is read off the pull request as GitHub stored it, the `user.login` of the answer, and
not off `GET /user`. That read can be refused, and a workflow token has no account to name. The
stored author is what a squash merge takes, so it is the thing worth checking. On a push that
opens the pull request it comes from the read back that already checks the body. On a later push
it comes from the listing that already finds the pull request on the branch. Neither path asks
GitHub anything new.

What each case does now.

- The secret is absent and `PR_ACCOUNT` is set. The pull request opens as the bot, the job turns
  red, and the line says the pull request carries `github-actions[bot]` and not the account the
  variable names.
- The token expired. Nothing changes. The publish stops red with no pull request, as record 0017
  says.
- The token belongs to somebody else. The pull request opens, the job turns red, and the line names
  both accounts.
- `PR_ACCOUNT` is empty. The publisher prints the author and says that nothing was compared,
  because no account was named to compare against. The job stays green. That is a clone, and a
  clone with no secret still has to publish.

The pull request opens before the job turns red. The work reaches review and the red job is what a
person sees. Refusing to open it would leave the work waiting on a person, the same as an expired
token, for a case where the work itself is fine.

The check runs on every push that finds a pull request, and not only on the push that opened it.
A later push that turned green would put a green job next to a pull request that still carries the
wrong account, and the red one would scroll out of sight.

The other answer was to try the person's token, fall back to the workflow token when GitHub
refuses it, and say which one was used. That turns the expired token green, with the bot as the
author. It is the case of the absent secret again, which is the one this record sets out to make
visible. A refused token means a person has to act, and a red job is how one learns that.

## Consequences

A pull request that carries the wrong account keeps a red publish job on every push until a
person acts. Acting means fixing the secret, or closing the pull request and pushing again, or
clearing `PR_ACCOUNT` to say the account is not checked on this repository. The publisher never
edits or reopens a pull request to fix the author, as record 0006 says.

The variable has to be set for the check to run. Until a person sets `PR_ACCOUNT` on this
repository, the publisher says on every run that it compared nothing. That line is the reminder.

The publisher on a branch is not the publisher that runs. The workflow runs `main`'s copy, so the
check starts on the first push after this change merges. The workflow file is the branch's own,
so the variable reaches `main`'s publisher from then on.

The tests plant the cases. A pull request opened as the account the variable names, one opened as
the bot, one opened as somebody else, one whose answer carries no author, a branch that already
has a pull request under another account, and an empty variable. Then the exit code and the line
for each, and a test that reads the workflow back and finds the variable handed to the publish.
