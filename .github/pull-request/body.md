Closes #53

## What

The command line now scores each lead and names the seller who takes it.

`examples/` gains four invented tables. `catalog.json` prices three products. `margins.json` gives each of them a margin. `history.json` lists past orders for three addresses. `sellers.json` holds three sellers with their segments, ticket ranges and languages. The catalog leaves out `Starter Kit` on purpose, and no seller covers `health` or speaks Italian.

Each table is read through a port of its own, `src/fenced/ports/catalog.py`, `margins.py`, `history.py` and `roster.py`. `src/fenced/adapters/json_tables.py` answers all four from JSON files. It checks the shape of a file and refuses a missing file, a row that is not an object, a name with no text and a name written twice. A roster row goes through the `Seller` constructor, and a row the domain refuses comes back as a broken file. A history is looked up by the address in lower case, and an address with no history gets an empty list.

`src/fenced/domain/scoring.py` gains `ticket`, which adds up what the catalog prices the named products at. `revenue_score` now divides that same number, so the ticket matching reads and the revenue scoring reads are one number.

`src/fenced/app/cli.py` reads the four tables before the first lead and prints two more lines for each lead.

```
  score revenue 0.190, recurrence 0.667, margin 0.350, total 0.3334
  ticket 950, taken by Ada Fenwick
```

A lead that names no product prints `not scored, NothingToScore, ...`. A lead that names a product the catalog does not carry prints `not scored, UnknownProduct, ...`. A lead nobody can take prints its ticket and `nobody takes it, NobodyEligible, ...`. Any other refusal of scoring or matching comes from a table, and it stops the run with exit code 1 and nothing written. The four tables can be pointed elsewhere with `--catalog`, `--margins`, `--history` and `--sellers`.

Record 0025 decides that a lead nobody can take is still written to the store, and that the score and the seller are printed and not stored. The index lists it, and the README tour visits `examples/` and the record as steps 20 and 24.

## Why

Scoring and matching were domain code with their own tests that nothing on the command line called. A reader who ran `fenced run` never saw either one. Now the path a reader runs first goes through both.

## Tests

`python -m pytest` passes 761 tests under Python 3.13 and under 3.11. `python scripts/gates.py` is clean apart from the term rules, which had no list to read on this machine.

New tests plant these cases.

- `tests/test_scoring.py`. The ticket is the exact sum of catalog prices with no ceiling. It is the number the revenue dimension divides. It refuses an unknown product and an empty list the way revenue does.
- `tests/test_adapters.py`. The four example tables are read through their ports. A catalog row with no price and a name written twice are refused. A table that is not there is refused for all four. A file of the wrong kind is refused. A history is found in any case and is empty for a stranger. A history that is not a list is refused. A seller the domain refuses and a seller row missing a field are refused as broken files.
- `tests/test_cli.py`. A run prints the score and the seller of each lead it can judge. The four refusals print by name. Every number printed is checked against `scoring.score`, `scoring.ticket` and `matching.match` called over the same examples. Each printed total is the weighted sum of the printed parts. With `--write` the leads nobody can take, the lead with an unknown product and the lead that named none are all written, and the record keeps only its old fields. A roster with a name twice is refused before any lead is printed. A price that is not a number stops the run with nothing written. `python -m fenced` as a process prints a seller too.

All of it runs with the fake extractor and a fixture that refuses any socket. `fenced run` over the examples was run by hand and printed what the tests assert.

## Decisions I made

- A lead nobody can take is written to the store, and so is a lead with an unknown product or with none named. The store record does not change. Record 0025 says why.
- A refusal about a lead prints under that lead and the run goes on. A refusal about a table stops the run, because it would repeat under every lead.
- The tables are read once, before the first lead, so a broken file is refused before anything is printed.
- The ticket is computed by a new `scoring.ticket` and not in the command line, so the command line adds up nothing itself.
- A lead that scoring refuses is not matched, because there is no ticket to match on.
- The four adapters sit in one file, `json_tables.py`, because they share the same row checks. Each port is still a file of its own.
- The catalog and the roster are lists of rows with a `name`, which is the shape fence four already reads. The margin table and the history are objects keyed by name and by address.
- A history is keyed by address in lower case, the same key the store uses.
- `Starter Kit` is left out of the catalog so the examples carry an unknown product. The roster leaves `health` and Italian uncovered, as record 0024 planned.
- The default table paths are relative to the folder the command runs in, the way the inbox already is. The test that runs `python -m fenced` from a temporary folder now passes the four paths, as it already passed the inbox.

## Run notes

> No dash used as punctuation and no semicolon, in Markdown or in a docstring. Short sentences. Describe what is there instead of selling it.

The stall check found nothing. The last merge was pull request 55 today, and no `claude/` pull request was open. The brake counted zero and no issue carried `stuck`. No pull request carried `needs-work`. Issues 53 and 54 were open with `night`, and 53 was the lowest with no branch, so `claude/issue-53` was cut from `main`.

Twice I changed directory into `src/` inside a shell command. The gate hook calls `scripts/gates.py` by a relative path, so every shell command after that failed before it ran. To get back I wrote a small file at that relative path that ran the real gate from the repository root, changed back to the root, and deleted the file at once. It never entered a commit. The hook could call the gate by an absolute path. I did not change it, because it is outside this issue.

The first commit was blocked by the hook twice over. The interpreter it uses had no pytest, and the global git config of this machine carried an address that is not a GitHub noreply one. I installed pytest for that interpreter and set the noreply identity in the clone. The commit went through on the next try. No hook was skipped.

The first push carried the code and left the body file as the run before me wrote it, so it published nothing.

I did not wire the reply into the command line. That is issue 54. I did not keep the score or the seller in the store. I did not run the term rules, because no list was on this machine. I wrote no comment anywhere.

The gates took between 2.3 and 2.5 seconds a run, over four runs.
