# tests/core_tests/test_event.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Test suite for Event class ensuring correct instantiation and management
# of event properties including timeline, processes, and propositions.

import pytest

from model.event import Event
from model.process_modes import ProcessModes


class TestEvent:
    """Test suite for the Event class."""

    def setup_method(self):
        """Reset class-level timeline before each test."""
        Event._Event__TIMELINE = 0

    def test_event_initialization_simple(self):
        """Test basic event creation with essential properties."""
        event = Event("e1", ["P1", "-"], ["p"], vector_clock=[1, 0])
        assert event.name == "e1"
        assert event.propositions == ["p"]
        assert event.vector_clock == [1, 0]

    def test_timeline_increments_sequentially(self):
        """Test sequential timestamp assignment for events."""
        event1 = Event("e1", [], [])
        event2 = Event("e2", [], [])
        event3 = Event("e3", [], [])
        assert event1.time == 0
        assert event2.time == 1
        assert event3.time == 2

    def test_timeline_is_global_counter(self):
        """Test timeline as global class counter."""
        event_a = Event("event_a", ["P1"], [])
        event_b = Event("event_b", ["P2"], [])
        assert event_b.time > event_a.time

    def test_default_vector_clock_initialization(self):
        """Test default vector clock initialization to zeros."""
        event = Event("e_test", ["-", "-", "-"], [])
        assert event.vector_clock == [0, 0, 0]

    def test_active_processes_identification(self):
        """Test identification of participating processes."""
        event = Event("e_sparse", ["-", "P2", "-", "P4"], [])
        assert event.active_processes == [1, 3]

    def test_active_processes_all_participating(self):
        """Test case where all processes participate."""
        event = Event("e_full", ["P1", "P2"], [])
        assert event.active_processes == [0, 1]

    def test_active_processes_none_participating(self):
        """Test event with no participating processes."""
        event = Event("e_empty", ["-", "-"], [])
        assert event.active_processes == []

    def test_multi_process_participation(self):
        """Test event with multiple process involvement."""
        event = Event("handshake", ["P1", "P2"], ["sync"])
        assert event.active_processes == [0, 1]
        assert "sync" in event.propositions

    def test_mode_update_and_representation(self):
        """Test mode tracking and string representation."""
        event = Event("e_mode", ["P1", "P2"], [])
        assert repr(event) == "e_modeii"
        event.update_mode(ProcessModes.CLOSED, 0)
        assert repr(event) == "e_mode+i"

    def test_proposition_membership(self):
        """Test proposition membership checking."""
        event = Event("e_props", ["P1"], ["p", "q"])
        assert "p" in event
        assert "q" in event
        assert "r" not in event

    def test_length_reflects_process_count(self):
        """Test length method returns process count."""
        event = Event("e_len", ["-", "P2", "-", "P4", "-"], [])
        assert len(event) == 5

    def test_initial_mode_is_iota(self):
        """Test initial mode array initialization."""
        event = Event("e1", ["P1", "P2"], [])
        assert event.mode == [ProcessModes.IOTA, ProcessModes.IOTA]

    def test_mode_array_access(self):
        """Test direct access and modification of process modes."""
        event = Event("e1", ["P1", "P2"], [])
        assert event[0] == ProcessModes.IOTA
        event[1] = ProcessModes.CLOSED
        assert event[1] == ProcessModes.CLOSED

    def test_mode_access_out_of_bounds(self):
        """Test invalid index access raises error."""
        event = Event("e1", ["P1"], [])
        with pytest.raises(IndexError):
            _ = event[1]

    def test_string_representation(self):
        """Test string representation of event."""
        event = Event("MyEvent", ["P1"], [])
        assert str(event) == "MyEvent"

    def test_repr_no_active_processes(self):
        """Test representation with no active processes."""
        event = Event("internal_step", ["-", "-"], [])
        assert repr(event) == "internal_step"

    def test_comprehensive_initialization(self):
        """Test event creation with all parameters."""
        event = Event(
            i_name="e_full",
            i_processes=["P1", "P2"],
            i_propositions=["p"],
            vector_clock=[1, 1],
        )
        assert event.time == 0
        assert len(event) == 2
        assert "p" in event
        assert event.vector_clock == [1, 1]

    def test_multiple_mode_updates(self):
        """Test sequence of mode changes."""
        event = Event("e_seq", ["P1", "P2", "P3"], [])
        event.update_mode(ProcessModes.CLOSED, 0)
        event.update_mode(ProcessModes.CLOSED, 2)
        assert event.mode == [
            ProcessModes.CLOSED,
            ProcessModes.IOTA,
            ProcessModes.CLOSED,
        ]
        assert repr(event) == "e_seq+i+"

    def test_mode_update_inactive_process(self):
        """Test mode update on inactive process index."""
        event = Event("e_inactive", ["P1", "-"], [])
        event.update_mode(ProcessModes.CLOSED, 1)

        assert event.mode[1] == ProcessModes.CLOSED
        assert repr(event) == "e_inactivei"
