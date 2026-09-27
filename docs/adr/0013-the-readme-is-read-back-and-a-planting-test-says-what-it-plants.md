# 13. The README is read back, and a planting test says what it plants

Status: accepted
Date: 2026-09-27

## Context

The README carries a table of the six fences, one row each, and it counts. Six rules, seven checks,
and twenty seven tests that plant a violation and expect a refusal. Nothing read any of that back.
The counts were right because whoever moved one updated the sentence by hand, which is discipline
and not a fence.

Two of the twenty seven planted nothing wrong.
`test_the_import_fence_reads_a_relative_import_in_a_package_init` and
`test_the_import_fence_still_admits_the_arithmetic_the_domain_is_made_of` build a tree the fence has
to accept, and both were counted with the tests that expect a refusal. The count was already wrong
by two, and the sentence had no way to say so.

The obvious thing to count is the `tmp_path` parameter, because every test that builds a tree takes
it. That is the same accident one level down. A parameter says a test was handed a temporary folder.
It does not say what the test wrote into the folder or what it expects back, so a count built on it
holds until a test takes `tmp_path` for some other reason.

This is the shape of record 0010 one level out. There the record named doors and the lists did not
carry them, and the table closed it by writing the mapping down and testing that the two agree.

## Decision

The description is read back, and what is counted is defined.

Each fence quotes the rule of its row in the README, on the line under its heading.
`readme_problems` reads the rows, the fences, the checks and the tests, and
`test_the_readme_describes_the_fences_the_file_carries` fails on each of these.

- A row the README carries that no fence quotes.
- A fence quoting a rule the README has no row for, and a fence quoting nothing at all.
- Two fences quoting one row.
- A test that takes `tmp_path` and carries no mark, a test that carries both marks, and a mark on a
  test that plants nothing.
- A check no test marked `plants` ever called, because a fence nobody watched reject anything is
  decoration and the README says so.
- A count the README writes that the file does not hold, a count with no number in front of it, and
  a phrase the README dropped.

A check is a function a test asserts returns an empty list. That is read off the assertion and not
off the return annotation, because five helpers in the same file return a list of strings too and
none of them is a check.

A test that builds a tree carries `plants` when the check has to refuse the tree and `admits` when
it has to accept it. Both marks are registered in `pyproject.toml`, and `--strict-markers` turns a
mark nobody registered into an error rather than a warning. `tmp_path` is what makes a missing mark
loud, and the mark is what a count is read off.

A number is written as words, and `spelled` renders the count the file holds in the same spelling,
so twenty five and 25 are one claim.

## Consequences

The README separates the two kinds now, and the tests that plant for this check are nine of the
first number. The sentence that was wrong by two is a test.

A reword of a row fails the suite until the quote under its fence is reworded with it. That is what
quoting buys over pointing, and record 0010 says the same of its two sentences.

Adding a fence costs three lines instead of one. The row, the quote under the heading, and the
count. Adding a test that plants costs two, the test and the count. Both are paid in the commit
that would otherwise have left the README stale.

What this does not do is read whether a row describes what its fence checks. The quote pairs a row
with a fence by name. A row that says the opposite of what its fence does passes, the same way a
door table that forgets a module passes in record 0010.

`test_the_tree_has_the_shape_the_fences_assume` is a check by neither name nor definition. It
asserts a comprehension and not a call, so nothing counts it, which is what it was before.
