# 15. A return window is hours from the message and not a time of day

Status: accepted
Date: 2026-09-28

## Context

Awareness is closed at five levels by `docs/adr/0002`, and the point of closing it was that what to
do at each level is a written rule somewhere else. This is that somewhere else. Each level gets one
action and one window to do it in.

The window is the part that needed deciding. The obvious shape is a time to reply by, which is what a
person actually wants to read. A time to reply by needs three things this module cannot have. A
clock, because the window is counted from now. A calendar, because Saturday is not Monday. A place,
because six in the evening is not the same hour everywhere. `docs/adr/0005` names a clock as a door,
and fence one refuses the import, so a module that returns a deadline is a module that cannot live in
`domain/`.

The other half of the same question is whose hours the window belongs to. A window that bends around
opening hours is a window about the shop. The issue this module was built for asked for the opposite,
which is a window that comes from what the person wrote.

## Decision

`src/fenced/domain/playbook.py` holds a table from each of the five levels to a `Step`, which carries
an `Action` and a number of hours.

The number is hours counted from the message the person wrote. It is not a deadline and it is not a
time of day. Whatever sends the reply owns the clock, the calendar and the place, and is free to hold
a window until the morning. That keeps this module a pure function of one argument, and it keeps the
question of what a working hour is out of the domain entirely.

The windows are 72, 48, 24, 8 and 2, shortening as awareness rises. Somebody who has said they are
ready to buy is written back inside two hours, and somebody who does not yet know they have a problem
is written back inside three days. A test reads the five numbers back in the order of the levels and
asserts each one is shorter than the last, so a window edited out of order turns the build red.

The action is a closed `Action` and not a line of text. A caller has to branch on what happens next,
and a sentence reads the same to a person while meaning nothing to the code. Each of the five actions
is used exactly once, which a test pins, because two levels that answer the same are four levels
wearing five names.

The level is parsed by `Awareness.parse` before the table is read, so a level written as text arrives
at the right row and a sixth level raises `UnknownAwareness`. That is the refusal the boundary in
`lead.py` already uses, and reusing it keeps one rule about what a level is rather than two.

The table is read directly, with no branch for a level it has no row for. A test asserts the keys of
the table are exactly the five levels. A defensive refusal there would be a line no test could reach,
in a repository where the rules are the tests.

## Consequences

The next step for a lead is a lookup with no clock in it, so it is the same answer on any machine at
any hour, and the tests are five assertions rather than a frozen clock.

The price is that nothing here answers the question a person actually asks, which is what time to
reply by. Turning a window into a time is real work about calendars and time zones, and it belongs to
whatever sends the reply, where a test can be given a clock on purpose.

A window is coarse. It knows the level and nothing else. It does not know how large the ticket is, how
long this person has been a customer, or whether they have written three times this week. Each of
those would change the window, and each one needs its own record.

The five numbers are policy in code. Changing one is a commit and a review, which is the point. A
shop that wants them in a configuration file wants them changed with no red test, and that is the
shape this repository refuses.
