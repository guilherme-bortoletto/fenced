Closes #35

## What

`readme_problems` in `tests/test_fences.py` reads the README back against the file it describes.
Each fence carries the rule of its row on the line under its heading, so the table and the fences
are paired by a quote rather than by position.

    # Fence 3. A write keeps its plan, its journal and its undo.
    # The row in the README: nothing persists a record outside `writes/`

`test_the_readme_describes_the_fences_the_file_carries` fails on a row no fence quotes, on a fence
that quotes a rule the README has no row for, on a fence that quotes nothing at all, on two fences
quoting one row, on a check no planting test ever called, and on a count the README writes that the
file does not hold.

Every test that builds a tree carries a mark saying which kind it is. `plants` is a tree a check has
to refuse and `admits` is a tree it has to accept. Both are registered in `pyproject.toml`, and
`--strict-markers` turns a mark nobody registered into an error.

The counts in the README come off the file now. Six rules, eight checks, thirty four tests that
plant a tree a check has to refuse, and two tests that plant a tree it has to accept. The old
sentence said twenty seven tests that plant a violation and expect a refusal, and two of those
twenty seven planted nothing wrong.

A number is written as words in that sentence, so `spelled` renders what the file holds in the same
spelling and the two are compared as text.

## Why

The README claimed six rules, seven checks and twenty seven planting tests, and nothing read any of
it. The counts were right because whoever moved one updated the sentence by hand. That is discipline
and not a fence, and this repository says its architecture is enforced by tests and not by the
README.

The obvious thing to count is the `tmp_path` parameter, and the issue says why it is not a
definition. A parameter says a test was handed a temporary folder. It says nothing about what the
test wrote there or what it expects back. Counting it gives a number that is right until a test
takes `tmp_path` for another reason, which is a fence that passes for the wrong reason.

The mark is what the counting is built on and the parameter is what makes a missing mark loud. A
test that takes `tmp_path` and carries no mark fails, so the count cannot drift quietly.

## Tests

Nine tests plant a README and a fence file into `tmp_path` and read the check over the pair. A row
with no fence, a fence with no row, a fence that quotes nothing, two fences quoting one row, a count
that went stale, a planting test with no mark, a test carrying both marks, a count the README
dropped, and a tree with neither file in it.

The check found something on the tree it was written for. Two of the twenty seven tests the README
counted build a tree the fence has to accept, so they are marked `admits` and counted apart.

286 tests pass on Python 3.11, 3.12 and 3.13.

## Decisions I made

The issue offered two roads, a mark on the planting tests or a README that stops counting. I took
the mark. A sentence with no number in it cannot be wrong, and it cannot be read back either, and
record 0010 already settled that the way to close this shape is to write the mapping down and test
that the two agree.

Two marks and not one, because two of the twenty seven tests plant a tree the fence has to accept.
One mark would have counted them with the refusals, which is the error the README already carried.

A check is a function a test asserts returns an empty list. The return annotation would have been
the easy definition and it is the same accident as `tmp_path`, because five helpers in that file
also return a list of strings.

The pairing is a quote and not a number. A row and a fence agree on the words of the rule, so a
reword of either fails the suite until the other is reworded with it.

This is a check and not a seventh fence. It reads the description of the fences and not the
architecture, so the README still counts six rules, and the checks went from seven to eight.

One thing the issue did not ask for. The check also fails when a check has no test that plants a
tree for it, which reads back the README sentence that says a fence nobody ever watched reject
anything is decoration. It is five lines and it sits next to the counting it depends on.

The reason all of this is written down in
`docs/adr/0013-the-readme-is-read-back-and-a-planting-test-says-what-it-plants.md`, with a row in
the index.

## Run notes

Quoting the text rule of `AGENTS.md` before anything else: "No dash used as punctuation and no semicolon, in Markdown or in a docstring. Short sentences. Describe what is there instead of selling it."

What I did. The stall check found the last merge under an hour old and no open pull request from a
`claude/` branch, so nothing was waiting on a person. I took issue 35, the only open issue labelled
night, and read its body and not its comments. Two commits. The first marks the twenty seven
planting tests and registers the marks, and it was pushed right after it was made. The second adds
the check, the counts and record 0013. Then these two files and the push that carries them.

What I did not do. I did not take the second road and drop the counts. I did not touch the door
check or record 0010, which this one is modelled on. I did not renumber the fences and I did not add
a row to the fence table, because the new check is not a rule about the architecture. I did not
count `test_the_tree_has_the_shape_the_fences_assume` as a check, because it asserts a comprehension
and not a call.

I did not run the term rules, because this clone has no list of private terms, so nothing in this
branch proves anything about how a term is matched.

`spelled` writes a number under a hundred. A count of a hundred planting tests would raise rather
than report, which is loud but not a message. I left it, because a branch that closes that case
would carry a test for a number sixty six tests away.

How long the gates took. `python -m pytest` runs 286 tests in 0.5 seconds, and
`python scripts/gates.py` takes 0.9 seconds end to end. The `python3` in this container is 3.11 and
this project asks for 3.12, so `pip install -e ".[dev]"` refused and I installed `pytest` on its
own, then ran the suite again under 3.12 and 3.13 to match the two the workflow uses. No gate was
softened and nothing was skipped.
