Closes #8

## What

The README tour is finished. It now runs to twenty seven steps, and the last seven cover the model record, the secrets record, `SECURITY.md`, `AGENTS.md`, the pull request workflow, the publisher and record 0008. A stray blank line inside the list is gone. The line that said the rest arrives later now says a new file gets its line with the pull request that adds it.

A new section, How the work happens, says in five lines how the backlog, the routine, the gates and the agent review fit together. It says plainly that an agent writes the code and another agent reviews and merges it.

The opening paragraph no longer says skeleton stage. It says what the command line does, and that scoring, matching and the reply are domain code the command line does not call yet.

The run section says the install is the one step that reaches the network, and shows `PYTHONPATH=src python -m fenced run` for a clone with nothing installed.

`SECURITY.md` asks a reporter to open an issue saying a problem exists without describing it, so the owner can take it to a private security advisory. It says what record 0021 and its tests prove about secrets, and that the examples are invented.

`tests/test_readme.py` walks the tour through the tree.

## Why

The issue asks for a README a reader finishes in fifteen minutes, with a tour whose files exist in reading order, commands that work on a fresh clone, a process section and a security policy.

## Tests

`python -m pytest` passes 670 tests. `python scripts/gates.py` is clean apart from the term rules, which had no list to read on this machine.

New tests in `tests/test_readme.py` plant these cases.

- The tour of this repository can be walked. Every step names a path that exists, the steps are numbered from one with no gap, and no path is visited twice.
- A tour that names a missing file, skips a number, visits a file twice or has no steps is refused.
- A numbered line after the tour section is not read as a step.

Every command in the run section was run in a fresh clone of the branch. `fenced run`, `fenced run --write`, `fenced undo 1` and `fenced undo 1 --write` each did what the README says. `fenced run --extractor model` with no key said so and exited with status 2. `PYTHONPATH=src python -m fenced run` worked with nothing installed.

## Decisions I made

- The Answers say a test already reads the tour back against the files. The test that existed reads back the counts in step 1 and the table of fences, and nothing checked that a tour path exists. I added that check.
- The tour check lives in a file of its own and not in `tests/test_fences.py`. That file counts every function asserted to return an empty list as a check, and the README counts the checks, so a tour check there would change the fence counts for something that is not a fence.
- The test checks that the tour can be walked and not that its order is right. Reading order is a choice a person makes.
- The tour grew by seven steps and not by every record. Records 0004 to 0013, 0017, 0022 and 0023 are about how the fences, the gates and the publisher check themselves. The ADR index lists them, and record 0008 stands in the tour as the way into the publishing part.
- `SECURITY.md` promises no channel, no response time and no claim about tests outside the examples. Only the example messages are said to be invented, because that is the part I could read in full.
- The process section counts its five lines as a numbered list, so the count can be checked by eye.

## Run notes

> No dash used as punctuation and no semicolon, in Markdown or in a docstring. Short sentences. Describe what is there instead of selling it.

Stall check found nothing. The last merge was pull request 50 today, and no `claude/` pull request was open. The brake counted zero and no issue carried `stuck`. No pull request carried `needs-work`. Issue 8 was the only open `night` issue and had no branch, so `claude/issue-8` was cut from `main`.

The default interpreter here is Python 3.11 and the package needs 3.12, so I made a 3.13 virtual environment for the fresh clone checks. The interpreter the gate hook uses had no pytest, so I installed pytest for it. The suite passes under both.

The first commit was blocked by the commit hook, because the global git identity on this machine is not a GitHub noreply address and the hook reads the identity before the command that set it. I set the identity in the clone in a step of its own and committed again. No hook was skipped.

The first two pushes left the pull request job green, because the branch still carried the body of issue 45.

I did not wire scoring, matching or the reply into the command line. The README says they are not wired yet.

I did not run the term rules, because no list was on this machine.

The gates took between 2.1 and 2.8 seconds a run, over five runs.
