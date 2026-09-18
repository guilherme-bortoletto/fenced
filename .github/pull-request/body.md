Closes #23

## What

The branch carries the text of its own pull request, and a workflow publishes it from a runner.

A run writes the title to `.github/pull-request/title.md` and the body to `.github/pull-request/body.md`, commits them and pushes. `.github/workflows/pull-request.yml` runs on a pushed `claude/` branch, runs the text gate over the two files, and calls `scripts/publish.py` from the runner. The job fails rather than publishing text that breaks a rule, and it does nothing at all when the branch carries neither file.

`scripts/publish.py` now asks GitHub first whether the branch already has a pull request, and publishes nothing when it has one. Nothing else about it changed. It posts with `urllib.request`, reads the pull request back, runs the gate again over the stored body, and still has no route that changes a body that already exists.

`ci.yml` also runs on a pushed `claude/` branch now.

`AGENTS.md` says the branch carries the title and the body, and no longer tells a run to call the publisher itself.

The decision is `docs/adr/0008-a-pull-request-is-opened-from-a-workflow-runner.md`.

## Why

Record 0006 said the line naming the agent came from a publishing tool, and that a plain REST call would have nothing in it to append one. The run on issue 17 tested that. The publisher posted straight at the GitHub api from the night sandbox, read the pull request back, and found the line on the stored body.

So the append is not in a publishing program. It is in the path out of that machine, which every call from inside it travels, and no program inside it can walk around. The only way to post a body that nothing appends to is to post it from somewhere else. The runner is somewhere else, and the branch is how the text gets there.

That also puts the body under the commit gate. Before this it was the one piece of public text no hook ever saw.

## Tests

`python -m pytest` is green at 241 tests, and `python scripts/gates.py` is clean.

Four of those tests are new, and each one plants a case in `tests/test_publish.py`. A branch that already has a pull request gets nothing, and the fake transport records no call after the listing. A closed pull request on the branch counts the same way. The listing the publisher asks for is read back and checked, that it names this branch and that it asks for every state. An answer that is not a listing at all is not read as a pull request, and the branch still gets one.

The twenty two tests that were already there still hold, including the one that reads the source of the publisher and refuses the words that would start an edit.

The two paths through the workflow ran on this branch before this body was written. The push that carried no title and no body left the publish step skipped and the job green. This pull request is the other path.

## Decisions I made

- The two files have fixed names under `.github/pull-request/`, so the commit hook reads them as tracked Markdown with everything else. They land on `main` when this merges and the next branch writes over them. A folder that kept one body per issue would grow without end.
- A closed pull request on the branch counts as already there. A closed pull request is a decision somebody made, and a push that opened a second one would take that decision back without saying so.
- `ci.yml` runs on a pushed `claude/` branch now. A pull request opened with the token a workflow runs with starts no workflow run of its own, so this pull request would have carried no checks at all. A branch whose pull request a person opens by hand queues both runs, which is the rarer case and cheap.
- The publish job runs the text rules over the two files and not the whole suite, because `ci.yml` runs the suite on the same commit on both versions of Python.
- The pull request opens on the push that carries the body, which is the last push of a run. The branch is still pushed right after the first commit, as `AGENTS.md` asks.
- Record 0006 keeps its status of accepted. What it decided stands, which is one route out and no edit ever. Record 0008 says which machine makes the call and why the reason in the older record was wrong.

## Run notes

> No dash used as punctuation and no semicolon, in Markdown or in a docstring. Short sentences. Describe what is there instead of selling it.

Three commits on `claude/issue-23`. The publisher and its tests, then the workflow with the record and `AGENTS.md`, then these two files. The branch was pushed right after the first commit and after each one since.

The gates were quick. `python -m pytest` takes about 0.3 seconds and `python scripts/gates.py`, which is the suite and the text rules over every tracked file, takes about 0.5 seconds. The hook in `.claude/settings.json` ran the same gate before every commit and every push in this run. No gate failed.

The sandbox this run works in has no `gh`, so the reads of issues and of workflow runs went through the REST api. Nothing was written to GitHub from here except the pushes.

What this run did not do. It did not turn on the repository setting that lets a workflow open a pull request, because that is a setting and not code. This pull request existing is the proof that the setting is on. It did not touch `README.md`, and it did not read the comments on issue 23.
