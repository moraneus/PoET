# tests/core_tests/test_state.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Test suite for State class validating frontier representation, state transitions,
# proposition calculation, and edge completion logic for partial order executions.

import pytest

from model.state import State
from model.event import Event
from model.process import Process
from model.process_modes import ProcessModes


class TestState:
    """Test suite for the State class representing global frontiers."""

    def setup_method(self):
        """Reset state counter and subformulas before each test."""
        State._State__COUNTER = 0
        State._State__SUBFORMULAS = None

    def test_state_initialization(self):
        """Test state creation including initial state S0."""
        s_init_formulas = State(i_processes=[], i_formulas=["p"])
        assert s_init_formulas.name == "S0"

        state = State(i_processes=["-", "-"])
        assert state.name == "S1"
        assert state.enabled is True
        assert "p" in state.now
        assert state.now["p"] is False

        if s_init_formulas.name == "S0":
            assert "_" in s_init_formulas.pre
            assert "p" in s_init_formulas.pre["_"]
            assert s_init_formulas.pre["_"]["p"] is False

        assert len(state.pre) == 0

    def test_state_propositions_from_frontier_events(self):
        """Test proposition collection from events in frontier."""
        e1 = Event("e1", ["P1"], ["p", "q"])
        e2 = Event("e2", ["P2"], ["r"])
        State._State__SUBFORMULAS = []
        state = State(i_processes=[e1, e2], i_formulas=[])
        assert state.propositions == {"p", "q", "r"}

    def test_initial_transition_from_iota(self):
        """Test first transition from all-IOTA state."""
        State._State__SUBFORMULAS = []
        s0 = State(i_processes=[ProcessModes.IOTA, ProcessModes.IOTA], i_formulas=[])
        event_a = Event("a", ["P1", "-"], i_propositions=[])

        s1, closed_set = s0 | event_a

        assert s1 is not None
        assert s1.name == "S1"
        assert len(s1.processes) == 2
        assert s1.processes[0] is event_a
        assert s1.processes[1] is ProcessModes.IOTA
        assert closed_set == set()
        assert s0.processes[0] == ProcessModes.CLOSED

    def test_transition_with_concurrent_event(self):
        """Test adding concurrent event to existing frontier."""
        State._State__SUBFORMULAS = []
        e_a = Event("a", ["P1", "-"], i_propositions=[])
        s_a = State(i_processes=[e_a, ProcessModes.IOTA], i_formulas=[])
        e_b = Event("b", ["-", "P2"], i_propositions=[])

        s_ab, _ = s_a | e_b

        assert s_ab is not None
        assert len(s_ab.processes) == 2
        assert s_ab.processes[0] is e_a
        assert s_ab.processes[1] is e_b

    def test_transition_with_dependent_event(self):
        """Test transition with event on same process as frontier event."""
        State._State__SUBFORMULAS = []
        e_a1 = Event("a1", ["P1", "-"], i_propositions=[])
        s1 = State(i_processes=[e_a1, ProcessModes.IOTA], i_formulas=[])
        e_a2 = Event("a2", ["P1", "-"], i_propositions=[])

        s2, closed_set = s1 | e_a2

        assert s2 is not None
        assert len(s2.processes) == 2
        assert s2.processes[0] is e_a2
        assert s2.processes[1] is ProcessModes.IOTA
        assert closed_set == {(e_a1, 0)}

    def test_transition_error_on_closed_process(self):
        """Test no state created when event occurs on closed process."""
        State._State__SUBFORMULAS = []
        s_closed = State(
            i_processes=[ProcessModes.CLOSED, ProcessModes.IOTA], i_formulas=[]
        )
        event_a_on_p1 = Event("a", ["P1", "-"], i_propositions=[])

        s_new, closed_set = s_closed | event_a_on_p1

        assert s_new is None
        assert closed_set is None

    def test_predecessor_summary_inheritance(self):
        """Test new state inherits parent's predecessor summaries."""
        s0 = State(i_processes=[ProcessModes.IOTA], i_formulas=["p"])
        s0.now["p"] = True

        e1 = Event("e1", ["P1"], i_propositions=[])
        s1, _ = s0 | e1

        assert len(s1.pre) == 2
        assert s0.name in s1.pre
        assert s1.pre[s0.name] == s0.now
        assert s1.pre[s0.name]["p"] is True
        assert "_" in s1.pre
        assert s1.pre["_"]["p"] is False

    def test_diamond_completion_adds_missing_edge(self):
        """Test edges_completion logic for concurrent events."""
        p1, p2 = Process("P1"), Process("P2")
        e_a = Event("a", ["P1", "-"], i_propositions=[])
        e_b = Event("b", ["-", "P2"], i_propositions=[])
        p1.add_event(e_a)
        p2.add_event(e_b)
        processes_mock = {"P1": p1, "P2": p2}

        State._State__SUBFORMULAS = []
        s_a = State([e_a, ProcessModes.UNDEFINED], i_formulas=[])
        s_b = State([ProcessModes.IOTA, e_b], i_formulas=[])
        s_ab = State([e_a, e_b], i_formulas=[])

        s_a.edges_completion([s_b, s_ab], processes_mock)

        assert s_ab.name in s_a.successors
        assert s_a.successors[s_ab.name][0] is e_b
        assert s_a.processes[1] == ProcessModes.CLOSED

    def test_diamond_completion_multiple_predecessors(self):
        """Test predecessor accumulation in diamond patterns."""
        s0 = State(
            i_processes=[ProcessModes.IOTA, ProcessModes.IOTA],
            i_formulas=["a_done", "b_done"],
        )

        e_a = Event("a", ["P1", "-"], i_propositions=[])
        e_b = Event("b", ["-", "P2"], i_propositions=[])

        s_a, _ = s0 | e_a
        s_a.now["a_done"] = True

        s_b, _ = s0 | e_b
        s_b.now["b_done"] = True

        s_ab, _ = s_a | e_b
        s_ab.pre[s_b.name] = s_b.now

        assert len(s_ab.pre) == 4
        assert s_a.name in s_ab.pre
        assert s_b.name in s_ab.pre
        assert s0.name in s_ab.pre
        assert "_" in s_ab.pre

    def test_edges_completion_rejects_non_immediate_successors(self):
        """Test edges_completion rejects events with order difference > 1."""
        p1, p2 = Process("P1"), Process("P2")
        e_a1 = Event("a1", ["P1", "-"], i_propositions=[])
        e_a2 = Event("a2", ["P1", "-"], i_propositions=[])
        e_b = Event("b", ["-", "P2"], i_propositions=[])
        p1.add_event(e_a1)
        p1.add_event(e_a2)
        p2.add_event(e_b)
        processes = {"P1": p1, "P2": p2}

        State._State__SUBFORMULAS = []
        s_a1 = State([e_a1, ProcessModes.UNDEFINED], i_formulas=[])
        s_a2b = State([e_a2, e_b], i_formulas=[])

        s_a1.edges_completion([s_a2b], processes)

        assert s_a2b.name not in s_a1.successors
