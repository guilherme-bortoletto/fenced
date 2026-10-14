Closes #45

## What

The publisher opens a pull request only from the push that changed `.github/pull-request/body.md`.

`scripts/publish.py` reads the two commits a push moved the branch between, from `PUSH_BEFORE` and `PUSH_AFTER`. It asks GitHub for `compare/{before}...{after}` and looks for the body file among the files listed. When the file is not there it publishes nothing, prints that this push did not change the body, and exits zero. A push that creates a branch names forty zeros as the commit before it, and that push is compared against the base branch. A commit of any other shape, or a missing one, is refused and the job turns red.

`.github/workflows/pull-request.yml` hands `github.event.before` and `github.event.after` to the publish step in those two variables.

Record 0023 says why, an index row points at it, and `AGENTS.md` has one sentence on it.

## Why

Record 0011 stops a body that closes another issue. A run that continues a branch finds a body that closes the right issue and that the run has not touched yet. Its first push published that body. That is what nearly happened on `claude/issue-41` on 29/09. The text cannot tell the two pushes apart. The push can.

The ordinary path stays as it was. The push that carries the body of a run is the push that changed the file, so it opens the pull request.

## Tests

`python -m pytest` passes 663 tests. `python scripts/gates.py` is clean apart from the term rules, which had no list to read on this machine.

New tests in `tests/test_publish.py` plant these cases.

- A push that left the body alone publishes nothing and says why. That is the branch of issue 41.
- A push that changed the body publishes it.
- A push with no files listed, and a file whose path only ends like the body file, publish nothing.
- The comparison runs from the commit before the push to the one after it.
- A push that creates the branch is compared against `main`.
- A branch that already has a pull request, and a body written for another issue, ask for no comparison.
- Five commits of the wrong shape are refused before anything is sent.
- A comparison that comes back without a list of files is refused.
- End to end through `main`, the first push of a continuing run exits zero, and a run with no commits in the environment exits one.
- The workflow hands over both commits from the push event and the body file the publisher looks for, and three planted workflows that drop one of them are refused.

## Decisions I made

- The commits reach the publisher through the environment and not as arguments. The workflow file comes from the branch and the publisher from `main`. The copy of `main` that runs on this branch does not know `--before`, and an unknown argument would have turned the job red and opened no pull request for this branch. An unknown variable is read past. `--before` and `--after` still exist and default to the two variables.
- The check is a comparison of the push and not a comparison of the body text with the text at the commit before. The comparison needs no new error handling for a file that is absent, and it reads what the push did.
- The comparison runs after the check for a standing pull request, so a branch that already has one gets the answer it got before and makes no extra call.
- A missing or malformed commit is refused rather than read as a push that changed nothing. A broken workflow should be a red job and not a quiet one.
- The body file path is a constant in the publisher, and a test reads the workflow to keep `--body-file` equal to it.
- A push that rewrites the body byte for byte publishes nothing. A failed publish is recovered by re-running the job on the push that wrote the body. Both are written down in record 0023.

## Run notes

> No dash used as punctuation and no semicolon, in Markdown or in a docstring. Short sentences. Describe what is there instead of selling it.

Stall check found nothing. The last merge was pull request 49 today, and no `claude/` pull request was open. The brake counted zero and no issue carried `stuck`. No pull request carried `needs-work`. Issue 45 was the only open `night` issue and had no branch, so `claude/issue-45` was cut from `main`.

pytest was not installed for the interpreter the gate uses, so the first gate run reported that the tests did not run. I installed pytest and ran it again.

The first commit was blocked by the commit hook, because the global git identity on this machine is not a GitHub noreply address and the hook reads the identity before the command that set it. I set the identity in the clone in a step of its own and committed again. No hook was skipped.

The first two pushes left the pull request job green, because the branch still carried the body of issue 44.

I did not prove the comparison against GitHub itself. It was proved against a fake transport. This push is the first one that reaches it, through the copy of the publisher on `main`, which does not have it yet. The first real comparison happens on the first push after this merges.

I did not run the term rules, because no list was on this machine.

The gates took between 2.4 and 2.9 seconds a run, over seven runs.
