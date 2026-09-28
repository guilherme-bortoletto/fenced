"""The step and the window for each of the five levels, and what the table refuses."""

from __future__ import annotations

import dataclasses

import pytest

from fenced.domain.lead import Awareness, UnknownAwareness
from fenced.domain.playbook import PLAYBOOK, Action, Step, next_step, window_hours

EXPECTED = {
    "unaware": (Action.NAME_THE_PROBLEM, 72),
    "problem_aware": (Action.ASK_WHAT_WAS_TRIED, 48),
    "solution_aware": (Action.SEND_THE_COMPARISON, 24),
    "product_aware": (Action.OFFER_A_CALL, 8),
    "ready_to_buy": (Action.HAND_TO_A_PERSON, 2),
}


# The table covers the five levels and nothing else.


def test_every_level_of_awareness_has_a_row_and_no_row_is_anything_else():
    assert set(PLAYBOOK) == set(Awareness)
    assert len(PLAYBOOK) == 5


@pytest.mark.parametrize(("level", "expected"), sorted(EXPECTED.items()))
def test_each_level_answers_with_the_step_the_table_writes_down(level, expected):
    action, hours = expected
    assert next_step(level) == Step(action=action, window_hours=hours)
    assert window_hours(level) == hours


def test_each_action_is_used_once_so_no_two_levels_read_the_same():
    used = [step.action for step in PLAYBOOK.values()]
    assert sorted(action.value for action in used) == sorted(action.value for action in Action)
    assert len(set(used)) == len(used)


def test_a_window_shortens_as_awareness_rises():
    windows = [PLAYBOOK[level].window_hours for level in Awareness]
    assert windows == sorted(windows, reverse=True)
    assert len(set(windows)) == len(windows)


def test_a_window_is_a_whole_number_of_hours_and_never_zero():
    for step in PLAYBOOK.values():
        assert isinstance(step.window_hours, int)
        assert not isinstance(step.window_hours, bool)
        assert step.window_hours > 0


# How a level arrives.


@pytest.mark.parametrize("level", list(Awareness))
def test_a_level_is_read_the_same_way_the_boundary_reads_one(level):
    assert next_step(level) is next_step(level.value)
    assert next_step(level) is next_step(f"  {level.value.replace('_', ' ').upper()}  ")


@pytest.mark.parametrize("invented", ["very_aware", "", "5", None, 3, ["unaware"]])
def test_a_sixth_level_never_reaches_the_table(invented):
    with pytest.raises(UnknownAwareness):
        next_step(invented)
    with pytest.raises(UnknownAwareness):
        window_hours(invented)


def test_the_answer_is_the_same_every_time_it_is_asked_for():
    assert next_step("ready_to_buy") == next_step(Awareness.READY_TO_BUY)
    assert window_hours("ready_to_buy") == 2


def test_a_step_does_not_change_afterwards():
    step = next_step(Awareness.UNAWARE)
    with pytest.raises(dataclasses.FrozenInstanceError):
        step.window_hours = 1
