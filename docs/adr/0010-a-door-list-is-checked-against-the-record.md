# 10. A door list is checked against the record that names the doors

Status: accepted
Date: 2026-09-21

## Context

Record 0005 defines a door in two sentences, and each one names examples. The first kind reaches
something the process does not hold, and it names a file, a socket, a subprocess, a shared library,
the terminal and the time zone database. The second answers from inside the process and not from the
arguments, and it names a clock, a source of randomness, an identifier drawn from either, and a
second thread of execution.

The lists did not cover what those two sentences name. Planted inside `domain/` and run against the
fence as it stood, `curses` passed and the record names the terminal outright. `concurrent` passed
and `threading` did not, and both are a second thread of execution. `compileall` passed and it
writes a compiled file to disk. So did `tty`, `termios`, `pty`, `syslog`, `py_compile` and `zipapp`.

Record 0005 prices in a list that is incomplete, and this is not that. A list that refuses one name
and passes another doing the same thing is a bug, and it is closed by name. The question left over
is what closes the next one. A name can be added forever, and the sentence that named it has no way
to say it is still waiting.

## Decision

The lists carry every name the two sentences name, and a test holds them to it.

The two sentences are quoted here as record 0005 writes them.

> A file, a socket, a subprocess, a shared library, the terminal, the time zone database.

> A clock, a source of randomness, an identifier drawn from either, and a second thread of execution.

Each thing a sentence names has a row below, and the row carries the standard library names that
reach it. `test_the_door_lists_carry_every_name_the_record_calls_a_door` reads the quotes, the rows
and the lists, and it fails on five things. A quote record 0005 does not say. A thing a sentence
names with no row. A row for something no sentence names. A name in a row that is not a standard
library module. A name in a row that is on no list of doors.

| Reaches something the process does not hold | Names on `DOORS_TO_THE_OUTSIDE` |
| --- | --- |
| a file | `bz2`, `compileall`, `configparser`, `dbm`, `fcntl`, `filecmp`, `fileinput`, `glob`, `grp`, `gzip`, `io`, `linecache`, `logging`, `lzma`, `mmap`, `netrc`, `nt`, `os`, `pathlib`, `posix`, `pwd`, `py_compile`, `shelve`, `shutil`, `site`, `sqlite3`, `sysconfig`, `tarfile`, `tempfile`, `zipapp`, `zipfile` |
| a socket | `asyncio`, `ftplib`, `http`, `imaplib`, `poplib`, `select`, `selectors`, `smtplib`, `socket`, `socketserver`, `ssl`, `syslog`, `urllib`, `xmlrpc` |
| a subprocess | `multiprocessing`, `pty`, `subprocess`, `webbrowser` |
| a shared library | `ctypes` |
| the terminal | `curses`, `getpass`, `pty`, `readline`, `rlcompleter`, `termios`, `tty` |
| the time zone database | `zoneinfo` |

| Answers from outside the arguments | Names on `SOURCES_OUTSIDE_THE_ARGUMENTS` |
| --- | --- |
| a clock | `datetime`, `sched`, `time` |
| a source of randomness | `random`, `secrets` |
| an identifier drawn from either | `uuid` |
| a second thread of execution | `_thread`, `asyncio`, `concurrent`, `multiprocessing`, `threading` |

A name sits on one list, and two of them are both kinds. `asyncio` runs a second thread of execution
and reaches a socket, and `multiprocessing` runs one and starts a subprocess. A name that is both
goes on `DOORS_TO_THE_OUTSIDE`, because reaching outside the process is the larger claim and the
fence reads that list first. So a row of the second kind is satisfied by either list, and a row of
the first kind is satisfied by the first list alone.

`RUNTIME_DOORS` is the third list, and it holds the names that reach with no import statement to
read. Record 0005 writes those names out one by one, so the table below carries all of them and the
test reads it both ways. A name on the list that no row names fails, and a name in a row that is not
on the list fails.

| Reaches with no import statement to read | Names on `RUNTIME_DOORS` |
| --- | --- |
| a module by name | `__import__` |
| code made out of text | `compile`, `eval`, `exec` |
| a file | `open` |
| whoever is at the terminal | `breakpoint`, `input` |

## Consequences

Fifteen names joined `DOORS_TO_THE_OUTSIDE` and three joined `SOURCES_OUTSIDE_THE_ARGUMENTS`. The
planted violation test that walks both lists covers every one of them, because it reads the
constants rather than a list of its own.

The first two tables are read one way. A list may carry a name no row names, and `sys`, `importlib`,
`signal` and `platform` are four of those. The sentences do not name what those reach, and record
0005 says the list is generous where a domain module might plausibly go. The direction worth failing
on is the other one, a thing the record calls a door with no name behind it on the list.

A reword of either sentence fails the test until the quote is reworded with it. That is what quoting
buys over pointing. Record 0006 was reworded once and a record can be, and what cannot happen
quietly is a sentence naming a door the list never got.

What this does not do is find a name nobody thought of. The rows are written by hand, the same way
the lists are, and a row that forgets a module is as silent as a list that forgot it. What it does
is make the record and the lists one thing. They cannot drift apart without a red suite, the next
omission is a row rather than a planted import, and a row is one line a reviewer reads in a diff.

Record 0005 keeps its status and its decision. It gained one line pointing here, because a reader
of the sentences should find the names they stand for.
