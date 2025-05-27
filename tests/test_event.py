# tests/test_event.py

import pytest
from model.event import Event
from model.process_modes import ProcessModes


class TestEvent:
    """
    Test suite for the Event class.
    Ensures that events, which represent actions in the distributed system,
    are correctly instantiated and manage their properties like time,
    processes, and propositions.
    """

    def setup_method(self):
        """
        Pytest hook to reset the class-level timeline before each test.
        This ensures that tests are isolated and don't influence each other's timestamps.
        """
        Event._Event__TIMELINE = 0

    def test_event_initialization_simple(self):
        """Tests basic object creation with essential properties."""
        event = Event("e1", ["P1", "-"], ["p"], vector_clock=[1, 0])
        assert event.name == "e1"
        assert event.propositions == ["p"]
        assert event.vector_clock == [1, 0]

    def test_timeline_increments_sequentially(self):
        """Ensures each new event gets a unique, sequential timestamp."""
        event1 = Event("e1", [], [])
        event2 = Event("e2", [], [])
        event3 = Event("e3", [], [])
        assert event1.time == 0
        assert event2.time == 1
        assert event3.time == 2

    def test_timeline_is_global_and_independent_of_event_data(self):
        """Verifies the timeline is a global class counter, not per-instance."""
        event_a = Event("event_a", ["P1"], [])
        event_b = Event("event_b", ["P2"], [])
        assert event_b.time > event_a.time

    def test_default_vector_clock_is_all_zeros(self):
        """Checks if the vector clock defaults to a list of zeros if not provided."""
        event = Event("e_test", ["-", "-", "-"], [])
        assert event.vector_clock == [0, 0, 0]

    def test_active_processes_are_identified_correctly(self):
        """Tests identification of participating processes from the process list."""
        event = Event("e_sparse", ["-", "P2", "-", "P4"], [])
        assert event.active_processes == [1, 3]

    def test_active_processes_when_all_are_active(self):
        """Tests the case where all processes participate in the event."""
        event = Event("e_full", ["P1", "P2"], [])
        assert event.active_processes == [0, 1]

    def test_active_processes_when_none_are_active(self):
        """Tests an internal or empty event with no participating processes."""
        event = Event("e_empty", ["-", "-"], [])
        assert event.active_processes == []

    def test_event_with_shared_process_participation(self):
        """Tests an event where multiple processes are involved (e.g., a handshake)."""
        event = Event("handshake", ["P1", "P2"], ["sync"])
        assert event.active_processes == [0, 1]
        assert "sync" in event.propositions

    def test_mode_update_and_representation(self):
        """
        Tests the internal mode tracking and how it affects the event's representation.
        The repr is used for debugging and visualization.
        """
        event = Event("e_mode", ["P1", "P2"], [])
        assert repr(event) == "e_modeii"
        event.update_mode(ProcessModes.CLOSED, 0)
        assert repr(event) == "e_mode+i"

    def test_proposition_membership_check(self):
        """Tests the `in` operator for checking propositions."""
        event = Event("e_props", ["P1"], ["p", "q"])
        assert "p" in event
        assert "q" in event
        assert "r" not in event

    def test_len_dunder_method_reflects_process_count(self):
        """Ensures `len(event)` returns the total number of processes."""
        event = Event("e_len", ["-", "P2", "-", "P4", "-"], [])
        assert len(event) == 5

    def test_initial_mode_is_always_iota(self):
        """Confirms that the internal mode array is initialized correctly."""
        event = Event("e1", ["P1", "P2"], [])
        assert event.mode == [ProcessModes.IOTA, ProcessModes.IOTA]

    def test_getitem_setitem_on_internal_modes(self):
        """Tests direct access and modification of the event's process modes."""
        event = Event("e1", ["P1", "P2"], [])
        assert event[0] == ProcessModes.IOTA
        event[1] = ProcessModes.CLOSED
        assert event[1] == ProcessModes.CLOSED

    def test_getitem_out_of_bounds(self):
        """Ensures accessing a mode with an invalid index raises an error."""
        event = Event("e1", ["P1"], [])
        with pytest.raises(IndexError):
            _ = event[1]

    def test_str_representation(self):
        """Verifies the user-facing string representation of an event."""
        event = Event("MyEvent", ["P1"], [])
        assert str(event) == "MyEvent"

    def test_repr_with_no_active_processes(self):
        """Checks the representation of an event with no active processes."""
        event = Event("internal_step", ["-", "-"], [])
        assert repr(event) == "internal_step"

    def test_event_initialization_with_all_properties(self):
        """A comprehensive test creating an event with all parameters specified."""
        event = Event(
            i_name="e_full",
            i_processes=["P1", "P2"],
            i_propositions=["p"],
            vector_clock=[1, 1]
        )
        assert event.time == 0
        assert len(event) == 2
        assert "p" in event
        assert event.vector_clock == [1, 1]

    def test_multiple_mode_updates(self):
        """Tests a sequence of mode changes on the same event."""
        event = Event("e_seq", ["P1", "P2", "P3"], [])
        event.update_mode(ProcessModes.CLOSED, 0)
        event.update_mode(ProcessModes.CLOSED, 2)
        assert event.mode == [ProcessModes.CLOSED, ProcessModes.IOTA, ProcessModes.CLOSED]
        assert repr(event) == "e_seq+i+"

    def test_mode_update_on_inactive_process(self):
        """
        Tests updating a mode at an index where the process is not active.
        The internal mode array should update, but the repr should not change
        as it only shows modes for active processes.
        """
        event = Event("e_inactive", ["P1", "-"], [])
        event.update_mode(ProcessModes.CLOSED, 1)  # Update inactive process

        # Verify the internal mode was updated
        assert event.mode[1] == ProcessModes.CLOSED

        # The repr should NOT change because it only shows modes for active processes.
        # The only active process is at index 0, and its mode is still IOTA.
        assert repr(event) == "e_inactivei"