Closes #28

## What

The nine names the issue planted are refused now, and the lists that refuse them are held to the record that says what a door is.

Fifteen names joined `DOORS_TO_THE_OUTSIDE`. `curses`, `tty`, `termios`, `pty`, `readline` and `rlcompleter` reach the terminal, which the record names outright. `compileall`, `py_compile`, `zipapp` and `filecmp` write or read a file on disk. `syslog` reaches the log of the machine. `posix` and `nt` are the module `os` is, under the name the platform gives it, and `grp` and `pwd` read the user database beside it.

Three names joined `SOURCES_OUTSIDE_THE_ARGUMENTS`. `concurrent` and `_thread` are a second thread of execution, which `threading` was already refused for. `sched` runs on a clock it reads itself unless it is handed another.

The part meant to last is the check beside them. `docs/adr/0010-a-door-list-is-checked-against-the-record.md` quotes the two sentences of record 0005 and writes out, thing by thing, the standard library names that reach each one. `door_list_problems` in `tests/test_fences.py` reads the quotes back against record 0005, the rows against the quotes, and every name in a row against the list the table says it is on. It fails on six things.

    a quote record 0005 does not say
    a thing a sentence names with no row
    a row for something no sentence names
    a name in a row that is not a standard library module
    a name in a row that is on no list of doors
    a name on RUNTIME_DOORS that no row reaches, or a row that reaches what is not on it

So the next omission is a row that disagrees with a list, which is a red suite, instead of a name somebody happened to plant.

Record 0005 keeps its status and its decision. It gained one line pointing at 0010. The index carries 0010 and the README counts the checks and the planted tests again.

## Why

The issue is right that this is not the incompleteness record 0005 prices in. `threading` was refused and `concurrent` was not, and both are a second thread of execution. `select` was refused and `curses` was not, and the record names the terminal in the sentence that defines the list.

A list that refuses one name and passes another doing the same thing is a bug. Record 0005 says so itself and says it is closed by name. What it had no answer for is the next one, because a name can be added forever and the sentence that named it has no way to say it is still waiting.

Quoting the sentence into a record and reading it in a test is what gives the sentence a voice. The lists and the words that define them are one thing now, and they cannot drift apart quietly.

## Tests

`python -m pytest` is green at 256 tests, up from 248. `python scripts/gates.py` is clean apart from the term rules, which is the correct verdict in a clone with no private list.

Eight of those tests are new.

One plants each of the nine names from the issue inside `domain/` and asserts the exact line the fence reports, which is the report the issue asked for read back the other way. One runs the new check over this tree. Six plant a record and a list that disagree, one shape each. A name in a row that is on no list. A table whose rows do not match the sentence, in both directions at once. A quote the record does not say. A name in a row that is not a module at all. A runtime door no row reaches. A tree with neither record in it, which fails closed rather than passing on nothing.

The planted violation test that walks both module lists covers the eighteen new names without a line written for them, because it reads the constants.

## Decisions I made

- The table lives in a new record and not inside 0005. The index says a record is not rewritten to match a later opinion. The decision of 0005 did not change, so it keeps its status and gains one line pointing forward.
- The two sentences are copied into 0010 and not pointed at. A pointer cannot notice a reword. The test asserts the quote is a sentence record 0005 still says, so a reword fails the suite until the quote is reworded with it.
- The first two tables are read one way. A name on a list with no row passes. `sys`, `importlib`, `signal` and `platform` reach things the two sentences never name, and record 0005 says the list is generous where a domain module might plausibly go. The direction worth failing on is a thing the record calls a door with no name behind it.
- A name that is both kinds goes on the list of the first kind, because reaching outside the process is the larger claim and the fence reads that list first. `asyncio` and `multiprocessing` are the two. So a row of the second kind is satisfied by either list and a row of the first kind is not.
- Eight names beyond the nine the issue planted. `posix` and `nt` are `os` reached under another name, which is the widest door on the list. `grp` and `pwd` read the user database. `filecmp` opens two files. `readline` and `rlcompleter` reach the terminal and a history file. `sched` reads a clock. Each one is a name the sentences already cover, and leaving them for the next issue would be leaving the same bug in place.
- The rows carry the names whose claim is plain. `pickle` is on the list because loading one runs code, and no sentence of the record names that, so it has no row. A row is the record reading itself, and a stretched row is worse than none.
- The README said eight planted tests and there were twenty six. The count is right again, and the fence paragraph says the first fence has a second function beside it.

## Run notes

> No dash used as punctuation and no semicolon, in Markdown or in a docstring. Short sentences. Describe what is there instead of selling it.

Four commits on `claude/issue-28`, pushed one at a time from the first. The first commit takes `.github/pull-request/title.md` and `.github/pull-request/body.md` off the branch, because issue 31 is open and a branch created from `main` carries the text of the run before it. The two files come back in this commit, which is the last one, so this push is the one that publishes.

The machine this run works in had no `pytest`. The first commit was refused by the hook, which said the tests did not run rather than that they passed. Installing `pytest` is what fixed it. Nothing in the repository changed for it, and no gate was skipped or softened to get past it.

The gates were quick. `python -m pytest` takes about 0.5 seconds at 256 tests. `python scripts/gates.py`, which is the suite and the text rules over every tracked file, takes about 0.8 seconds. `python scripts/gates.py --text` takes about 0.15 seconds. The hook ran the same gate before every commit and every push. No gate failed after `pytest` was there.

What this run did not do. It did not go looking for doors nobody has named yet, because the rows are written by hand like the lists and a row that forgets a module is as silent as a list that forgot it. It did not give `sys`, `importlib`, `signal` or `platform` a row. It did not change the line the fence reports for a refused import, so every test that reads those lines still reads them. It did not touch `scripts/gates.py`, the workflow, or any pull request that is already open.
