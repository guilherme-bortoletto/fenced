# 7. A private term is read across the whitespace that hides it

Status: accepted
Date: 2026-09-18

## Context

The `pre-commit` hook in the clone reads the staged diff three ways, raw, with whitespace
collapsed, and with added lines squeezed, because a term written across a line break walked past
the plain read.

`scripts/gates.py --text` read a file one way, one line at a time. Measured against a term from the
list:

    the whole term on one line       refused
    the term split by a line break   passed
    the term split by a space        passed

That is the wrong way round. `AGENTS.md` points at `--text` for the body of an issue and the body
of a pull request, which are public text no commit hook ever sees. So the one gate with nothing
behind it was the one that missed, while the hook guarding commits, which runs this same gate, did
not.

A line break inside a term is not rare or clever. An editor wraps a paragraph, a body is pasted
from a column of a different width, a term sits at the end of a line. Nobody has to try.

## Decision

Each term is matched against three views of the same text.

| View | What it is for |
|---|---|
| the text as it stands, one line at a time | a term written with whitespace inside it |
| every run of whitespace turned into one space | a term of two words written across a line break |
| every run of whitespace taken out | a term of one word broken by a line break or by a space |

A match in any view is a refusal. It is reported at the line the match starts on, and a term found
more than once on a line is reported once, so the output stays one line for one place to look.

How much is collapsed is all of it. Every run of whitespace, of any kind and any length, across
line breaks and blank lines, over the whole text and not only inside a paragraph. Nothing else
about the text is changed. Case was already ignored and still is.

The views are built once per file and used for every term, and both routes into the gate, a file
named on the command line and a tracked file in the default run, go through the one function that
builds them.

## Consequences

A collapsed view has fewer boundaries than the text it came from, so it matches more. That is the
price and it is worth naming exactly.

A short term matches inside two ordinary words once the whitespace between them is gone. With
`sonar` on a list, the line "the person arrived" is refused, because the space that kept `person`
and `arrived` apart is the space the third view removes. The single space view joins paragraphs, so
a term of two words is refused when the first word ends one paragraph and the second opens the
next.

The trade is right because the two mistakes are not the same size. A false refusal costs one look
and one rewording by the person who wrote the text, in front of them, before anything is published.
A missed term is a private word published under a name, and GitHub keeps what it was given.
A gate that refuses too much is annoying. A gate that refuses too little is decoration.

Requiring a word boundary around a match was considered and rejected. Once the whitespace is gone
there is no boundary left to require, and a term broken by a line break is exactly the case that
has none.

Keeping only a line break view was considered and rejected. It closes half of the measurement
above and leaves a term written with a space inside it passing, which is the same hole with a
different keystroke in it.

A term short enough to appear inside ordinary words is now a cost the list carries. That is where
it is fixed, by writing the term long enough to be itself, and the list is not in this repository,
so this record is the only place the shape of that cost is written down.

Nine tests plant the cases. The term across a line break, the term with a space inside it, a term
of two words across a line break, one report for a line the term is written on twice, text holding
no term at all, a tracked file read the same way as a file given by name, the route from a list
written for the test through `FENCED_TERMS_FILE`, the line number each view reports, and the false
match above, planted so that it is a decision and not a surprise.

Every term in those tests is a word invented for them. Planting a real one to prove the gate
refuses it would publish the term.
