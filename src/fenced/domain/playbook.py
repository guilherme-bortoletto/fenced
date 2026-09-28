"""What happens next, for each of the five levels of awareness.

A table and the two lookups that read it. For every level `Awareness` closes there is
one action and one window, and the pair is what a caller gets back. A sixth level does
not reach the table, because the level is parsed the same way the boundary parses it
and a sixth level is refused there.

The window is a number of hours counted from the message the person wrote, and not a
time of day. A time of day needs a calendar, a clock and a place, and none of the three
is an argument of a pure function. So what the person said sets how long the window is,
and whatever sends the reply is free to hold it until the morning.

The windows shorten as awareness rises. Somebody who has said they are ready to buy is
written back inside two hours and somebody who does not yet know they have a problem is
written back inside three days. That order is the rule, and a test reads it back.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from fenced.domain.lead import Awareness


class Action(Enum):
    """The actions this playbook can name, closed the way the levels are closed.

    A caller branches on one of these. A free line of text would read the same to a
    person and mean nothing to the code, and nothing downstream could be tested on it.
    """

    NAME_THE_PROBLEM = "name_the_problem"
    ASK_WHAT_WAS_TRIED = "ask_what_was_tried"
    SEND_THE_COMPARISON = "send_the_comparison"
    OFFER_A_CALL = "offer_a_call"
    HAND_TO_A_PERSON = "hand_to_a_person"


@dataclass(frozen=True)
class Step:
    """The next step and the window it happens in.

    The two travel together because either one alone is half an instruction. An action
    with no window says what to do and not when, and a window with no action says when
    and not what.
    """

    action: Action
    window_hours: int


# The playbook itself, written out level by level so a reader argues with the table and
# not with the code. Every level of `Awareness` has a row, and a test reads that back.
PLAYBOOK: Mapping[Awareness, Step] = {
    Awareness.UNAWARE: Step(Action.NAME_THE_PROBLEM, 72),
    Awareness.PROBLEM_AWARE: Step(Action.ASK_WHAT_WAS_TRIED, 48),
    Awareness.SOLUTION_AWARE: Step(Action.SEND_THE_COMPARISON, 24),
    Awareness.PRODUCT_AWARE: Step(Action.OFFER_A_CALL, 8),
    Awareness.READY_TO_BUY: Step(Action.HAND_TO_A_PERSON, 2),
}


def next_step(awareness: object) -> Step:
    """The step for one level of awareness, with the level parsed before it is read.

    Parsing here rather than trusting the caller keeps one rule about what a level is.
    A level written as text arrives at the right row, and anything that is not one of
    the five raises `UnknownAwareness`, which is the refusal the boundary already uses.
    """
    return PLAYBOOK[Awareness.parse(awareness)]


def window_hours(awareness: object) -> int:
    """How long the window is for one level, in hours from the message.

    A caller that only has to know when reads this instead of taking the step apart.
    """
    return next_step(awareness).window_hours
