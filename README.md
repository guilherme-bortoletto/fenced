# fenced

A small Python service whose architecture is enforced by tests, not by the README.

The rules below are not advice. They are `tests/test_fences.py`. They run in CI on every push, and
again before every commit an agent makes in here, through the hook in `.claude/settings.json`.

Skeleton stage. The fences are in and green. The domain arrives one issue at a time, and the
sections below grow with it.

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
tree carries a mark saying whether the check has to refuse that tree or accept it, and
`docs/adr/0013-the-readme-is-read-back-and-a-planting-test-says-what-it-plants.md` says why the
count is read off the mark and not off the parameter.

## Fifteen minute tour

1. `tests/test_fences.py`. The point of the repository. Six rules, eight checks, thirty four
   tests that plant a tree a check has to refuse, and two tests that plant a tree it has to
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

The rest of the domain, the ports, the adapters, the write layer and the command line arrive with
the issues that build them, and each one gets its line here.

## Run it

```
python -m pip install -e ".[dev]"
python -m pytest
python scripts/gates.py
```

No key, no network, no service. If any command here asks you for a credential, that is a bug.

## What the model is not allowed to decide

| Decision | Where it actually lives |
|---|---|
| price | the catalog |
| turnaround | a written rule |
| who takes the lead | a deterministic match |
| how good the lead is | a calculation over data |

The model never writes the reply. It fills typed fields, and a field it cannot type does not exist.

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
