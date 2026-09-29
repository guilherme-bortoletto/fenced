Closes #4

## What

`src/fenced/domain/reply.py` renders a reply from a template and typed fields. A `Field` carries a
name, the text it renders as, and the `Source` that built it. `Source` is closed at three values,
which are the catalog, the matching and the playbook. A table in the module maps each field name to
the one source allowed to build it, so a field that claims another source is refused in the
constructor, and a name the table does not carry does not exist at all.

Five builders are the only route a field is made by, and none of them takes text from a caller.
`product` and `price` read a row of the catalog. `quantity` counts the products the catalog carries.
`seller` reads the name off the `Seller` the match picked. `window` reads the hours off the playbook.

`TEMPLATES` holds one template for each action the playbook names. `render` fills one, and `reply`
picks the template for a level of awareness and builds the window field itself from that same level,
so the hours in the text and the action behind them cannot disagree. A template that names a field
nothing supplied raises `MissingField`, a field the template has no place for raises `UnusedField`,
and a name no source owns raises `UnknownField`. None of the three renders.

`unsourced_numbers` reads the rendered text and reports every run of digits that no field produced.
`render` refuses one with `UnsourcedNumber`. The check reads runs of digits and not shapes, so a date
and a quantity pass because they came from a field.

`docs/adr/0016-a-reply-is-a-template-of-typed-fields.md` records the decision, with a line in the
index and two lines in the README tour.

## Why

The issue asks for the reply the model does not write. A model that writes it writes a price it read
in a message, a date nobody promised and a name nobody assigned, and none of the three is a mistake a
test can catch, because the text is different every time.

A template alone does not fix that, because a template filled from a mapping of strings carries
whatever the caller had, and the caller is one step away from what the model returned. So a value has
to prove which source built it, and a number in the finished text has to belong to one of those
values. That is what the table of fields and the check on digits do.

## Tests

`tests/test_reply.py` is 104 tests. A full reply renders for each of the five levels of awareness,
and every number in it is one a field produced. A missing field, a field the template has no place
for, a window passed in to `reply`, a template with a brace that names no field, and a template that
is not text are each refused. A value that no source produced is refused three ways, which are a
field claiming a source that is not allowed to build it, a field name no source owns, and a value
that is not a `Field` at all. A number written into the template is refused, including one hidden
inside a word. A date and a quantity pass when they came from a field and are reported when they did
not. Every builder is read back against its source, and every template is read back to assert it
names only fields a source can build, that it says when the person hears back, and that it writes no
number of its own.

The whole suite is 523 tests and passes. `python scripts/gates.py` is clean apart from the term
rules, which no clone here has a list for. The suite was also run under Python 3.12 and Python 3.13,
which are the two versions CI uses, because the interpreter on the machine this ran on is Python
3.11.

## Decisions I made

- A reply names nobody. The issue names three sources, and the person who wrote is not one of them,
  so a name in a reply would be text the model returned. The templates address no one by name, and
  the greeting belongs to whatever sends the reply. The decision record says so under Consequences.
- The check reads runs of digits and has no rule about shapes. The issue asks that a date and a
  quantity pass because they came from a field, so provenance is the only question asked and a date
  needs no pattern of its own. That also means no source of dates was invented, because a date needs
  a clock and a clock is a door fence one refuses.
- `reply` builds the window field itself instead of taking one. A caller who passes a window can pass
  the window of another level, which would put an hour in the text that the action does not match.
  One passed in is refused rather than replaced.
- The catalog is read again in this module rather than shared with `scoring.py`. The two raise their
  own refusals, because a reply that failed to render is not a score that failed to add up, and the
  reading is four lines.
- A field the template has no place for is refused rather than ignored. A value that silently renders
  nowhere is a mistake in the caller, and a reply is text that leaves the building.
- `unsourced_numbers` is public. It is the check, and a reader who wants to know what the rule
  actually is reads it and the test that calls it directly.

## Run notes

The text rule of AGENTS.md is that no dash is used as punctuation and no semicolon, in Markdown or in
a docstring, that sentences are short, and that the text describes what is there instead of selling
it.

Step one found no stall. The most recent merged pull request is #39 from the night before, and there
was no open pull request at all, so nothing was waiting on a person. Step two found no open pull
request whose head branch starts with `claude/` and no open issue carrying `stuck`, so the brake was
clear at a limit of one. Step three had nothing to rework. Step four picked issue #4, which was the
only open issue labelled `night`. Its body has no `Answers` section. The branch `claude/issue-4` did
not exist on origin and was created from `main`.

Two commits. The first carried the module and its tests and was pushed straight away, which
published nothing because the two pull request files still carried the text of the run before this
one. The second carried the decision record, the index row and the README lines. This push carries
the text of this run and is the last one.

What I did not do. Nothing renders a reply outside the domain yet, because there is no adapter and
no command line to call it from, and those are issues #6 and #5. No example catalog was added, so
fence four still reads no product names. Nothing was changed in the fences, the gates or the
workflows.

The gates took about one and a half seconds per run, most of it the suite, and were run before each
commit. The suite alone takes about one second. `python -m pip install -e ".[dev]"` fails on this
machine because the default interpreter is Python 3.11 and the project asks for 3.12 or later, so
`pytest` was installed for it on its own and the suite was run again under 3.12 and 3.13 in
throwaway environments. The commit identity of the clone was set to the GitHub noreply address the
gate asks for before the first commit, because the clone arrived with another one.
