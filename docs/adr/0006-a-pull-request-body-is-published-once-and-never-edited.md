# 6. A pull request body is published once by a plain REST call and never edited

Status: accepted
Date: 2026-09-18

## Context

Every pull request this repository had opened carried attribution and a session link, in the edit
history of its body, where nothing looks.

The chain was the same every time. The sandbox the night run works in has no `gh`, so the body was
published by a tool that appends a line naming the agent and linking to the run that wrote it. The
run read the body back, saw the line, and edited it out. The published body ended up clean and the
version before the edit stayed, because an edit is what writes the earlier version into the history
of the body. GitHub keeps that version for good. Closing the pull request does not remove it.

Measured over the pull requests opened before this one:

    versions checked: 11, carrying attribution or a session link: 2
      pull request 12 body
      pull request 16 body

The text gate was not wrong and it was not late. It read the file, the file was clean, and the line
arrived after that, between the gate and GitHub. Reading the body back and editing was the repair,
and the repair is the thing that records.

## Decision

A pull request body leaves this repository once, through `scripts/publish.py`, which posts it with
`urllib.request`. Nothing sits between the file and the wire, so nothing can append to it.

The gate runs before the call, over the title and over the body, because text that breaks a rule
must not reach GitHub at all. Then the pull request is read back and compared to what was sent, and
the gate runs again over the stored body. That read is a check and not a repair. When the two
disagree the publisher says so and stops, and the body on GitHub stays as it is.

There is no route in `scripts/publish.py` that changes a body that already exists. The absence is
the fence, and a test reads the source and refuses the words that would start one.

The token arrives in `GITHUB_TOKEN` or in `GH_TOKEN`. No key is written down in this tree.

Three other shapes were considered and rejected. Keeping the appending tool and editing faster,
which changes nothing, because one edit is one recorded version whenever it happens. Publishing an
empty body and filling it in afterwards, which records an empty first version and still needs the
edit. Turning attribution off in the settings of the tool that appends it, which is a setting on one
machine, and a rule this repository keeps cannot live somewhere a stranger reading the tree cannot
see.

## Consequences

The night run publishes through one file it can read, and a reviewer can see the whole route out in
one screen.

A pull request opened before this decision keeps what its history already holds. Nothing here can
take a stored version back, and an edit made to try would add one more.

The publisher refuses more often than a tool would. No token, a body that breaks a text rule, a
private term, an answer with no number, a stored body that disagrees. Each one leaves the branch
pushed and the pull request unopened, which is the state a person can act on.

Twenty two tests plant the cases. Each form of an appended line, in the body and in the title, a
semicolon, a private term, a stored body that gained a line, a stored body that disagrees, a missing
token, a refusal from GitHub, and a call that does not complete. Two of them assert that nothing
reached the fake transport at all.

The line endings GitHub stores a body with are folded back before the comparison, because a body
stored with carriage returns is the same body.
