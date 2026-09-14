# 1. Architecture rules live in tests

Status: accepted
Date: 2026-09-14

## Context

Every project this size writes its rules in a README. Six months later the README still says the
domain is pure and an HTTP client has been sitting in it for four months. Nothing ever checked, so
nothing ever failed. The rule was a preference, and a preference loses to whatever is quicker on a
Tuesday afternoon.

Tools exist for this. import-linter, pytest-archon and tach all read a configuration file and refuse
a forbidden import. They are the right answer for a code base with many teams in it.

## Decision

The rules of this repository are ordinary tests in `tests/test_fences.py`, written by hand against
the standard library, one function per rule.

Each fence is a function that returns what it found wrong, plus a test that expects nothing. Eight
further tests plant a violation and check that the fence refuses it, at least one for each fence.

The suite runs in CI on every push, and again before every commit an agent makes here. When a fence
is wrong, it changes through a new decision record and a pull request of its own, never inside the
change that it was blocking.

## Consequences

A reader sees the rule and the check that enforces it on one screen, without learning a
configuration language first. That is the point of this repository, so the cost of writing them by
hand is the product, not overhead.

The fences are naive. The import fence reads the import graph and nothing else. The provider fence
is a text search, which is blunt and will one day refuse a sentence that was innocent. The secret
fence knows the shapes of the keys listed in it and no others, which is why push protection and
secret scanning are turned on the moment this repository becomes public.

When this stops fitting on one screen, the right move is to adopt import-linter and delete the
hand written version. That will be its own record.
