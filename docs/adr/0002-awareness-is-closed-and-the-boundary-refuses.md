# 2. Awareness is a closed set and the boundary refuses instead of coercing

Status: accepted
Date: 2026-09-18

## Context

The model reads free text and returns a mapping of fields. Those fields cross into the domain, and
two questions had to be answered before any rule could be written on top of them.

The first is what shape a level of awareness has. An open string means every module that branches on
it has to carry an else, and the else is where a level nobody planned for goes to hide.

The second is what happens to a field of the wrong type. A model returns JSON, and JSON has a null.
Python will turn that null into the string "None" without complaining, and a lead named None reads
as a real name to everything downstream.

## Decision

Awareness is an enum of five values and nothing else. `Awareness.parse` forgives case, spacing,
hyphens and underscores, because those are spelling. It refuses a sixth level, because that is
meaning. A test asserts the list is exactly those five, so adding one is a deliberate act with a red
test behind it.

The constructor of `Lead` is the only boundary. It refuses any required field that is not text,
rather than calling `str` on it. Building a lead from a mapping and building one directly run the
same refusals and the same trimming, so there is one rule and not two that drift apart.

The address check is deliberately shallow. It refuses a missing local part, a host with no dotted
name, more than one at sign, and any space or control character. It does not try to decide what a
mail server will accept, because that is not a rule this domain owns. The control character refusal
is not cosmetic, since that is how a header gets smuggled into whatever sends the reply.

## Consequences

A branch over awareness is total, and the playbook can be written without a default case.

A null, a number or a list in a required field ends the lead at the door with a `MissingField`,
which is a `LeadError`, which is a `ValueError`. Every refusal a caller can get is in that one
family.

The cost is that an extractor with something more to say has nowhere to put it. A confidence, a
second best level, or a reason for the pick all need a field this shape does not have. When one of
them is actually needed, it gets its own record rather than a quiet widening of the enum.
