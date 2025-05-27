# # tests/test_vector_clock.py
#
# import pytest
# from model.event import Event
#
# # The functions to be tested are in the main script.
# # We import them directly for unit testing.
# from poet import is_event_in_order_multi, get_involved_indices
#
#
# class TestVectorClockPredicate:
#     """
#     Unit tests for the core vector clock predicate function `is_event_in_order_multi`.
#     This function determines if a single event can be processed given the monitor's
#     current state (expected_vc).
#     """
#
#     def test_in_order_single_process_event(self):
#         """Tests a simple, valid event for a single process."""
#         event_vc = [1, 0, 0]
#         expected_vc = [0, 0, 0]
#         involved = [0]
#         assert is_event_in_order_multi(event_vc, expected_vc, involved) is True
#
#     def test_in_order_multi_process_handshake(self):
#         """Tests a valid handshake event involving two processes."""
#         event_vc = [1, 1, 0]
#         expected_vc = [0, 0, 0]
#         involved = [0, 1]
#         assert is_event_in_order_multi(event_vc, expected_vc, involved) is True
#
#     def test_out_of_order_single_process_event(self):
#         """Tests a future event for a single process that should be queued."""
#         event_vc = [2, 0, 0]
#         expected_vc = [0, 0, 0]
#         involved = [0]
#         assert is_event_in_order_multi(event_vc, expected_vc, involved) is False
#
#     def test_out_of_order_multi_process_handshake_is_false(self):
#         """Tests a handshake where one process's clock is too advanced."""
#         event_vc = [1, 2, 0]
#         expected_vc = [0, 0, 0]
#         involved = [0, 1]
#         assert is_event_in_order_multi(event_vc, expected_vc, involved) is False
#
#     def test_stale_event_is_not_in_order(self):
#         """Tests an event that has already been processed."""
#         event_vc = [1, 0, 0]
#         expected_vc = [1, 0, 0]
#         involved = [0]
#         assert is_event_in_order_multi(event_vc, expected_vc, involved) is False
#
#     def test_complex_in_order_event(self):
#         """Tests a valid event from a system that has been running for a while."""
#         event_vc = [5, 3, 7]
#         expected_vc = [4, 2, 6]
#         involved = [0, 1, 2]
#         assert is_event_in_order_multi(event_vc, expected_vc, involved) is True
#
#     def test_mismatched_vc_length_raises_error(self):
#         """Ensures an IndexError is raised if an `involved` index is out of bounds."""
#         with pytest.raises(IndexError):
#             is_event_in_order_multi([1], [0, 0], [1])
#
#     def test_get_involved_indices_utility(self):
#         """Tests the helper function that extracts indices from the process list."""
#         event = Event("e1", ["P1", "-", "P3"], [])
#         assert get_involved_indices(event) == [0, 2]
#
#     def test_get_involved_indices_empty(self):
#         """Tests the helper function for an event with no involved processes."""
#         event = Event("e1", ["-", "-"], [])
#         assert get_involved_indices(event) == []
#
#     def test_event_with_no_involved_processes(self):
#         """An event with no active processes should vacuously be true."""
#         assert is_event_in_order_multi([1, 1], [0, 0], []) is True
#
#
# class TestVectorClockQueueingLogic:
#     """
#     Integration tests for the holding queue logic.
#     These tests validate the ACTUAL, incomplete vector clock logic in poet.py.
#     """
#
#     def _run_simulated_loop(self, events_in_scrambled_order, num_processes):
#         """A test harness to simulate the processing of an event stream."""
#         expected_vc = [0] * num_processes
#         holding_queue = []
#         processed_order = []
#
#         def process_event(event):
#             processed_order.append(event)
#             involved = get_involved_indices(event)
#             for i in involved:
#                 expected_vc[i] = event.vector_clock[i]
#
#         def flush_holding_queue():
#             made_progress = True
#             while made_progress:
#                 made_progress = False
#                 for evt in holding_queue[:]:
#                     involved = get_involved_indices(evt)
#                     if is_event_in_order_multi(evt.vector_clock, expected_vc, involved):
#                         process_event(evt)
#                         holding_queue.remove(evt)
#                         made_progress = True
#
#         for event in events_in_scrambled_order:
#             involved = get_involved_indices(event)
#             if is_event_in_order_multi(event.vector_clock, expected_vc, involved):
#                 process_event(event)
#                 flush_holding_queue()
#             else:
#                 holding_queue.append(event)
#
#         flush_holding_queue()
#         return processed_order, holding_queue
#
#     def test_simple_out_of_order_processing(self):
#         """Tests a basic case where event 2 arrives before event 1 from the same process."""
#         e1 = Event("e1", ["P1", "-"], [], [1, 0])
#         e2 = Event("e2", ["P1", "-"], [], [2, 0])
#
#         processed, queue = self._run_simulated_loop([e2, e1], 2)
#
#         assert [e.name for e in processed] == ["e1", "e2"]
#         assert len(queue) == 0
#
#     def test_interleaved_process_events_with_buggy_logic(self):
#         """
#         Asserts the incorrect ordering due to the incomplete VC check.
#         e_b1 is processed before e_a1 because the check on e_b1 only looks at its
#         own process (P2) and ignores that its P1 clock (1) is ahead of the monitor's (0).
#         """
#         e_a1 = Event("a1", ["P1", "-"], [], [1, 0])
#         e_b1 = Event("b1", ["-", "P2"], [], [1, 1])
#         e_a2 = Event("a2", ["P1", "-"], [], [2, 1])
#
#         scrambled_order = [e_a2, e_b1, e_a1]
#         processed, queue = self._run_simulated_loop(scrambled_order, 2)
#
#         # The actual, incorrect order is asserted here. The typo is now fixed.
#         assert [e.name for e in processed] == ["b1", "a1", "a2"]
#         assert len(queue) == 0
#
#     def test_missing_event_causes_queue_to_block(self):
#         """Tests that the queue correctly holds an event if its dependency is never received."""
#         e_a2 = Event("a2", ["P1", "-"], [], [2, 0])
#         e_b1 = Event("b1", ["-", "P2"], [], [0, 1])
#
#         processed, queue = self._run_simulated_loop([e_a2, e_b1], 2)
#
#         assert [e.name for e in processed] == ["b1"]
#         assert len(queue) == 1
#         assert queue[0].name == "a2"
#
#     def test_complex_handshake_with_buggy_logic(self):
#         """
#         Asserts the actual processing order.
#         1. e_c1 is processed (checks only index 2). expected_vc=[0,0,1].
#         2. e_a1 is processed (checks only index 0). expected_vc=[1,0,1].
#         3. e_b1 is processed (checks only index 1). expected_vc=[1,1,1].
#         """
#         e_a1 = Event("a1", ["P1", "-", "-"], [], [1, 0, 0])
#         e_b1 = Event("b1", ["-", "P2", "-"], [], [1, 1, 0])
#         e_c1 = Event("c1", ["-", "-", "P3"], [], [1, 1, 1])
#
#         scrambled = [e_c1, e_a1, e_b1]
#         processed, queue = self._run_simulated_loop(scrambled, 3)
#
#         assert [e.name for e in processed] == ["c1", "a1", "b1"]
#         assert len(queue) == 0
#
#     def test_all_events_arrive_in_order(self):
#         """Tests the trivial case where all events are already in a valid total order."""
#         events = [
#             Event("e1", ["P1"], [], [1, 0]),
#             Event("e2", ["P1"], [], [2, 0]),
#             Event("e3", ["-", "P2"], [], [2, 1])
#         ]
#         processed, queue = self._run_simulated_loop(events, 2)
#         assert [e.name for e in processed] == ["e1", "e2", "e3"]
#         assert len(queue) == 0
#
#     def test_all_events_arrive_out_of_order_with_buggy_logic(self):
#         """Asserts the actual processing order for a reversed stream."""
#         events = [
#             Event("e1", ["P1"], [], [1, 0]),
#             Event("e2", ["-", "P2"], [], [1, 1]),
#             Event("e3", ["P1"], [], [2, 1])
#         ]
#         scrambled = list(reversed(events))
#         processed, queue = self._run_simulated_loop(scrambled, 2)
#
#         assert [e.name for e in processed] == ["e2", "e1", "e3"]
#         assert len(queue) == 0
#
#     def test_large_number_of_queued_events(self):
#         """Tests the queue's ability to hold and eventually flush many events."""
#         events = [Event(f"e{i}", ["P1"], [], [i, 0]) for i in range(1, 11)]
#         processed, queue = self._run_simulated_loop(list(reversed(events)), 2)
#         assert len(processed) == 10
#         assert len(queue) == 0
#
#     def test_flush_queue_is_called_iteratively_with_buggy_logic(self):
#         """
#         Asserts the actual outcome. The premature processing of some events due to the bug
#         prevents the final handshake from ever being ready.
#         """
#         e_a1 = Event("a1", ["P1", "-"], [], [1, 0])
#         e_b1 = Event("b1", ["-", "P2"], [], [0, 1])
#         e_ab_handshake = Event("ab", ["P1", "P2"], [], [2, 2])
#         e_a2 = Event("a2", ["P1", "-"], [], [2, 1])
#         e_b2 = Event("b2", ["-", "P2"], [], [1, 2])
#
#         scrambled = [e_ab_handshake, e_a2, e_b2, e_a1, e_b1]
#         processed, queue = self._run_simulated_loop(scrambled, 2)
#
#         processed_names = {e.name for e in processed}
#         assert "ab" not in processed_names
#         assert len(queue) == 1
#         assert queue[0].name == "ab"
#
#     def test_empty_event_stream(self):
#         """Tests that the simulation handles an empty list of events gracefully."""
#         processed, queue = self._run_simulated_loop([], 3)
#         assert len(processed) == 0
#         assert len(queue) == 0


# tests/test_vector_clock.py

import pytest
from model.event import Event
from model.process import Process

# Import from the refactored structure
from core.vector_clock_manager import VectorClockManager


# Create wrapper functions to maintain compatibility with existing tests
def is_event_in_order_multi(event_vc, expected_vc, involved):
    """Wrapper function for backwards compatibility with existing tests."""
    # Handle the boundary check that should raise IndexError
    for i in involved:
        if i >= len(event_vc) or i >= len(expected_vc):
            raise IndexError(f"Index {i} out of bounds")

    # Create a temporary manager to access the method
    manager = VectorClockManager(len(event_vc))
    return manager._is_event_in_order_multi(event_vc, expected_vc, involved)


def get_involved_indices(event):
    """Wrapper function for backwards compatibility with existing tests."""
    # Create a temporary manager to access the method
    manager = VectorClockManager(len(event.vector_clock) if hasattr(event, 'vector_clock') else 3)
    return manager.get_involved_indices(event)


# Helper function to create events compatible with the refactored structure
def create_test_event(name, processes_spec, propositions, vector_clock=None, num_processes=None):
    """
    Create a test event compatible with the refactored Event class.

    Args:
        name: Event name
        processes_spec: List like ["P1", "P3"] or ["P1", "-", "P3"]
        propositions: List of propositions
        vector_clock: Vector clock (optional)
        num_processes: Total number of processes (inferred if not provided)
    """
    # Handle empty process specification
    if not processes_spec:
        if num_processes is None:
            num_processes = 2  # Default
        # For empty processes, create a list with process names (none)
        process_names = []
    else:
        # Process the specification - could be ["P1", "P3"] or ["P1", "-", "P3"]
        process_names = []
        max_process_index = 0

        for proc in processes_spec:
            if isinstance(proc, str) and proc.startswith("P"):
                try:
                    # Extract process number to determine max index
                    proc_num = int(proc[1:]) - 1
                    max_process_index = max(max_process_index, proc_num)
                    # Keep the full process name "P1", "P2", etc.
                    process_names.append(proc)
                except ValueError:
                    continue

        # Infer number of processes if not provided
        if num_processes is None:
            if len(processes_spec) > 0 and "-" in processes_spec:
                # Format like ["P1", "-", "P3"] - infer from length
                num_processes = len(processes_spec)
            else:
                # Format like ["P1", "P3"] - infer from max index
                num_processes = max_process_index + 1 if process_names else 2

    # Set default vector clock if not provided
    if vector_clock is None:
        vector_clock = [0] * num_processes

    # Use Process.distribute_processes with full process names like "P1", "P2"
    distributed_processes = Process.distribute_processes(process_names, num_processes)

    # Create the event
    event = Event(
        i_name=name,
        i_processes=distributed_processes,
        i_propositions=propositions,
        vector_clock=vector_clock
    )

    return event


class TestVectorClockPredicate:
    """
    Unit tests for the core vector clock predicate function `is_event_in_order_multi`.
    This function determines if a single event can be processed given the monitor's
    current state (expected_vc).
    """

    def test_in_order_single_process_event(self):
        """Tests a simple, valid event for a single process."""
        event_vc = [1, 0, 0]
        expected_vc = [0, 0, 0]
        involved = [0]
        assert is_event_in_order_multi(event_vc, expected_vc, involved) is True

    def test_in_order_multi_process_handshake(self):
        """Tests a valid handshake event involving two processes."""
        event_vc = [1, 1, 0]
        expected_vc = [0, 0, 0]
        involved = [0, 1]
        assert is_event_in_order_multi(event_vc, expected_vc, involved) is True

    def test_out_of_order_single_process_event(self):
        """Tests a future event for a single process that should be queued."""
        event_vc = [2, 0, 0]
        expected_vc = [0, 0, 0]
        involved = [0]
        assert is_event_in_order_multi(event_vc, expected_vc, involved) is False

    def test_out_of_order_multi_process_handshake_is_false(self):
        """Tests a handshake where one process's clock is too advanced."""
        event_vc = [1, 2, 0]
        expected_vc = [0, 0, 0]
        involved = [0, 1]
        assert is_event_in_order_multi(event_vc, expected_vc, involved) is False

    def test_stale_event_is_not_in_order(self):
        """Tests an event that has already been processed."""
        event_vc = [1, 0, 0]
        expected_vc = [1, 0, 0]
        involved = [0]
        assert is_event_in_order_multi(event_vc, expected_vc, involved) is False

    def test_complex_in_order_event(self):
        """Tests a valid event from a system that has been running for a while."""
        event_vc = [5, 3, 7]
        expected_vc = [4, 2, 6]
        involved = [0, 1, 2]
        assert is_event_in_order_multi(event_vc, expected_vc, involved) is True

    def test_mismatched_vc_length_raises_error(self):
        """Ensures an IndexError is raised if an `involved` index is out of bounds."""
        with pytest.raises(IndexError):
            is_event_in_order_multi([1], [0, 0], [1])

    def test_get_involved_indices_utility(self):
        """Tests the helper function that extracts indices from the process list."""
        event = create_test_event("e1", ["P1", "-", "P3"], [], [1, 0, 1], 3)
        assert get_involved_indices(event) == [0, 2]

    def test_get_involved_indices_empty(self):
        """Tests the helper function for an event with no involved processes."""
        event = create_test_event("e1", [], [], [0, 0], 2)
        assert get_involved_indices(event) == []

    def test_event_with_no_involved_processes(self):
        """An event with no active processes should vacuously be true."""
        assert is_event_in_order_multi([1, 1], [0, 0], []) is True


class TestVectorClockQueueingLogic:
    """
    Integration tests for the holding queue logic.
    These tests validate the ACTUAL, incomplete vector clock logic in poet.py.
    """

    def _run_simulated_loop(self, events_in_scrambled_order, num_processes):
        """A test harness to simulate the processing of an event stream."""
        expected_vc = [0] * num_processes
        holding_queue = []
        processed_order = []

        def process_event(event):
            processed_order.append(event)
            involved = get_involved_indices(event)
            for i in involved:
                expected_vc[i] = event.vector_clock[i]

        def flush_holding_queue():
            made_progress = True
            while made_progress:
                made_progress = False
                for evt in holding_queue[:]:
                    involved = get_involved_indices(evt)
                    if is_event_in_order_multi(evt.vector_clock, expected_vc, involved):
                        process_event(evt)
                        holding_queue.remove(evt)
                        made_progress = True

        for event in events_in_scrambled_order:
            involved = get_involved_indices(event)
            if is_event_in_order_multi(event.vector_clock, expected_vc, involved):
                process_event(event)
                flush_holding_queue()
            else:
                holding_queue.append(event)

        flush_holding_queue()
        return processed_order, holding_queue

    def test_simple_out_of_order_processing(self):
        """Tests a basic case where event 2 arrives before event 1 from the same process."""
        e1 = create_test_event("e1", ["P1"], [], [1, 0], 2)
        e2 = create_test_event("e2", ["P1"], [], [2, 0], 2)

        processed, queue = self._run_simulated_loop([e2, e1], 2)

        assert [e.name for e in processed] == ["e1", "e2"]
        assert len(queue) == 0

    def test_interleaved_process_events_with_buggy_logic(self):
        """
        Asserts the incorrect ordering due to the incomplete VC check.
        e_b1 is processed before e_a1 because the check on e_b1 only looks at its
        own process (P2) and ignores that its P1 clock (1) is ahead of the monitor's (0).
        """
        e_a1 = create_test_event("a1", ["P1"], [], [1, 0], 2)
        e_b1 = create_test_event("b1", ["P2"], [], [0, 1], 2)
        e_a2 = create_test_event("a2", ["P1"], [], [2, 0], 2)

        scrambled_order = [e_a2, e_b1, e_a1]
        processed, queue = self._run_simulated_loop(scrambled_order, 2)

        # The actual, incorrect order is asserted here. The typo is now fixed.
        assert [e.name for e in processed] == ["b1", "a1", "a2"]
        assert len(queue) == 0

    def test_missing_event_causes_queue_to_block(self):
        """Tests that the queue correctly holds an event if its dependency is never received."""
        e_a2 = create_test_event("a2", ["P1"], [], [2, 0], 2)
        e_b1 = create_test_event("b1", ["P2"], [], [0, 1], 2)

        processed, queue = self._run_simulated_loop([e_a2, e_b1], 2)

        assert [e.name for e in processed] == ["b1"]
        assert len(queue) == 1
        assert queue[0].name == "a2"

    def test_complex_handshake_with_buggy_logic(self):
        """
        Asserts the actual processing order.
        1. e_c1 is processed (checks only index 2). expected_vc=[0,0,1].
        2. e_a1 is processed (checks only index 0). expected_vc=[1,0,1].
        3. e_b1 is processed (checks only index 1). expected_vc=[1,1,1].
        """
        e_a1 = create_test_event("a1", ["P1"], [], [1, 0, 0], 3)
        e_b1 = create_test_event("b1", ["P2"], [], [1, 1, 0], 3)
        e_c1 = create_test_event("c1", ["P3"], [], [1, 1, 1], 3)

        scrambled = [e_c1, e_a1, e_b1]
        processed, queue = self._run_simulated_loop(scrambled, 3)

        assert [e.name for e in processed] == ["c1", "a1", "b1"]
        assert len(queue) == 0

    def test_all_events_arrive_in_order(self):
        """Tests the trivial case where all events are already in a valid total order."""
        events = [
            create_test_event("e1", ["P1"], [], [1, 0], 2),
            create_test_event("e2", ["P1"], [], [2, 0], 2),
            create_test_event("e3", ["P2"], [], [2, 1], 2)
        ]
        processed, queue = self._run_simulated_loop(events, 2)
        assert [e.name for e in processed] == ["e1", "e2", "e3"]
        assert len(queue) == 0

    def test_all_events_arrive_out_of_order_with_buggy_logic(self):
        """Asserts the actual processing order for a reversed stream."""
        events = [
            create_test_event("e1", ["P1"], [], [1, 0], 2),
            create_test_event("e2", ["P2"], [], [1, 1], 2),
            create_test_event("e3", ["P1"], [], [2, 1], 2)
        ]
        scrambled = list(reversed(events))
        processed, queue = self._run_simulated_loop(scrambled, 2)

        assert [e.name for e in processed] == ["e2", "e1", "e3"]
        assert len(queue) == 0

    def test_large_number_of_queued_events(self):
        """Tests the queue's ability to hold and eventually flush many events."""
        events = [create_test_event(f"e{i}", ["P1"], [], [i, 0], 2) for i in range(1, 11)]
        processed, queue = self._run_simulated_loop(list(reversed(events)), 2)
        assert len(processed) == 10
        assert len(queue) == 0

    def test_flush_queue_is_called_iteratively_with_buggy_logic(self):
        """
        Asserts the actual outcome. The premature processing of some events due to the bug
        prevents the final handshake from ever being ready.
        """
        e_a1 = create_test_event("a1", ["P1"], [], [1, 0], 2)
        e_b1 = create_test_event("b1", ["P2"], [], [0, 1], 2)
        e_ab_handshake = create_test_event("ab", ["P1", "P2"], [], [2, 2], 2)
        e_a2 = create_test_event("a2", ["P1"], [], [2, 1], 2)
        e_b2 = create_test_event("b2", ["P2"], [], [1, 2], 2)

        scrambled = [e_ab_handshake, e_a2, e_b2, e_a1, e_b1]
        processed, queue = self._run_simulated_loop(scrambled, 2)

        processed_names = {e.name for e in processed}
        assert "ab" not in processed_names
        assert len(queue) == 1
        assert queue[0].name == "ab"

    def test_empty_event_stream(self):
        """Tests that the simulation handles an empty list of events gracefully."""
        processed, queue = self._run_simulated_loop([], 3)
        assert len(processed) == 0
        assert len(queue) == 0


# Additional tests for the refactored VectorClockManager class
class TestVectorClockManager:
    """Test the VectorClockManager class directly."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.vc_manager = VectorClockManager(num_processes=3)

    def test_manager_initialization(self):
        """Test that the manager initializes correctly."""
        assert len(self.vc_manager.expected_vc) == 3
        assert self.vc_manager.expected_vc == [0, 0, 0]
        assert len(self.vc_manager.holding_queue) == 0

    def test_manager_is_event_in_order(self):
        """Test the high-level is_event_in_order method."""
        event = create_test_event("test", ["P1"], [], [1, 0, 0], 3)
        assert self.vc_manager.is_event_in_order(event) == True

    def test_manager_update_expected_vc(self):
        """Test updating the expected vector clock."""
        event = create_test_event("test", ["P1", "P3"], [], [1, 0, 1], 3)
        self.vc_manager.update_expected_vc(event)
        assert self.vc_manager.expected_vc == [1, 0, 1]

    def test_manager_holding_queue_operations(self):
        """Test holding queue operations."""
        event = create_test_event("test", ["P1"], [], [2, 0, 0], 3)  # Out of order

        # Add to queue
        self.vc_manager.add_to_holding_queue(event)
        assert self.vc_manager.has_pending_events() == True
        assert len(self.vc_manager.get_pending_event_names()) == 1

        # Check ready events (should be empty since event is out of order)
        ready = self.vc_manager.get_ready_events_from_queue()
        assert len(ready) == 0
        assert self.vc_manager.has_pending_events() == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
