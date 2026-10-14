# 19. The command line simulates with the fake extractor unless told otherwise

Status: accepted
Date: 2026-10-14

## Context

Until this record nothing in `src` reached the outside world. The domain, the ports and the write
layer were all tested against fakes kept in the tests. Issue 6 asked for the adapters that reach
outside and for a command line that ties them together. Four questions came with it that a reader
would ask.

Which extractor runs when nobody says. The README promises that no command asks for a credential,
and the model extractor needs a key.

Where the message comes from. The extractor reads the text a person wrote and returns fields, and
one of the fields a `Lead` needs is that same text.

What a run is, and how one is named so it can be taken back.

How the clock reaches a port, when fence one refuses every module that reads one inside `ports/`.

## Decision

The command line lives in `src/fenced/app/cli.py`. It builds the adapters, hands them to the core,
and decides nothing of its own. `python -m fenced` and the `fenced` script both run it.

The fake extractor is the default. It reads by a few fixed rules written in
`src/fenced/adapters/fake_extractor.py`, so the default run needs no key and no network, and every
test of the command line runs it. The model is used only with `--extractor model`. Its adapter reads
the key from `FENCED_LLM_API_KEY` and from nowhere else, and when the variable is absent or blank the
adapter is never built. The command line prints what is missing and what runs without it, and exits
before the inbox is read, so a run that stops for a key has read nothing and written nothing.

The message of a lead is the text in the inbox, always. Whatever the extractor returns under that
name is replaced before the fields reach `Lead.from_fields`. The model is asked for the name, the
address and the awareness, and it is not asked to copy the text back, because a copy is a chance to
change it.

A run is one apply, and its id is the number of the journal entry that apply wrote. `fenced undo N`
takes that number, and it simulates like a run does until it is given `--write`. An undo that writes
is a run of its own, with a number of its own, so the undo of an undo is how a run comes back, as
`docs/adr/0018` already says.

The clock port returns the moment as ISO 8601 text with an offset. The port names no module that
reads a clock, and the command line turns the text into a moment. `--now` gives the run a fixed
moment, which is how a test, and a person reading a run again, holds the time still. A moment with no
offset is refused by the clock and by the inbox, because it is no moment in particular.

## Consequences

A person who tries the repository gets the whole path, from the inbox to the journal and back, with
nothing to set up. The cost is that the default run reads with rules a real message will beat. The
fake is a stand in for tests and for the tour, and it says so.

A key never sits in a file the command line reads. It is in the environment of the shell that runs
the command, and `.env` stays out of git. A failed request to the provider names the status and not
the body of the answer, so nothing the provider sends back carries the key into an error.

The command line reads the arguments, the environment and the two streams through parameters of
`main`, and opens no file and no socket itself. Every file it touches is touched by an adapter.

Scoring, matching and the reply are not in the command line yet. Each needs fields the extractor does
not return today, such as the products a person asked about and the language they wrote in, and
asking a model for them is a decision of its own.
