# 3. A score is decimal arithmetic over three bounded dimensions

Status: accepted
Date: 2026-09-18

## Context

The model is not allowed to say how good a lead is. Three things about a lead are already written
down somewhere in this shape of the problem. What the person asked about has a price in the catalog.
What they bought before is a history. What each product leaves behind is a margin. A score over
those three is arithmetic, and arithmetic can be pinned by a test.

That leaves the arithmetic itself, and the first version of this module got it wrong in a way worth
recording. It added prices as floats and rounded with the rounding of the language. Two things
followed. The order the products were named in moved the score, because float addition is not
associative. With three products priced at 352.23, 746.07 and 464.20, one order gave a revenue of
0.313 and another gave 0.312. A tie fell one way or the other depending on which parts produced it,
because a half in binary is rarely the half that was typed. Over fifty thousand leads priced to the
cent, the published total disagreed with the total a reader works out from the published parts in
about one case in six.

Two more questions had to be settled. What a dimension means when the data is thin, since most leads
have no history at all. And whether a lead with nothing to score gets a zero or gets refused.

## Decision

`src/fenced/domain/scoring.py` computes three dimensions, each a pure function of what is passed in
and each a number between zero and one at three places.

Revenue is the basket the lead asked about, divided by `FULL_REVENUE`. Recurrence counts the orders
past the first, divided by `RECURRENT_AT` minus one, so an empty history and a single order both
score zero, because one order is not yet a habit. Margin is the plain mean of the margins of what
was asked about.

The arithmetic is decimal. A price arrives as the number a reader sees, read through the text a
float prints as. Decimal addition of those numbers is exact, so the order the products were named in
cannot move a score. The tie rule is written down as half going up rather than left to the language.
The calculation runs in a decimal context belonging to this module, so a caller who has changed the
context of the process changes nothing here.

The total is not rounded. It is the weighted sum of the three published dimensions, exactly, so a
reader who multiplies the parts by the weights and adds them gets the number that was published and
not a number near it. The parts stay next to the total in a frozen `Score`, because a total on its
own says a lead is worth a number and not why.

The weights are 0.5, 0.2 and 0.3, and the tests pin each one against a literal rather than pinning
their sum. A sum test alone accepts a negative weight, and a negative weight makes the better lead
score lower. A second test raises each dimension in turn and asserts the total never falls.

`FULL_REVENUE` caps a basket, and that is all it does. A single product priced at or above it wins
the revenue dimension on its own. That is a decision the catalog makes and not one this module can
take back, and a test pins it so nobody reads the ceiling as a protection it is not.

A lead that names no product is refused with `NothingToScore` rather than scored zero. A name that
is not written text, a price or a margin that is not an amount, a product missing from a table, and
a history that is not a sequence of written orders are each refused by the class whose docstring
covers them. Every refusal is a `ScoreError`, which is a `ValueError`.

Four other shapes were considered and rejected. Weighting the margin by price, which would let
revenue count a second time under another name. Keeping floats and sorting the names before adding,
which settles the order and leaves the tie. Rounding the total a second time, which is what made the
parts stop adding up. Putting the weights in a configuration file, which would let policy change
with no review and no red test.

## Consequences

A score is reproducible. The same catalog, history and margin table give the same number on any
machine, in any order, under any decimal context a caller has set, with no network, no clock and no
file. That is what keeps the tests short and what lets a person check a score by hand.

The price of it is that a score is a `Decimal` and not a `float`. Everything that reads a score has
to accept that, and a caller that wants a float has to ask for one and accept what floats do.

An integer too large for a float is now an ordinary number here, because decimal conversion does not
overflow where `float()` did. A catalog that carries one is scored rather than crashed on.

A refused lead has to be handled by the caller instead of arriving as a low score. That is the point
of the refusal. An unknown lead and a bad lead read the same once they are both a zero, and the
person deciding needs to tell them apart.

The rule stays deliberately coarse. It knows nothing about when a message arrived, how long a
customer has been away, or how much of the history is recent. Each of those is a real dimension and
each one needs its own record and its own data, not a quiet extra term in this sum.
