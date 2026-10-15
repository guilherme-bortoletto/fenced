# 25. A lead nobody can take is still written to the store

Status: accepted
Date: 2026-10-15

## Context

Issue 53 puts scoring and matching on the path of the command line. For each lead a run now prints
the score with its three parts and its total, and the seller `matching.match` picks. Some leads
come out of that with a refusal instead. `NobodyEligible` says no seller covers the segment, the
ticket and the language of the lead. `UnknownProduct` says the person asked about a product the
catalog does not carry. `NothingToScore` says they named no product at all.

The issue asked for a decision on whether such a lead is still written to the store.

## Decision

It is. Every lead the boundary in `Lead.from_fields` accepts is planned and written as before,
whatever scoring and matching answer about it.

A lead nobody can take is the lead a person most needs to see. A segment no seller covers is a
hiring problem or a routing problem, and record 0014 keeps the two refusals apart so a person can
tell which. Dropping the lead would hide both. The same holds for a product the catalog does not
carry, which is either a gap in the catalog or a misreading of the message, and for a person who
named no product, who still wrote and still has a next step.

The record keeps the same fields as before. The score, the ticket and the seller are printed and
not stored. A score is computed from three tables that change, so a stored score goes stale the
day a price moves, and the next run computes it again from the tables as they stand.

Scoring and matching each refuse in two ways. A refusal about the lead, which is one of the three
above, is printed under that lead by the name of its class, and the run goes on. A refusal about a
table, such as a price that is not a number or a roster that carries one name twice, stops the run
with nothing written, because it would repeat under every lead and says nothing about any of them.

## Consequences

The store holds the same leads after this change as before it, so a run over the examples writes
seven records and its undo takes seven away.

A person who wants to find the leads nobody can take reads the run and not the store. Keeping the
seller or the refusal in the record is a decision for the step that first needs to read it back.
