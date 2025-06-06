# tests/core_tests/test_process.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Test suite for Process class validating event history management
# and process ID distribution utilities for distributed system modeling.

import pytest

from model.process import Process
from model.event import Event
from model.process_modes import ProcessModes


class TestProcess:
    """Test suite for the Process class."""

    def test_process_initialization(self):
        """Test process creation with name and empty event list."""
        proc = Process("P1", i_propositions=("p", "q"))
        assert isinstance(proc, Process)
        assert proc.name == "P1"
        assert proc.events == []

    def test_add_single_event(self):
        """Test adding single event to process history."""
        proc = Process("P1")
        event1 = Event("e1", ["P1"], [])
        proc.add_event(event1)
        assert proc.events == [event1]

    def test_add_and_find_multiple_events(self):
        """Test adding sequence of events and finding their indices."""
        proc = Process("P1")
        events = [Event(f"e{i}", ["P1"], []) for i in range(5)]
        for e in events:
            proc.add_event(e)

        assert len(proc.events) == 5
        assert proc.find_event(events[0]) == 0
        assert proc.find_event(events[4]) == 4

    def test_find_event_not_found(self):
        """Test finding non-existent event returns -1."""
        proc = Process("P1")
        event1 = Event("e1", ["P1"], [])
        event_other = Event("e_other", ["P2"], [])
        proc.add_event(event1)
        assert proc.find_event(event_other) == -1

    def test_find_event_with_process_modes(self):
        """Test find_event with ProcessModes returns -1."""
        proc = Process("P1")
        proc.add_event(Event("e1", ["P1"], []))
        assert proc.find_event(ProcessModes.IOTA) == -1
        assert proc.find_event(ProcessModes.UNDEFINED) == -1
        assert proc.find_event(ProcessModes.CLOSED) == -1
        assert proc.find_event(ProcessModes.OPEN) == -1
        assert proc.find_event(ProcessModes.ERROR) == -1

    def test_distribute_processes_normal_case(self):
        """Test standard process distribution functionality."""
        result = Process.distribute_processes(["P1", "P3"], 3)
        assert result == ["P1", "-", "P3"]

    def test_distribute_processes_fully_populated(self):
        """Test distribution with all processes specified."""
        result = Process.distribute_processes(["P1", "P2", "P3"], 3)
        assert result == ["P1", "P2", "P3"]

    def test_distribute_processes_large_and_sparse(self):
        """Test distribution with high number of total processes."""
        result = Process.distribute_processes(["P2", "P10"], 12)
        expected = ["-"] * 12
        expected[1] = "P2"
        expected[9] = "P10"
        assert result == expected

    def test_distribute_processes_empty_input(self):
        """Test distribution with empty active processes list."""
        result = Process.distribute_processes([], 4)
        assert result == ["-", "-", "-", "-"]

    def test_distribute_processes_out_of_order(self):
        """Test distribution with unordered input."""
        result = Process.distribute_processes(["P3", "P1"], 3)
        assert result == ["P1", "-", "P3"]

    def test_distribute_processes_out_of_bounds_error(self):
        """Test out-of-bounds process index raises IndexError."""
        with pytest.raises(IndexError, match=r"out-of-bounds index .* for 3 processes"):
            Process.distribute_processes(["P4"], 3)

        with pytest.raises(IndexError, match=r"out-of-bounds index .* for 2 processes"):
            Process.distribute_processes(["P1", "P3"], 2)

    def test_distribute_processes_invalid_format_error(self):
        """Test malformed process ID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid format for process ID: PX"):
            Process.distribute_processes(["PX"], 3)

        with pytest.raises(ValueError, match="Invalid format for process ID: P"):
            Process.distribute_processes(["P"], 3)

        with pytest.raises(ValueError, match="Invalid format for process ID: NotAP"):
            Process.distribute_processes(["NotAP"], 3)

    def test_find_event_with_duplicate_objects(self):
        """Test find_event uses object identity for distinct objects."""
        proc = Process("P1")
        event1_obj1 = Event("e1", ["P1"], [])
        event1_obj2 = Event("e1", ["P1"], [])
        proc.add_event(event1_obj1)
        proc.add_event(event1_obj2)
        assert proc.find_event(event1_obj1) == 0
        assert proc.find_event(event1_obj2) == 1

    def test_distribute_processes_single_process(self):
        """Test distribution with single process system."""
        result = Process.distribute_processes(["P1"], 1)
        assert result == ["P1"]

    def test_distribute_processes_single_process_inactive(self):
        """Test distribution for single process with no active event."""
        result = Process.distribute_processes([], 1)
        assert result == ["-"]
