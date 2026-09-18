# 5. A door is a name that answers from outside the arguments

Status: accepted
Date: 2026-09-18

## Context

`AGENTS.md` says `domain/` and `ports/` stay pure and only `adapters/` reach the outside world. The
first fence in `tests/test_fences.py` is what enforces that. It reads the imports of every file in
the two pure packages and refuses three things. A name that is not in the standard library. A name
under `fenced` that is neither `domain` nor `ports`. A standard library name on a written list of
doors.

Planted inside `domain/` and run against the fence as it stood, four of them passed.

    open() bare      -> the fence said clean
    import datetime  -> the fence said clean
    import random    -> the fence said clean
    from ctypes      -> the fence said clean

The door list banned `io`, `os`, `pathlib`, `shutil` and `tempfile`, which is every route to a file
except the builtin that opens one. `ctypes` loads a shared library and calls into it, which is every
door at once. A clock and a source of randomness were a question the list had never answered,
because neither of them reaches outside the process.

That question had to be settled now and not later. `src/fenced/domain/scoring.py` promises that the
same catalog, the same history and the same margin table give the same score. `docs/adr/0003` says
the dimensions that come next are about when a message arrived and how long a customer has been
away. The change that adds them reaches for a clock, and a fence that says clean is a fence that
lets the promise go.

## Decision

A door is a name that answers from outside the arguments. There are two kinds of them and the fence
refuses both.

One kind reaches something the process does not hold. A file, a socket, a subprocess, a shared
library, the terminal, the time zone database. `DOORS_TO_THE_OUTSIDE` carries those names and the
line the fence reports says the import reaches outside.

The other kind answers from inside the process and still not from the arguments, and does not answer
the same way twice. A clock, a source of randomness, an identifier drawn from either, and a second
thread of execution. `SOURCES_OUTSIDE_THE_ARGUMENTS` carries those names and the line the fence
reports says the import answers from outside the arguments. So a clock and a source of randomness
are doors. A rule that reads one cannot be pinned by a test, and being pinned by a test is the whole
of what the pure packages are for.

An instant is data like any other. A date the domain reasons about arrives as an argument, from the
adapter that read it or from the caller that decided what now means. That is the shape the next
dimension takes.

`RUNTIME_DOORS` names what reaches with no import statement to read. `__import__`, `eval`, `exec`
and `compile` were already there. `open`, `input` and `breakpoint` join them, because a file and a
terminal are doors whether or not a module was imported first.

The fence reads a name and not an expression. It refuses a call whose function is a name, so
`eval("1")` is caught and `__builtins__["open"]("s")` is not, because the second one is a call on a
subscript. That is the same door reached one step sideways. Reading the expression instead would
mean deciding what an arbitrary piece of syntax resolves to, which is the tracing a written list
exists to avoid, and the shapes it would have to cover have no end a reader could check. So the
hole is written down here rather than closed. A line like that stands out in a diff, and this
record is what a reviewer points at when one appears.

All three lists are written by name, for three reasons. A fence that decided by behaviour would have
to import the module and watch it, which means running the code the fence is there to refuse. A name
is what a reader of the diff sees, so the list can be argued with in review instead of traced
through. And a name costs one line, which is what keeps the rule and its check on one screen.

The price of a written list is that it is not complete and never will be. It is generous where a
domain module might plausibly reach and silent everywhere else. It grows by name when a change
reaches for something that is not on it, and a name that is missing is a bug closed with a test that
plants it, which is the ordinary work `AGENTS.md` describes.

Three other shapes were considered and rejected. Refusing the call rather than the module, such as
`datetime.now` and `random.random`, which reads better and is weaker, because an alias or a name
bound once at import walks straight past it. Allowing `datetime` for the type of an argument, which
costs nothing to give up, because the annotation is a string under `from __future__ import
annotations` and the import would be a standing invitation to read the clock two lines lower.
Leaving the clock off the list and trusting review to catch it, which is architecture written as
advice, and that is the thing this repository is against.

## Consequences

A domain module cannot ask what time it is. The caller decides what now means and passes it in, so a
test can say what now was, and a rule about how long a customer has been away can be pinned to a
literal.

Nothing in the tree had to move. `lead.py` and `scoring.py` import `re`, `collections.abc`,
`dataclasses`, `enum` and `decimal`, and none of those is on either list.

`sys` is on the list, so a domain module cannot write to a stream of the process or read its
arguments. A domain module that wants to say something returns it.

`pkgutil`, `zipimport` and `modulefinder` import a module by name, which is what `importlib` and
`runpy` already did, so they are on the list as well. `sysconfig` and `site` read the install
layout off disk, which is the first kind of door. A list that is incomplete is the price named
above. A list that refuses one name and passes another doing the same thing is a bug, and it is
closed by name like any other.

A planted violation test covers every name on all three lists, one planted file per name, and
asserts the exact line the fence reports. The two tests that walk the module lists read the
constants, so a name added later arrives with a planted violation of its own. What each of those
tests proves is the refusal, and the planting is the part written by hand.
