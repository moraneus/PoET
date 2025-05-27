# tests/test_process.py

import pytest
from model.process import Process
from model.event import Event
from model.process_modes import ProcessModes


class TestProcess:
    """
    Test suite for the Process class.
    A Process acts as a container for the sequence of events it participates in.
    This suite also heavily tests the utility function for mapping events to processes.
    """

    def test_process_initialization(self):
        """Tests that a process is created with a name and an empty event list."""
        proc = Process("P1", i_propositions=("p", "q"))
        assert isinstance(proc, Process)
        assert proc.events == []

    def test_add_single_event(self):
        """Tests adding one event to a process's history."""
        proc = Process("P1")
        event1 = Event("e1", [], [])
        proc.add_event(event1)
        assert proc.events == [event1]

    def test_add_and_find_multiple_events(self):
        """Tests adding a sequence of events and finding their indices."""
        proc = Process("P1")
        events = [Event(f"e{i}", [], []) for i in range(5)]
        for e in events:
            proc.add_event(e)

        assert len(proc.events) == 5
        assert proc.find_event(events[0]) == 0
        assert proc.find_event(events[4]) == 4

    def test_find_event_not_found_raises_value_error(self):
        """Ensures that searching for an event not in the process history raises an error."""
        proc = Process("P1")
        event1 = Event("e1", [], [])
        event_other = Event("e_other", [], [])
        proc.add_event(event1)
        with pytest.raises(ValueError):
            proc.find_event(event_other)

    def test_find_event_with_non_event_types(self):
        """
        Verifies that `find_event` returns -1 for specific non-event inputs.
        NOTE: The original code does not handle `None`, so it is not tested here.
        """
        proc = Process("P1")
        proc.add_event(Event("e1", [], []))
        assert proc.find_event(ProcessModes.IOTA) == -1
        assert proc.find_event(ProcessModes.UNDEFINED) == -1

    def test_distribute_processes_normal_case(self):
        """Tests the standard functionality of the distributor."""
        result = Process.distribute_processes(["P1", "P3"], 3)
        assert result == ["P1", "-", "P3"]

    def test_distribute_processes_fully_populated(self):
        """Tests the case where all processes are specified."""
        result = Process.distribute_processes(["P1", "P2", "P3"], 3)
        assert result == ["P1", "P2", "P3"]

    def test_distribute_processes_large_and_sparse(self):
        """Tests distribution with a high number of total processes."""
        result = Process.distribute_processes(["P2", "P10"], 12)
        expected = ['-'] * 12
        expected[1] = "P2"
        expected[9] = "P10"
        assert result == expected

    def test_distribute_processes_empty_input_list(self):
        """Tests distribution when the list of active processes is empty."""
        result = Process.distribute_processes([], 4)
        assert result == ["-", "-", "-", "-"]

    def test_distribute_processes_out_of_order_input(self):
        """Ensures the distributor correctly places processes regardless of input order."""
        result = Process.distribute_processes(["P3", "P1"], 3)
        assert result == ["P1", "-", "P3"]

    def test_distribute_processes_error_on_out_of_bounds(self, capsys):
        """
        Tests that providing an invalid process index (e.g., P4 in a 3-process system)
        correctly triggers a SystemExit.
        """
        with pytest.raises(SystemExit) as e:
            Process.distribute_processes(["P4"], 3)

        assert e.type == SystemExit
        assert e.value.code == 1

        captured = capsys.readouterr()
        assert "[PROCESS ERROR]" in captured.out
        assert "list assignment index out of range" in captured.out

    def test_find_event_with_duplicate_event_objects(self):
        """Tests that `find_event` uses object identity and finds the correct index."""
        proc = Process("P1")
        event1_obj1 = Event("e1", [], [])
        event1_obj2 = Event("e1", [], [])  # Same name, different object
        proc.add_event(event1_obj1)
        proc.add_event(event1_obj2)
        assert proc.find_event(event1_obj1) == 0
        assert proc.find_event(event1_obj2) == 1

    def test_distribute_processes_with_single_process(self):
        """Tests the edge case of a system with only one process."""
        result = Process.distribute_processes(["P1"], 1)
        assert result == ["P1"]

    def test_distribute_processes_single_process_inactive(self):
        """Tests the edge case of a single-process system with no active event."""
        result = Process.distribute_processes([], 1)
        assert result == ["-"]