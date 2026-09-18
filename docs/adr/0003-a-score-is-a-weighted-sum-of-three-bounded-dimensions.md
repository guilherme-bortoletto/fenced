# 3. A score is a weighted sum of three bounded dimensions

Status: accepted
Date: 2026-09-18

## Context

The model is not allowed to say how good a lead is. That leaves the question of what does say it,
and a number that comes out of nowhere is no better than a number that comes out of a model.

Three things about a lead are already written down somewhere in this shape of the problem. What the
person asked about has a price in the catalog. What they bought before is a history. What each
product leaves behind is a margin. Those three are data, so a score over them is arithmetic and can
be pinned by a test.

Two questions had to be settled before any of it could be written. The first is what a dimension
means when the data is thin, since most leads have no history at all. The second is whether a lead
with nothing to score gets a zero or gets refused.

## Decision

`src/fenced/domain/scoring.py` computes three dimensions, each a pure function of what is passed in
and each a number between zero and one.

Revenue is the basket the lead asked about, divided by `FULL_REVENUE`, the basket that already wins
the dimension. It stops at one, so one large product cannot decide a score by itself.

Recurrence counts the orders past the first, divided by `RECURRENT_AT` minus one. An empty history
scores zero and so does a single order, because one order is not yet a habit. A past order naming a
product the catalog no longer carries still counts, because it happened.

Margin is the plain mean of the margins of what the lead asked about. It is not weighted by price,
because weighting by price would let the revenue dimension count a second time under another name.

The total is the weighted sum under `WEIGHTS`, which add up to one and are written in the module so
a reader argues with the numbers rather than with the code. Every dimension is rounded to three
decimal places, so a test can pin a score and float noise never separates two equal ones. The three
parts are kept next to the total in a frozen `Score`, because a total on its own says a lead is
worth a number and not why.

A lead that names no product is refused with `NothingToScore` rather than scored zero. A price or a
margin that is not an amount, a product missing from a table, and a history that is not a list of
written orders are refused in the same way. Every refusal is a `ScoreError`, which is a
`ValueError`.

## Consequences

A score is reproducible. The same catalog, history and margin table give the same number on any
machine, with no network, no clock and no file, which is what makes the tests short.

The weights and the two ceilings are policy, and policy that lives in a module changes with a
commit, a review and a red test when someone gets it wrong. Moving them into a configuration file
would make them changeable without any of that, so they stay here until there is a reason.

A refused lead has to be handled by the caller instead of arriving as a low score. That is the point
of the refusal. An unknown lead and a bad lead read the same once they are both a zero, and the
person deciding needs to tell them apart.

The rule is deliberately coarse. It knows nothing about when a message arrived, how long a customer
has been away, or how much of the history is recent. Each of those is a real dimension and each one
needs its own record and its own data, not a quiet extra term in this sum.
