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

No sales slogan, in a name, a comment or a heading. Write what the code does. It answers when the person wrote, it separates who is likely to buy by a written rule, and it hands the decision back to a person.

## Before every commit

`python scripts/gates.py` runs the fences and the text rules, and a hook runs it again on its own. When a gate fails, fix the cause. Never work around a gate and never soften a fence to get a commit through. A fence that is actually wrong is an ADR and a pull request of its own.

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

Write to GitHub through `gh api repos/{owner}/{repo}/...`, because GraphQL may be refused.

## Never

Never merge. Never push to `main`. Never force push. Never rebase a branch that is already pushed, merge instead. Never put attribution or a session link in a commit or a pull request. Never pass `--no-verify`, and never skip a hook by any other route.
