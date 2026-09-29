# 16. A reply is a template of typed fields, and every number in it names the field it came from

Status: accepted
Date: 2026-09-29

## Context

The model turns free text into fields. `docs/adr/0002` closed awareness and made the boundary in
`lead.py` refuse rather than coerce, so everything past that boundary has a type the rest of the
domain can rely on. What was still open is the other direction, which is the sentence that goes back
out to the person who wrote.

A model that writes the reply writes a price it read in a message, a date nobody promised and a name
nobody assigned. None of those three is a bug a test can catch, because the text is different every
time and a test cannot read a sentence. The three of them are also the three decisions the README
already says the model does not get to make.

The other shape is a template with the values filled in, which is ordinary code. That only helps if
the values cannot come from anywhere. A template filled from a mapping of strings is a template that
carries whatever the caller had, and the caller is a step away from what the model returned.

So the question was how a value proves where it came from, and what happens to a number nobody can
answer for.

## Decision

`src/fenced/domain/reply.py` holds one template for each action the playbook names, and renders a
template from typed fields.

A field is a frozen `Field` with a name, the text it renders as, and the `Source` that built it.
`Source` is closed at three values, which are the catalog, the matching and the playbook. A table in
the module maps each field name to the one source allowed to build it, and the constructor refuses a
field that names any other. A name the table does not carry is refused there as well, which is what
it means for a field the domain cannot type not to exist.

The five builders are the only route a field is made by in this repository, and none of them takes
text from a caller. `product` and `price` read a row of the catalog and return what the catalog holds,
including the spelling of the product name. `quantity` counts the products the catalog carries.
`seller` reads the name off the `Seller` the match picked and refuses anything that is not one.
`window` reads the hours off the playbook. A caller who wants a value in a reply has to have a source
that produces it.

The last rule reads the rendered text. Every run of digits in it has to sit inside the text some
field produced, and a run that does not is `UnsourcedNumber`. The check reads runs of digits and not
shapes, so a date and a quantity pass because they came from a field and not because either one has a
rule of its own. A number written into a template is refused, and a test reads every template back to
assert none of them carries a digit at all.

A template that names a field nothing supplied is `MissingField`, and a field the template has no
place for is `UnusedField`. Neither renders. A hole in a reply and a value that silently went nowhere
are both a mistake in the caller, and a reply is text that leaves the building.

`reply` picks the template by the action the playbook gives for a level of awareness, and builds the
window field itself from that same level. So the hours in the text and the action behind them cannot
disagree, and a window passed in is refused rather than replaced.

## Consequences

The reply is text a test can read. A template is a constant, the fields are typed, and the check on
numbers is four lines, so a price that came from a message cannot reach a person without a red test
first.

The price is that a reply is not written for the person. Five templates are five sentences, and a
shop that wants warmth, a subject line or a second language wants more than a table of five. Each of
those is a template and a test, which is the shape this decision commits to.

A reply names nobody. A name is what the person wrote, and the person who wrote is not one of the
three sources, so the templates address no one by name. Whatever sends the reply owns the greeting,
where a name is a field of a lead and not a value in a rendered sentence.

The fence is the constructor and the builders, not the language. Nothing stops a caller from building
a `Field` by hand with a source that is allowed to hold that name, the same way nothing stops a caller
from building a `Lead` by hand. What is stopped is the value that claims the wrong source, the name no
source owns, and the number no field produced. The builders are where the text actually comes from,
and they read a catalog, a `Seller` and the playbook table and nothing else.

The catalog is read a second time here, next to the reading in `scoring.py`. The two refuse the same
way and raise their own errors, because a reply that failed to render is not a score that failed to
add up. A shared reader would tie the two modules together for four lines.
