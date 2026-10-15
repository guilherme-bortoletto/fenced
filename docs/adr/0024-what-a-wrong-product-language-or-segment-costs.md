# 24. What a wrong product, language or segment costs

Status: accepted
Date: 2026-10-15

## Context

Record 0020 asks the model for three fields and says that asking for more means a field of its own.
Matching in `src/fenced/domain/matching.py` needs a segment and a language, and scoring in
`src/fenced/domain/scoring.py` needs the products a person asked about. None of them was on a lead,
so the command line stopped after the next step. Issue 52 asked for the three, and for a decision
about what each one costs when the model gets it wrong.

The model can be wrong about any field and the code cannot tell. A refusal only catches a value that
is not a value at all. So the question for each field is what a wrong value that looks right does
downstream, and what a refusal does instead.

## Decision

The model is asked for six fields. The three new ones are `products`, `language` and `segment`, and
each is a property of the schema in `src/fenced/adapters/llm_extractor.py` and a check in
`Lead.from_fields`.

The segment is one of five written in `Segment`. A wrong segment sends the lead to a seller who
covers the wrong kind of business, or to nobody, and `NobodyEligible` then reads as a routing
problem when it is a reading problem. The set is closed so that a segment nobody planned for is
refused at the boundary and never reaches matching. A wrong segment that is in the set is not
caught, and the cost is a lead that a person has to move to another seller.

The language is one of six two letter codes written in `Language`. A wrong language is the costliest
of the three, because it is the one the person sees. The reply goes out in a language they did not
write in, or a seller who cannot read them takes the lead. So the schema lets the model answer with
an empty string when the message is in none of the six, and the boundary refuses that. A guess at the
nearest language the set accepts is what the empty string is there to prevent.

The products are names as the person wrote them, trimmed and each kept once in the order named. An
empty list is a person who named none, and that is still a lead. A bare string, a null among the
names or a blank name is refused rather than dropped, because it says the reading went wrong.
Whether the catalog carries a name is not decided here. A product the person did not name moves the
score of a lead up, and a product the model missed moves it down. Neither moves a price, because
every price comes from the catalog. A name the catalog does not carry is refused by scoring with
`UnknownProduct`, and is not scored as zero.

A field that is missing, of the wrong type, or outside its set is a `LeadError`. The command line
hands that message back by its id with the reason and goes on with the rest, as record 0020 says.

The fake extractor reads all three by rules written at the top of
`src/fenced/adapters/fake_extractor.py`. A segment is the first row of a table of words. A language
is the row of a table of short common words with the most hits. A product is a run of two or more
capitalised words off the signature lines. A field the rules cannot find is left out, so the default
run needs no key and no network and still meets the same refusals.

## Consequences

A message from a segment or in a language outside the sets is handed back before a seller is picked.
A message in the sets that no seller covers crosses the boundary, and matching refuses it with
`NobodyEligible`. The examples carry two messages meant for that refusal, a clinic in the `health`
segment and a shop that writes in Italian, so the next step has something to refuse.

Adding a segment or a language is a change to an enum with a red test behind it, the way record 0002
says of awareness. The prompt writes every member out by hand, because fence four refuses a prompt
assembled at run time, and a test checks that the prompt names each one.

The store keeps the same record as before. The three fields reach the command line and nothing that
is written. Keeping them in the store is a decision for the step that first needs them there.
