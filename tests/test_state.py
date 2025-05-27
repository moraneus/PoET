# tests/test_state.py

import pytest
from model.state import State
from model.event import Event
from model.process import Process
from model.process_modes import ProcessModes


class TestState:
    """
    Test suite for the State class.
    A State represents a frontier (a consistent global snapshot) in a partial order execution.
    This suite tests the complex logic of state transitions and graph construction.
    """

    def setup_method(self):
        """Reset the unique state counter before each test for predictable names (S0, S1...)."""
        State._State__COUNTER = 0

    def test_state_initialization(self):
        """Tests the creation of the very first state (S0)."""
        State(i_processes=[], i_formulas=["p"])
        state = State(i_processes=["-", "-"])
        assert state.name == "S1"
        assert state.enabled is True
        assert "p" in state.now and state.now["p"] is False

    def test_state_propositions_are_collated_from_events(self):
        """Ensures propositions from all events in the frontier are collected."""
        e1 = Event("e1", ["P1"], ["p", "q"])
        e2 = Event("e2", ["P2"], ["r"])
        state = State(i_processes=[e1, e2], i_formulas=[])
        assert state.propositions == {"p", "q", "r"}

    def test_initial_transition_from_iota(self):
        """Tests the first transition from the empty initial state."""
        s0 = State(i_processes=[ProcessModes.IOTA, ProcessModes.IOTA], i_formulas=[])
        event_a = Event("a", ["P1", "-"], i_propositions=[])

        s1, closed_set = s0 | event_a

        assert s1 is not None and s1.name == "S1"
        assert s1.processes == [event_a, ProcessModes.IOTA]
        assert closed_set == set()
        assert s0.processes[0] == ProcessModes.CLOSED

    def test_transition_with_concurrent_event(self):
        """Tests adding a new event that is concurrent to an existing event in the state."""
        e_a = Event("a", ["P1", "-"], i_propositions=[])
        s_a = State(i_processes=[e_a, ProcessModes.IOTA], i_formulas=[])
        e_b = Event("b", ["-", "P2"], i_propositions=[])

        s_ab, _ = s_a | e_b

        assert s_ab is not None
        assert s_ab.processes == [e_a, e_b]

    def test_transition_with_dependent_event(self):
        """Tests a transition where the new event depends on an event already in the frontier."""
        e_a1 = Event("a1", ["P1", "-"], i_propositions=[])
        s1 = State(i_processes=[e_a1, ProcessModes.IOTA], i_formulas=[])
        e_a2 = Event("a2", ["P1", "-"], i_propositions=[])

        s2, closed_set = s1 | e_a2

        assert s2 is not None
        assert s2.processes == [e_a2, ProcessModes.IOTA]
        assert closed_set == {(e_a1, 0)}

    def test_transition_error_on_closed_process(self):
        """Ensures no new state is created for an event on a process that is already 'closed'."""
        s_closed = State(i_processes=[ProcessModes.CLOSED, ProcessModes.IOTA], i_formulas=[])
        event_a = Event("a", ["P1", "-"], i_propositions=[])

        s_new, closed_set = s_closed | event_a

        assert s_new is None
        assert closed_set is None

    def test_predecessor_summary_is_passed_on_transition(self):
        """Verifies that a new state's `pre` dictionary correctly stores its parent's summary."""
        s0 = State(i_processes=[ProcessModes.IOTA], i_formulas=["p"])
        s0.now["p"] = True

        e1 = Event("e1", ["P1"], i_propositions=[])
        s1, _ = s0 | e1

        assert len(s1.pre) == 1
        assert s1.pre[s0.name] == s0.now
        assert s1.pre[s0.name]["p"] is True

    def test_diamond_completion_adds_missing_edge(self):
        """
        Tests the crucial 'diamond completion' logic for concurrent events.
        """
        p1, p2 = Process("P1"), Process("P2")
        e_a = Event("a", ["P1", "-"], i_propositions=[])
        e_b = Event("b", ["-", "P2"], i_propositions=[])
        p1.add_event(e_a)
        p2.add_event(e_b)
        processes_mock = {"P1": p1, "P2": p2}

        s_a = State([e_a, ProcessModes.UNDEFINED], i_formulas=[])
        s_b = State([ProcessModes.IOTA, e_b], i_formulas=[])
        s_ab = State([e_a, e_b], i_formulas=[])

        s_a.edges_completion([s_b, s_ab], processes_mock)

        assert s_ab.name in s_a.successors
        assert s_a.successors[s_ab.name][0] == e_b
        assert s_a.processes[1] == ProcessModes.CLOSED

    def test_diamond_completion_with_multiple_predecessors(self):
        """
        Tests that a state with multiple predecessors (like s_ab) correctly records
        summaries from all of them after transitions.
        """
        s0 = State(i_processes=[ProcessModes.IOTA, ProcessModes.IOTA], i_formulas=["a_done", "b_done"])
        e_a = Event("a", ["P1", "-"], i_propositions=[])
        e_b = Event("b", ["-", "P2"], i_propositions=[])

        s_a, _ = s0 | e_a
        s_a.now["a_done"] = True

        s_b, _ = s0 | e_b
        s_b.now["b_done"] = True

        s_ab, _ = s_a | e_b
        s_ab.pre[s_b.name] = s_b.now

        assert len(s_ab.pre) == 2
        assert s_a.name in s_ab.pre and s_b.name in s_ab.pre

    def test_edges_completion_fails_if_order_difference_is_gt_one(self):
        """Ensures an edge is not added if events are not immediate successors."""
        p1, p2 = Process("P1"), Process("P2")
        e_a1 = Event("a1", ["P1", "-"], i_propositions=[])
        e_a2 = Event("a2", ["P1", "-"], i_propositions=[])
        e_b = Event("b", ["-", "P2"], i_propositions=[])
        p1.add_event(e_a1);
        p1.add_event(e_a2)
        p2.add_event(e_b)
        processes = {"P1": p1, "P2": p2}

        s_a1 = State([e_a1, ProcessModes.UNDEFINED], i_formulas=[])
        s_a2b = State([e_a2, e_b], i_formulas=[])

        s_a1.edges_completion([s_a2b], processes)

        assert s_a2b.name not in s_a1.successors