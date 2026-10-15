# 20. The model returns fields and nothing else

Status: accepted
Date: 2026-10-14

## Context

The README says the model reads free text and decides nothing. Record 0016 already holds the
outgoing half of that. A reply is a template filled by typed fields, and every number in it names
the source that built it. The model is not one of those sources, so it never writes a sentence
that goes back to a person.

What record 0016 leaves out is the incoming half. It does not say why the model is asked for
fields at all, rather than for a summary, a score or a draft that a person checks. And it does not
say what happens when the model answers with something that is not the fields it was asked for.
Both questions sit in `src/fenced/adapters/llm_extractor.py`, which is the only file in `src` that
names a provider.

## Decision

The model is asked for three fields, a name, an address and one of the five levels of awareness,
and for nothing else.

A field is something the rest of the code can refuse. A name and an address are text the boundary
in `src/fenced/domain/lead.py` trims and checks. A level of awareness is one of a closed set, as
record 0002 says. A summary, a score or a draft is none of that. A test cannot read it, the
boundary cannot refuse it, and the next step would have to trust it. So the model is kept to the
one job a rule cannot do, which is reading a message written in whatever way a person writes, and
every decision after that is a written rule in the domain.

The prompt is one constant, `SYSTEM_PROMPT`, and the fourth fence reads it, so a price, a product
or a person cannot reach the model through it. The request carries a JSON schema with the three
fields, the five levels as an enum, and no other property allowed. The model is not asked to copy
the message back. The command line puts the text from the inbox under `message` itself, whatever
the extractor returned under that name, because a copy is a chance to change it.

An answer that is not the fields is refused at one of two places.

The extractor refuses an answer it cannot read as fields at all. An answer that is not JSON, that
is not an object, that stopped for any reason other than finishing its turn, that carries no text,
or whose text is not a JSON object is `ExtractionFailed`. That is a kind of `LlmError`, and the
command line stops the run on it before the plan is made, so nothing is written.
`test_the_model_extractor_refuses_an_answer_that_is_not_three_fields` plants seven of those
answers, including a refusal by the model and an answer cut off by its token limit.

The extractor does not check which keys came back, and it coerces nothing. That is the job of
`Lead.from_fields`, which every answer crosses before anything else reads it. A missing field, a
field that is not text, a blank field, an address that cannot be reached, and a level that is not
one of the five are each a `LeadError`. The command line hands that message back by its id with
the reason and goes on with the rest. A key the boundary does not ask for is never read, so an
extra field the model adds goes nowhere.

## Consequences

The model can be wrong about a field, and the code cannot tell. A name it misread is a valid name
and a level it misjudged is a valid level. What it cannot do is put a price, a date or a promise in
front of a person, because no field it returns reaches a reply, and record 0016 refuses a number
no source produced.

The two places refuse differently on purpose. An answer that is not fields says something is wrong
with the provider or the request, and that is true for the next message too, so the run stops. An
answer that is fields the boundary refuses says something about one message, so that message is
handed back and the rest go on.

Asking for more means a field of its own. The products a person asked about and the language they
wrote in are not returned today, as record 0019 says, and each one is a property in the schema, a
type the boundary checks, and a decision about what a wrong value costs.

Record 0024 adds the products, the language and the segment as fields of their own, and says what
each one costs when the model gets it wrong.
