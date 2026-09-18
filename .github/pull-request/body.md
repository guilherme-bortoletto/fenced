Closes #23

## What

The branch carries the text of its own pull request, and a workflow publishes it from a runner.

A run writes the title to `.github/pull-request/title.md` and the body to `.github/pull-request/body.md`, commits them and pushes. `.github/workflows/pull-request.yml` runs on a pushed `claude/` branch, runs the text gate over the two files, and calls the publisher from the runner. The job fails rather than publishing text that breaks a rule, and it does nothing at all when the branch carries neither file.

The text is the branch's and the rules are `main`'s. The job checks the pushed branch out, checks `main` out into `rules-from-main`, and runs `main`'s text gate and `main`'s publisher over the two files the branch carries. A branch says what its pull request says. It does not say what the gate refuses or what the publisher is allowed to do, and the job that runs them holds write on pull requests.

`scripts/publish.py` now asks GitHub first whether the branch already has a pull request, and publishes nothing when it has one. Nothing else about it changed. It posts with `urllib.request`, reads the pull request back, runs the gate again over the stored body, and still has no route that changes a body that already exists.

`ci.yml` also runs on a pushed `claude/` branch now.

`AGENTS.md` says the branch carries the title and the body, and no longer tells a run to call the publisher itself.

The decision is `docs/adr/0008-a-pull-request-is-opened-from-a-workflow-runner.md`.

## Why

Record 0006 said the line naming the agent came from a publishing tool, and that a plain REST call would have nothing in it to append one. The run on issue 17 tested that. The publisher posted straight at the GitHub api from the night sandbox, read the pull request back, and found the line on the stored body.

So the append is not in a publishing program. It is in the path out of that machine, which every call from inside it travels, and no program inside it can walk around. The only way to post a body that nothing appends to is to post it from somewhere else. The runner is somewhere else, and the branch is how the text gets there.

That also puts the body under the commit gate. Before this it was the one piece of public text no hook ever saw.

## Tests

`python -m pytest` is green at 244 tests, and `python scripts/gates.py` is clean.

Seven of those tests are new, and each one plants a case in `tests/test_publish.py`. A branch that already has a pull request gets nothing, and the fake transport records no call after the listing. A closed pull request on the branch counts the same way. The listing the publisher asks for is read back and checked, that it names this branch and that it asks for every state. An answer that is not a listing at all is not read as a pull request, and the branch still gets one. Then the workflow itself, read as text. That it runs the gate and the publisher from the checkout of `main`, that a copy run from the branch is refused, and that a workflow which never checks `main` out is refused.

The twenty two tests that were already there still hold, including the one that reads the source of the publisher and refuses the words that would start an edit.

The two paths through the workflow ran on this branch before this body was written. The push that carried no title and no body left the publish step skipped and the job green. The push that carried both reached the publish step and answered 403, because the repository setting that lets a workflow open a pull request was off. This body existing on GitHub is the proof that it is on.

## Decisions I made

- The two files have fixed names under `.github/pull-request/`, so the commit hook reads them as tracked Markdown with everything else. They land on `main` when this merges and the next branch writes over them. A folder that kept one body per issue would grow without end.
- A closed pull request on the branch counts as already there. A closed pull request is a decision somebody made, and a push that opened a second one would take that decision back without saying so.
- `ci.yml` runs on a pushed `claude/` branch now. A pull request opened with the token a workflow runs with starts no workflow run of its own, so this pull request would have carried no checks at all. A branch whose pull request a person opens by hand queues both runs, which is the rarer case and cheap.
- The publish job runs the text rules over the two files and not the whole suite, because `ci.yml` runs the suite on the same commit on both versions of Python.
- The pull request opens on the push that carries the body, which is the last push of a run. The branch is still pushed right after the first commit, as `AGENTS.md` asks.
- `main` is checked out into `rules-from-main` inside the workspace, and the branch is checked out first, because a checkout at the root of the workspace cleans what is already in it.
- The record says what this does not cover. A push event runs the workflow file from the branch that was pushed, so the branch still says whether the job runs at all and what steps it has. Reading the two scripts from `main` keeps the rules of this publish out of the reach of the branch being published, and it is not a fence against a branch written to defeat it.
- `AGENTS.md` says the rules come from `main` too, because the sentence that tells a run what the workflow does had the same gap the record had.
- This body was rewritten before the push that carries it, because the push is what opens the pull request and a body is never edited after that.
- Record 0006 keeps its status of accepted. What it decided stands, which is one route out and no edit ever. Record 0008 says which machine makes the call and why the reason in the older record was wrong.

## Run notes

> No dash used as punctuation and no semicolon, in Markdown or in a docstring. Short sentences. Describe what is there instead of selling it.

Two nights on `claude/issue-23`. The first wrote the publisher, the workflow, the record and these two files, in three commits pushed as they were made. Tonight is one commit on top of them. The workflow takes its rules from `main`, the record says which copy makes the call, and `AGENTS.md` says the same.

The gates were quick. `python -m pytest` takes about 0.5 seconds at 244 tests, and `python scripts/gates.py`, which is the suite and the text rules over every tracked file, takes about 0.8 seconds. The hook in `.claude/settings.json` ran the same gate before the commit and before the push. No gate failed.

Two things about the machine this run works in. `pytest` was not installed in it, so it was installed before the first gate ran. The clone arrived configured with an address the gate refuses, so it was set to the address every commit on `main` already carries, and the gate read the new one. There is no `gh` here either, so the reads of issues and of workflow runs went through the REST api. Nothing was written to GitHub from here except the push.

What this run did not do. It did not turn on the repository setting that lets a workflow open a pull request, because that is a setting and not code. It did not touch the parts of the branch the issue said were right, which are the declared permissions, the token, the branch name reaching the shell through the environment, the pinned actions, the concurrency group, the skip on a deletion, and publishing nothing when a pull request already exists. It did not read the comments on issue 23.
