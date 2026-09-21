Closes #25

## What

A run of `scripts/gates.py` now says which rules it ran and which it could not, and the word `clean` never covers a rule that did not run.

With a list of private terms pointed at, all three rules run and the run says so, with the size of the list. A list of twelve terms reads like this.

    gates: ran the tests, the text rules, the term rules over a list of 12
    gates: clean

With no list, which is the ordinary state of a clone, the term rules do not run and the run says that too.

    gates: ran the tests, the text rules
    gates: did not run the term rules, because no list of private terms was pointed at, by --terms-file or FENCED_TERMS_FILE
    gates: clean apart from the term rules

`--text` gets the same treatment, because that route never runs the suite and used to print `clean` all the same.

The exit code does not move. A clone with no private list is not a failure, so a run without one still exits zero. This is a reporting rule and not a new refusal.

The hook stays quiet when every rule ran and nothing was found. It writes the same accounting when a rule was skipped, and it writes it above `gates: blocked` when it blocks.

`AGENTS.md` says the term rules run only where a list is, and that a change to how a term is matched is proved on the machine that holds one.

The decision is `docs/adr/0009-a-run-says-which-rules-it-could-not-run.md`.

## Why

The list of private terms is named by `FENCED_TERMS_FILE` and lives on one machine. `.gitignore` keeps it out of every clone, which is the point of it. So a run in a sandbox never has one, the term rules never run there, and the gate printed `gates: clean`.

`clean` is a word about every rule. Printed by a run where one rule never started, it says something that is not true, and it says it to the reader who has no other way to find out.

The branch on issue 19 changed how a term is matched, ran the gate before every commit as the procedure asks, and was told everything was fine. The new matching refused a file already on `main`. The gate was reporting a partial run in the words of a full one.

A gate that cannot run a rule should say so, the same way it refuses a commit whose address it cannot read rather than passing it for lack of evidence.

## Tests

`python -m pytest` is green at 248 tests. `python scripts/gates.py` reports clean apart from the term rules, which is the new line and the correct one for a clone with no list.

Four of those tests are new, in `tests/test_gates.py`.

A run with a list names the term rules and the size of the list, and its verdict is `gates: clean` on its own. A run without one lists the term rules as a rule it did not run, carries the reason, and its verdict names them. A run of the text rules alone counts the suite as a rule it did not run. Then the whole route twice, as a subprocess, one run with a list and one without, both exiting zero, reading the difference in what a passing run says.

The four earlier tests that plant a term still hold, and so do the rest.

## Decisions I made

- A missing list reports and does not fail. Refusing every commit in every clone that is not the one machine would make the gate unusable where it is most often run, and a gate people route around is worse than a gate that says less than they hoped.
- `--text` counts the suite as a rule it did not run. The issue names the term rules, and this is the same hole with a different rule in it. A route that prints `clean` while the suite never ran is the thing the issue is about.
- The accounting prints on a failing run too, above the findings, so a reader of a refusal sees what was and was not checked.
- The hook says nothing when every rule ran and nothing was found. A hook that speaks on every command is a hook a reader stops reading.
- The size of the list is said and the terms are not. The count is enough to tell a list that loaded from a list that is empty, and the terms belong to the machine.
- `clean apart from` keeps the word for the rules that did run. A separate word would read as a failure, and the exit code says it is not one.

## Run notes

> No dash used as punctuation and no semicolon, in Markdown or in a docstring. Short sentences. Describe what is there instead of selling it.

One commit on `claude/issue-25`, pushed right after it was made. The change is `scripts/gates.py`, four tests, `AGENTS.md`, record 0009 and its row in the index.

The gates were quick. `python -m pytest` takes about 0.6 seconds at 248 tests. `python scripts/gates.py`, which is the suite and the text rules over every tracked file, takes about 0.8 seconds. `python scripts/gates.py --text` takes about 0.14 seconds. The hook in `.claude/settings.json` ran the same gate before the commit and before the push. No gate failed.

This run is stopped and issue 25 carries the label `stuck`. The reason is not the work above, which is finished and pushed. The push that carries a first commit now also carries `.github/pull-request/title.md` and `.github/pull-request/body.md` as they stand on `main`, which is the text of the previous run. The workflow published them, so pull request 30 opened on this branch with the title of issue 23 and a body that says `Closes #23`.

That cannot be repaired from a run. `scripts/publish.py` publishes nothing when the branch already has a pull request, and a closed one counts the same way, so closing 30 does not let this branch get a correct one. Record 0006 says a body is published once and never edited, and the publisher has no route that changes a body that already exists. Editing it from here is the one thing record 0006 refuses, because the edit is what writes the version before it into the history of the body, and GitHub keeps that version for good.

So this file is the body pull request 30 should have carried, and it is here on the branch rather than on GitHub. A person decides what happens to 30.

One more thing this run found. The comment it wrote on issue 25 was read by the text gate first and passed. The stored comment carries a line under a rule, naming the agent and linking to its run, which the run did not write. So the append record 0008 describes is not only on the route a pull request body takes. It is on an issue comment from the same machine too. The comment was left as it stands, because record 0006 is about exactly this and an edit would write the version before it into the history of the comment.

The hole underneath is that the two files live on `main` and a branch inherits them, so the first push of every run publishes the previous run's text. It wants an issue of its own. What this run did not do is open that issue, change the workflow, or touch pull request 30 in any way.
