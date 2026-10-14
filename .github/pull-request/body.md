Closes #6

## What

`src/fenced/ports/` gains three shapes beside the store and the journal. `Extractor` turns text
into fields. `Clock` says the moment now as ISO 8601 text with an offset. `Inbox` lists messages,
each one an id, the moment it arrived and the text.

`src/fenced/adapters/` is new and holds what answers them.

- `json_crm.py` keeps the store as one JSON file of records by key, written beside itself and
  moved into place. `json_journal.py` keeps the journal as JSON lines and waits for the disk
  before an append returns. `json_inbox.py` reads the messages and refuses one with a missing
  field, a repeated id or a moment with no offset.
- `clock.py` has `SystemClock` and `FixedClock`.
- `fake_extractor.py` reads by fixed rules. The address is the first word with an at sign, the
  name is the last line without one, and the awareness is the first row of a table of phrases.
- `llm_extractor.py` is the only file that names a provider. It posts to the Messages API with
  `urllib`, asks for the three fields through a JSON schema, and reads the key from
  `FENCED_LLM_API_KEY`. With no key it raises `MissingKey`, whose message says what is missing
  and what runs without it.

`src/fenced/app/cli.py` is the command line, run as `python -m fenced` or `fenced`. `fenced run`
reads `examples/messages.json`, prints each lead with the next step the playbook names and when
it is due, hands back a message the boundary refuses, and prints the plan. It writes only with
`--write`, and then names the run by its journal entry. `fenced undo N` shows the undo of run N
and carries it out with `--write`. `examples/messages.json` holds six invented messages on the
reserved example domains and no phone number. Five become leads and one has no address.

The README has three more tour lines and a section on the command line, and
`docs/adr/0019-the-command-line-simulates-with-the-fake-extractor-unless-told-otherwise.md`
records the decisions below that a reader would ask about.

## Why

The README promised a write that is planned, shown, applied behind a flag and undone, and
issue 5 built that against stores kept in the tests. Nothing yet reached a file, a clock or a
model. This puts each of those behind a port, in the one folder allowed to touch them, and gives
a person one command that runs the whole path with nothing to set up.

## Tests

`tests/test_cli.py` has 16 tests. They run `main` end to end over the examples with the fake
extractor, and a fixture refuses any socket, so a test that reached the network would fail.

- A run simulates by default and leaves no file. It prints each lead with its step and due
  moment, and hands back the message with no address. `--now` decides which steps are late.
- `--write` keeps five records and one journal line, and neither file holds a line of any
  message. A second run over the same inbox has nothing to write.
- An undo simulates by default, takes the run back with `--write`, is refused a second time,
  and its own undo brings the records back. An unknown run is refused.
- `--extractor model` with no key exits 2, prints the explanation and leaves no store. A moment
  with no offset and a broken inbox are refused before anything is written.
- `python -m fenced run` as a process prints the same plan.
- The examples carry no run of seven digits once separators are taken out, and every address is
  on `example.com`, `example.org` or `example.net`.

`tests/test_adapters.py` has 45 tests. The store, the journal and the inbox against their files
and their refusals, the two clocks, the fake rules, and the write layer applied and undone
through the two files with fresh adapters reading back. The model extractor runs with a sender
of the test's own. The tests read the request it builds, that the key goes only in its header,
that `FENCED_LLM_MODEL` changes the model, that seven malformed answers are refused, and that a
refused request names the status and not the body.

`python -m pytest` is 625 passed. `python scripts/gates.py` is clean apart from the term rules.

## Decisions I made

The fake extractor is the default and the model needs `--extractor model`. The README says no
command asks for a credential, and the issue asks for a test with no network.

The message of a lead is always the text in the inbox. Whatever the extractor returns under that
name is replaced, and the model is not asked to copy the text back.

A run id is the number of the journal entry the run wrote, because that is what `undo` already
takes. An undo that writes is a run with a number of its own.

The clock port returns ISO 8601 text and not a `datetime`, because fence one refuses `datetime`
inside `ports/`. The command line turns the text into a moment.

The clock is used for the one thing the command line needs a time for. It reads each step's due
moment, which is the message's arrival plus the playbook window, and marks it `late` or `open`.

The command line is `src/fenced/app/cli.py`, where the third fence already allowed a module to
reach the store. It opens no file itself. The arguments, the environment and the streams are
parameters of `main`.

The model adapter asks for the default model it names at low effort, with JSON schema output
and the provider's default fallback for a refusal. Any stop other than a finished turn is refused.

Scoring, matching and the reply are not wired in. Each needs fields the extractor does not return
yet, and that is a question for its own issue. Record 0019 says so.

## Run notes

The text rule of AGENTS.md, in one line: "No dash used as punctuation and no semicolon, in
Markdown or in a docstring. Short sentences. Describe what is there instead of selling it."

What I did. The stall check came first. The most recent merge is pull request 46 from earlier
today, and no pull request on a `claude/` branch was open, so nothing was waiting. The brake
counted none and no issue carried `stuck`, so there was nothing to rework. Issue 6 is the only
open issue labelled `night`. No branch for it was on origin, so `claude/issue-6` was made from
`main`. There were two commits, code and tests first, pushed on their own, then the README and
record 0019, and then this title and body, which is the push that opens this pull request.

What I did not do. The model extractor was never run against the provider, because this machine
has no key and should not have one. Its request is tested and its answer is not. Nothing in the
domain or the write layer changed, and no fence changed. No comment anywhere and no label set.

One thing on the machine, the same one the last run met. A shell command moved the working
directory into `src/fenced/adapters`, and the commit hook looks for `scripts/gates.py` from the
working directory, so it refused the next command. I wrote a three line file there that runs the
real gate from the root, used it for one command to step back, and deleted it in that command.
It was never added or committed, and the gate ran in full each time.

The machine's `python` is 3.11 and carried no pytest, so pytest was installed into it. The code
runs on 3.11 and the CI runs 3.12 and 3.13. The git identity was set in a command of its own
before the first commit, and both commits carry the noreply address.

The gates. `python -m pytest` is 625 passed in 1.6 seconds. A full run of
`python scripts/gates.py`, tests included, took 2.6 seconds. The term rules did not run, because
no list of private terms was pointed at, and the run says so rather than calling itself clean.
