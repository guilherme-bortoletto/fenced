# 14. A seller is picked by three hard rules and a written order

Status: accepted
Date: 2026-09-28

## Context

The model is not allowed to pick who takes a lead. Three things about a seller are already written
down in this shape of the problem. Which segments they cover, which ticket sizes they work in, and
which languages they speak. A lead that fails any of the three is a lead that seller cannot take, so
those three are a filter and not a preference.

The filter is the easy half. The hard half is that it usually leaves more than one seller standing,
and something has to choose between them. The first version of this module returned the first
eligible seller in the roster it was handed. That read as deterministic and was not. The roster
arrives from a caller, the caller reads it from somewhere, and the order of a list of people is the
order somebody typed them in. A test could pin the answer only by pinning the input order, which
means the test pins the typing and not the rule. Worse, the same roster loaded two ways gave two
answers, and neither one was wrong in a way anybody could point at.

A load count would settle it, and would be a better rule than any of the ones below. It is also a
number that changes while nobody is looking, which makes it an argument this module has to be handed
rather than a fact it can read, and nothing in this repository yet counts what a seller is holding.

Two other questions had to be settled. Whether a roster with nobody in it and a roster where nobody
fits are one answer or two. And what to do about two sellers with one name, since a rule that ends
in a name needs the name to be unique to end at all.

## Decision

`src/fenced/domain/matching.py` filters on the three rules, then puts what is left in an order
written down in the module.

The order asks four questions in turn. How many segments does this seller cover, so that a seller
who covers one segment comes before a seller who covers six. How wide is their ticket range. How many
languages do they speak. Then the name, read without its case. The first question whose answers
differ decides, and the fourth one always differs, so the order is total. A total order is what makes
the answer the same for the same sellers in any order they arrive in, which is the property the first
version lacked.

The first three questions are the three hard rules asked a second time. The filter asks whether a
seller covers the rule at all, and the order asks how narrowly they cover it. So the order of the
questions is the order of the rules, and one reason covers the whole key, which is that the more
particular seller goes first.

An earlier version of this module asked the first two and left the language out. That put a seller
who speaks one language and a seller who speaks five side by side with nothing between them but the
alphabet, under a reason that had already answered the other two questions. Nothing argued for
treating a language differently. It is read by the same fold, held in the same constructor and
already asked by `covers`, and a seller who speaks one language is the more particular seller the
same way a seller who covers one segment is. Leaving it out was an omission and not a choice, and
this record is the place that has to tell those two apart.

That the more particular seller goes first is a choice and not a fact. A shop can reasonably want the
opposite. It is written in one function, `order`, and pinned by its own tests, so changing it is one
edit and one red test rather than an argument about behaviour nobody can find in the code.

`eligible` returns the whole ranked list and `match` returns its first entry. The list is the working
of the pick. A person who asks why a lead went one way reads it and sees who else could have taken
the lead and in what order, instead of being told a name.

An empty roster is `NobodyToMatch` and a roster where nobody fits is `NobodyEligible`. Read as one
refusal they both look like nobody is free, and the person deciding has to tell a hiring problem
apart from a routing problem. Two sellers whose names fold to the same text are `InvalidRoster`,
refused rather than picked between, because the name is the last step of the order and a step that
cannot settle a tie is not an order.

Segments and languages are folded to one case, because case is spelling and not meaning, which is
the rule `docs/adr/0002` already set for awareness. A name keeps the case it was written in and is
folded only where it is compared. A ticket is read the way a price is read in
`docs/adr/0003`, through the text a float prints as, and the one subtraction this module does runs
in a decimal context of its own so a caller cannot narrow two ticket ranges into one width.

## Consequences

A pick is reproducible. The same sellers give the same seller, in any order, on any machine, with no
clock, no file and no service. The tests permute a roster and assert one answer, which is a test the
first version could not have passed.

The price is that the order encodes a policy. A seller who covers one segment, works in one narrow
range and speaks one language is preferred, and nothing about the problem proves that is right. A
shop that hired a person to speak five languages may well want that person reached first. The policy
is visible and it is one function, which is the most this module can offer.

A dimension the filter asks about is a dimension the order asks about. That is the rule this record
now carries, and it is what makes a fourth question a change to the policy rather than a gap in it.
A dimension the filter does not have is a different matter, and the paragraph below names three.

The rule still knows nothing about how much work a seller is already holding, about who spoke to
this person last, or about anybody being away. Each of those is a real dimension, and each one needs its
own record and its own data rather than a quiet extra question in `order`.

A roster cannot carry one name twice. A shop with two people called the same thing has to write the
names apart before the roster reaches the domain, which is where a person can see that it happened.
