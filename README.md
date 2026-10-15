# fenced

A small Python service whose architecture is enforced by tests, not by the README.

The rules below are not advice. They are `tests/test_fences.py`. They run in CI on every push, and
again before every commit an agent makes in here, through the hook in `.claude/settings.json`.

The fences are in and green, and the domain sits behind them. The command line reads invented
messages, turns each one into a lead, names its next step and when it is due, scores it, names
the seller who takes it, prints the reply as a draft for a person to send, and plans the write
that records the lead. It sends nothing.

## Why

Architecture written in a README rots, because nothing reads it. Here a layer boundary is a test. A
change that makes the domain import an HTTP client turns the build red before a person looks at it,
and the decision behind the boundary is written down next to the test that defends it.

An agent that decides is an agent you cannot test. Here the model does one job, which is turning
free text into fields. Everything after that is ordinary code with ordinary tests. The model does
not set a price, does not promise a date, does not pick a person and does not produce a score.

A write that goes straight to the record store cannot be reviewed or taken back. Here a write is
planned first, shown as a diff, applied only behind a flag, recorded in a journal, and undone from
that journal.

## The fences

| Rule | How the test checks it | What breaks without it |
|---|---|---|
| `domain/` and `ports/` answer from their arguments and nothing else | reads the imports and the calls with `ast` | the business rules stop being testable offline |
| the name of a model provider appears in one adapter and nowhere else | text search across `src/` | changing model turns into starting over |
| nothing persists a record outside `writes/` | finds the calls with `ast` | simulation, journal and undo are lost together |
| a prompt carries no price, product or person | reads the prompt constants and the example data | the model starts knowing what it should have asked |
| every decision record has a status, a date and a line in the index | reads `docs/adr/` | the decision gets argued again in six months |
| nothing shaped like a credential is in the tree | scans every tracked file, and refuses a tracked `.env` | a leak |

Each fence is one short function. They are hand written on purpose, with no library, so the rule
and the check sit on one screen. All six are tested against a planted violation, because a fence
nobody ever watched reject anything is decoration. The first fence has a second function beside it,
which holds its lists of doors to the record that says what a door is.

Nothing in that table is only a description. Each fence quotes the rule of its row, and
`test_the_readme_describes_the_fences_the_file_carries` reads the rows and the fences back against
each other. A row with no fence fails, a fence with no row fails, and so does a check that no test
ever planted a tree for. The counts in the tour below come off the same file. A test that plants a
tree carries a mark saying whether the check has to refuse that tree or accept it, and the mark is
read back against what the test asserts, so a mark that disagrees with its own assertion is a
failing test. `docs/adr/0013-the-readme-is-read-back-and-a-planting-test-says-what-it-plants.md`
says why the count is read off the mark and not off the parameter, and why the mark alone is not
enough to read it off.

## Fifteen minute tour

1. `tests/test_fences.py`. The point of the repository. Six rules, eight checks, thirty eight
   tests that plant a tree a check has to refuse, and five tests that plant a tree it has to
   accept.
2. `docs/adr/0001-architecture-rules-live-in-tests.md`. Why they are tests and not a config file.
3. `scripts/gates.py`. The same rules on text, for the places a test cannot reach.
4. `.github/workflows/ci.yml`. Python 3.12 and 3.13, actions pinned by commit.
5. `src/fenced/domain/lead.py`. The first piece of the domain, and the boundary everything the
   model returns has to cross.
6. `docs/adr/0002-awareness-is-closed-and-the-boundary-refuses.md`. Why that boundary refuses
   instead of coercing.
7. `src/fenced/domain/scoring.py`. How good a lead is, as arithmetic over the catalog, the history
   and the margin table.
8. `docs/adr/0003-a-score-is-decimal-arithmetic-over-three-dimensions.md`. Why that arithmetic is
   decimal, and why the parts stay next to the total.
9. `src/fenced/domain/matching.py`. Who takes the lead, by three hard rules and an order
   written down in one function.
10. `docs/adr/0014-a-seller-is-picked-by-hard-rules-and-a-written-order.md`. Why the order is
    written rather than left to the roster.
11. `src/fenced/domain/playbook.py`. What happens next at each level of awareness, and how long
    the window is.
12. `docs/adr/0015-a-return-window-is-hours-from-the-message.md`. Why that window is hours from
    the message and not a time of day.
13. `src/fenced/domain/reply.py`. The reply, as a template and the typed fields that fill it, with
    every number in the text answered for by one of them.
14. `docs/adr/0016-a-reply-is-a-template-of-typed-fields.md`. Why a value proves which source built
    it, and what happens to a number nobody can answer for.
15. `src/fenced/ports/`. The record store and the journal, as the methods the write layer calls,
    and the extractor, the clock, the inbox, the catalog, the margin table, the purchase history
    and the roster, as what the command line asks of each. Nothing there says where anything
    lives.
16. `src/fenced/writes/`. A write as a plan and its diff, an executor that simulates unless it is
    told otherwise, a journal entry written before the store, and an undo read from that entry.
17. `docs/adr/0018-a-write-is-journaled-first-and-undone-from-the-journal-alone.md`. Why the entry
    goes first, why it keeps a hash and not the text, and what a write that fails halfway leaves.
18. `src/fenced/adapters/`. The outside world. The store and the journal as files, the inbox,
    a clock, a fake extractor that reads by fixed rules, the four tables in `json_tables.py`, and
    `llm_extractor.py`, the only file that names a model provider.
19. `src/fenced/app/cli.py`. The command line. It reads `examples/messages.json`, prints each
    lead with its next step and when that step is due, then its segment, its language and the
    products the person named, then its score in three parts and a total and the seller who
    takes it, then the reply as a draft for that seller to send, and shows the plan. A lead
    scoring or matching refuses prints the refusal by name, and a lead with no seller prints
    why it has no draft. It sends nothing. It writes only with `--write`, and `fenced undo N`
    takes a run back by the number it was written as.
20. `examples/`. The invented messages, and the invented catalog, margin table, purchase
    history and roster a run scores and matches against.
21. `docs/adr/0019-the-command-line-simulates-with-the-fake-extractor-unless-told-otherwise.md`.
    Why the default run needs no key, why the message is never the model's, and what a run id is.
22. `docs/adr/0020-the-model-returns-fields-and-nothing-else.md`. Why the model is asked for
    fields and nothing more.
23. `docs/adr/0024-what-a-wrong-product-language-or-segment-costs.md`. What a wrong product, a
    wrong language and a wrong segment cost, and why each one is refused where it is.
24. `docs/adr/0025-a-lead-nobody-can-take-is-still-written.md`. Why a lead nobody can take is
    still written, and why the score and the seller are printed and not stored.
25. `docs/adr/0026-a-draft-is-printed-and-kept-nowhere.md`. Why a draft is printed and kept in
    no file, the journal least of all.
26. `docs/adr/0021-no-secret-enters-the-tree.md`. What the fence on secrets catches and what it
    misses, each as far as a named test proves it.
27. `SECURITY.md`. How to report a problem, and what this repository promises about secrets and
    data.
28. `AGENTS.md`. The rules an agent works under in here, from what never enters the tree to
    the shape of a pull request.
29. `.github/workflows/pull-request.yml`. The job that opens a pull request from a runner, with
    the text the branch carries and the rules `main` carries.
30. `scripts/publish.py`. The one way a pull request body leaves this repository, once and never
    edited.
31. `docs/adr/0008-a-pull-request-is-opened-from-a-workflow-runner.md`. Why that call is made
    from a runner and not from the machine the code is written on.

A new file gets its line here with the pull request that adds it.

## How the work happens

1. Issues the owner labels `night` are the backlog, and the owner decides what enters it.
2. A routine, started on a schedule or by hand, takes the lowest one, writes the code on a
   branch and opens one pull request.
3. The gates run on every commit and on every pull request body. What fails them does not go
   through.
4. A second agent session reviews each pull request, and either sends it back with
   `needs-work` or merges it.
5. An agent writes the code and another agent reviews and merges it. No person reviews every
   pull request. The owner writes the rules in `AGENTS.md` and in the routine's instructions,
   and can stop the loop at any time.

## Run it

```
python -m pip install -e ".[dev]"
python -m pytest
python scripts/gates.py
```

The install is the one step that reaches the network, once, for `pytest` and the build backend. Everything after it
runs offline. The command line also runs straight from the clone with nothing installed, as
`PYTHONPATH=src python -m fenced run`.

The command line, over the invented messages in `examples/`.

```
fenced run                  # show each lead, its next step, its score, its seller, its draft and the plan
fenced run --write          # write the plan and journal it as run 1
fenced undo 1               # show what taking run 1 back would change
fenced undo 1 --write       # take it back
```

The store and the journal are files under `.fenced/`, which git leaves out. `--store` puts them
somewhere else, and `--now` reads the windows against a moment you give instead of the clock.
`--catalog`, `--margins`, `--history` and `--sellers` read the four tables from files of your own
instead of the invented ones.

No key, no network, no service. If any command here asks you for a credential, that is a bug.
The one exception is a run with `--extractor model`, which reads the key from
`FENCED_LLM_API_KEY` and says so and stops when it is not set.

## What the model is not allowed to decide

| Decision | Where it actually lives |
|---|---|
| price | the catalog |
| turnaround | a written rule |
| who takes the lead | a deterministic match |
| how good the lead is | a calculation over data |
| what the reply says | a template filled by typed fields |
| whether the reply is sent | a person |

The model never writes the reply. It fills the fields of a lead, and the reply is a template filled
by fields only the catalog, the matching and the playbook can build. The command line prints it as
a draft and a person sends it.

## What this is not

- Not a framework. It is a reference small enough to read in one sitting.
- Not a product, and not for sale.
- No runtime dependency. Standard library only, with `pytest` for the tests.
- Not a generic architecture. It is one shape of one problem, defended.

## Related tools

- [import-linter](https://import-linter.readthedocs.io/en/stable/readme.html),
  [pytest-archon](https://github.com/jwbargsten/pytest-archon) and
  [tach](https://github.com/gauge-sh/tach) do the first three fences properly once a project is big
  enough to need them.
- [MADR](https://adr.github.io/madr/) is the decision record format this repository trims down.
