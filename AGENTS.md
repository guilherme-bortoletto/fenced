# AGENTS.md

This repository is personal and written to be read by a stranger. Everything in it is public facing.

## What never enters this repository

- Anything from paid work. No employer, no colleague, no client, no internal system, no internal number, no internal decision.
- Anything from a private project. Nothing about it, not even its shape.
- Any secret. No key, no token, no credential, in any file and in any commit. A key arrives through an environment variable and `.env` stays out of git.

When a term is borderline, it stays out.

## Code

- English everywhere. Names, comments, docstrings, commit messages, issues and pull requests.
- Standard library only at run time. `pytest` is the single development dependency.
- `domain/` and `ports/` stay pure. Only `adapters/` reach the outside world.
- Only `writes/` persists a record. A write is planned, shown as a diff, applied behind a flag, recorded in the journal, and can be undone.
- Only `adapters/llm_extractor.py` may name a model provider.
- A decision a reader would ask about goes to `docs/adr/` with a status, a date and a line in the index.

## Text

No dash used as punctuation and no semicolon, in Markdown or in a docstring. Short sentences. Describe what is there instead of selling it.

No attribution and no session link, in any file. Nobody writes that line. A tool appends it after the text was written, so the gate refuses it in a file it is given and in every tracked text file. A Markdown file is read as it stands, link and all. A Python file is read as its docstrings and its comments, which is what lets the pattern live in the code that refuses it and in the test that plants it. That decision is `docs/adr/0004-the-text-gate-reads-a-python-file-as-its-docstrings-and-its-comments.md`.

No sales slogan, in a name, a comment or a heading. Write what the code does. It answers when the person wrote, it separates who is likely to buy by a written rule, and it hands the decision back to a person.

## Before every commit

`python scripts/gates.py` runs the whole suite and the text rules. The hook in `.claude/settings.json` runs it again whenever a shell tool here reaches for `commit`, `push`, `merge`, `revert`, `cherry-pick`, `rebase` or `am`. On the machine that writes the code there is a `pre-commit` hook in the clone that runs it as well, which is where the private term list is checked too.

Every commit carries a GitHub noreply address. The gate refuses any other author or committer address, including one passed inline with `git -c user.email=`.

When a gate fails, fix the cause. Never work around a gate and never soften a fence to get a commit through. A fence that is actually wrong is an ADR and a pull request of its own. A fence that simply misses a case is a bug, and closing it is ordinary work with a test that plants the case.

Not every machine has a working `python3`. The gate hook tries it first and falls back to `python`.

The gate also refuses a private term when `FENCED_TERMS_FILE` points at a list of them. That list belongs to a machine and never to this repository.

## Pull requests

One issue, one branch named `claude/issue-N`, one pull request. Push right after the first commit, not at the end.

Title is the title of the issue. The body has these sections and no others:

- `Closes #N`
- What
- Why
- Tests
- Decisions I made
- Run notes

A small ambiguity is decided and listed under Decisions I made. A real blocker gets the `stuck` label, a comment on the issue, and the run stops there.

Write to GitHub through the REST api, because GraphQL may be refused. On a machine that has `gh`, that is `gh api repos/{owner}/{repo}/...`.

A pull request body is published by `python scripts/publish.py --owner O --repo R --head BRANCH --base main --title-file T --body-file B`, and by nothing else. A tool that publishes a body for an agent may append a line naming the agent and linking to its run. Reading the body back and editing that line out does not remove it, because the edit is what writes the version before it into the history of the body, and GitHub keeps that version for good. So the body is posted with a plain REST call that has nothing between the file and the wire. The publisher runs the text gate over the title and the body before the call, reads the pull request back, runs the gate again over the stored body, and refuses when the two disagree. It never edits what it published, and it has no route that changes a body that already exists. The decision is `docs/adr/0006-a-pull-request-body-is-published-once-and-never-edited.md`.

The body of an issue is public text that no commit hook sees. Run `python scripts/gates.py --text <file>` over it before it is published.

## Never

Never merge. Never push to `main`. Never force push. Never rebase a branch that is already pushed, merge instead. Never put attribution or a session link in a commit or a pull request. Never pass `--no-verify`, and never skip a hook by any other route.
