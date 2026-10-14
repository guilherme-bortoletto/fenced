# 23. A pull request body is published by the push that changed it, and by no other

Status: accepted
Date: 2026-10-14

## Context

Record 0011 made the first push of a run publish nothing. A fresh branch inherits the two text
files from `main`, those files carry the body of the run before it, and the publisher finds that
body closing another issue than the one the branch names.

That holds for a fresh branch. It does not hold for a run that continues a branch, which the night
run allows when `claude/issue-N` already exists on origin. A branch that already wrote its own
title and body carries a body that closes the issue its branch names. The first push of the
continuing run finds the two numbers equal and publishes that body, before the run has changed a
word of it.

It happened on 29/09 on `claude/issue-41`. The first publish failed on the token. The branch kept
a body stating two things that were no longer true, and the next push to it would have published
that body, which record 0006 says cannot be edited afterwards. The two text files were taken off the
branch by hand before the next run started, which is commit `9a14de9` in pull request 42.

What tells the two pushes apart is not the text. A body naming its own issue looks the same on
the push that wrote it and on every push after it. What differs is the push itself.

## Decision

The publisher asks GitHub which files the push changed, and it opens a pull request only when the
body file is one of them.

A push event names two commits, the one the branch was at before the push and the one after it.
The workflow hands both to the publisher in `PUSH_BEFORE` and `PUSH_AFTER`. The publisher reads
`GET /repos/{owner}/{repo}/compare/{before}...{after}` and looks for `.github/pull-request/body.md`
among the files it lists. When the file is there the push wrote the body and the publish goes on
as before. When it is not there the publisher publishes nothing, prints that this push did not
change the body, and exits zero.

A push that creates a branch names forty zeros as the commit before it. That push is compared
against the base branch instead, so a branch whose first push already carries its body still
publishes on that push.

The comparison runs after the check for a pull request the branch already has. A branch with one
gets the answer it got before and asks nothing more. It runs after the issue numbers too, so the
first push of a fresh run still asks GitHub nothing.

Both commits are checked for their shape before they go into a URL. A value that is not a commit
is refused and the job turns red. A missing one is refused in the same way, because reading a push
nobody named as a push that changed nothing would hide a broken workflow behind a green job.

The two commits travel in the environment and not as arguments. The workflow file comes from the
branch and the publisher comes from `main`, as record 0008 says. A branch that hands a new argument
to a copy of `main` that does not know it gets a red job and no pull request. A variable it does
not know is read past, so the branch that brings this change still opens its own pull request.

## Consequences

The ordinary path is the one it was. The push that carries the body of a run is the push that
changed the body file, so it opens the pull request. Every push before it publishes nothing for
the reason record 0011 gives, and every push after it publishes nothing because the pull request
is there.

A run that continues a branch publishes nothing on its first push. It publishes when it writes its
own body, which is the push that changes the file.

When the push that wrote the body fails to publish, a later push does not publish that body for
it. A person who fixed what failed re-runs the job, which reads the same push event and publishes.
A run that continues the branch writes the body again, and that push publishes.

A run that writes the same body twice, byte for byte, changes nothing and publishes nothing. The
body has to change, and a run that continues a branch has new run notes to write.

## What this does not cover

GitHub lists at most three hundred files in a comparison. A push that changed more than that and
the body with it may find the body missing from the list, and then it publishes nothing and says
so. That failure stays on the side of publishing nothing.

A push that merges `main` into the branch is compared from the commit before the merge. When `main`
changed the body file and the merge took that change, the push counts as one that changed the body.
The body it carries then closes the issue of the run on `main`, and record 0011 stops it there.

The check says the push changed the file. It does not say the run read what it wrote.
