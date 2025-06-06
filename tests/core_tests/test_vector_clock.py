# tests/core_tests/test_vector_clock.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Test suite for VectorClockManager validating event ordering, queue management,
# and Fidge-Mattern vector clock algorithms for distributed system monitoring.

import pytest

from model.event import Event
from model.process import Process
from core.vector_clock_manager import VectorClockManager


def create_test_event(
    name, processes_spec, propositions=None, vector_clock=None, num_processes=None
):
    """Create test event compatible with Event class."""
    if propositions is None:
        propositions = []

    if not processes_spec:
        if num_processes is None:
            num_processes = 2
        process_names = []
    else:
        process_names = []
        max_process_index = 0

        for proc in processes_spec:
            if isinstance(proc, str) and proc.startswith("P"):
                try:
                    proc_num = int(proc[1:]) - 1
                    max_process_index = max(max_process_index, proc_num)
                    process_names.append(proc)
                except ValueError:
                    continue

        if num_processes is None:
            if len(processes_spec) > 0 and "-" in processes_spec:
                num_processes = len(processes_spec)
            else:
                num_processes = max_process_index + 1 if process_names else 2

    if vector_clock is None:
        vector_clock = [0] * num_processes

    distributed_processes = Process.distribute_processes(process_names, num_processes)

    return Event(
        i_name=name,
        i_processes=distributed_processes,
        i_propositions=propositions,
        vector_clock=vector_clock,
    )


class TestVectorClockPredicate:
    """Test core vector clock predicate functions."""

    def setup_method(self):
        """Set up test manager."""
        self.manager = VectorClockManager(3)

    def test_in_order_single_process_event(self):
        """Test valid single process event."""
        assert self.manager._is_event_in_order_multi([1, 0, 0], [0, 0, 0], [0]) is True

    def test_in_order_multi_process_handshake(self):
        """Test valid handshake event."""
        assert (
            self.manager._is_event_in_order_multi([1, 1, 0], [0, 0, 0], [0, 1]) is True
        )

    def test_out_of_order_single_process_event(self):
        """Test future event that should be queued."""
        assert self.manager._is_event_in_order_multi([2, 0, 0], [0, 0, 0], [0]) is False

    def test_out_of_order_multi_process_handshake(self):
        """Test handshake with advanced process clock."""
        assert (
            self.manager._is_event_in_order_multi([1, 2, 0], [0, 0, 0], [0, 1]) is False
        )

    def test_stale_event_not_in_order(self):
        """Test already processed event."""
        assert self.manager._is_event_in_order_multi([1, 0, 0], [1, 0, 0], [0]) is False

    def test_complex_in_order_event(self):
        """Test valid event from running system."""
        assert (
            self.manager._is_event_in_order_multi([5, 3, 7], [4, 2, 6], [0, 1, 2])
            is True
        )

    def test_get_involved_indices_utility(self):
        """Test process index extraction."""
        event = create_test_event("e1", ["P1", "P3"], [], [1, 0, 1], 3)
        assert self.manager.get_involved_indices(event) == [0, 2]

    def test_get_involved_indices_empty(self):
        """Test event with no involved processes."""
        event = create_test_event("e1", [], [], [0, 0], 2)
        manager = VectorClockManager(2)
        assert manager.get_involved_indices(event) == []

    def test_event_no_involved_processes(self):
        """Test event with no active processes."""
        assert self.manager._is_event_in_order_multi([1, 1, 1], [0, 0, 0], []) is True


class TestVectorClockQueueingLogic:
    """Test holding queue logic and event processing simulation."""

    def _run_simulated_loop(self, events_in_scrambled_order, num_processes):
        """Simulate event processing with vector clock ordering."""
        manager = VectorClockManager(num_processes)
        processed_order = []

        def process_event(event):
            processed_order.append(event)
            manager.update_expected_vc(event)

        def flush_holding_queue():
            made_progress = True
            while made_progress:
                made_progress = False
                ready_events = manager.get_ready_events_from_queue()
                for evt in ready_events:
                    process_event(evt)
                    made_progress = True

        for event in events_in_scrambled_order:
            if manager.is_event_in_order(event):
                process_event(event)
                flush_holding_queue()
            else:
                manager.add_to_holding_queue(event)

        flush_holding_queue()
        return processed_order, list(manager.holding_queue)

    def test_simple_out_of_order_processing(self):
        """Test basic out-of-order event processing."""
        e1 = create_test_event("e1", ["P1"], [], [1, 0], 2)
        e2 = create_test_event("e2", ["P1"], [], [2, 0], 2)

        processed, queue = self._run_simulated_loop([e2, e1], 2)

        assert [e.name for e in processed] == ["e1", "e2"]
        assert len(queue) == 0

    def test_interleaved_process_events(self):
        """Test interleaved events from different processes."""
        e_a1 = create_test_event("a1", ["P1"], [], [1, 0], 2)
        e_b1 = create_test_event("b1", ["P2"], [], [0, 1], 2)
        e_a2 = create_test_event("a2", ["P1"], [], [2, 0], 2)

        scrambled_order = [e_a2, e_b1, e_a1]
        processed, queue = self._run_simulated_loop(scrambled_order, 2)

        assert [e.name for e in processed] == ["b1", "a1", "a2"]
        assert len(queue) == 0

    def test_missing_event_blocks_queue(self):
        """Test queue blocking when dependency is missing."""
        e_a2 = create_test_event("a2", ["P1"], [], [2, 0], 2)
        e_b1 = create_test_event("b1", ["P2"], [], [0, 1], 2)

        processed, queue = self._run_simulated_loop([e_a2, e_b1], 2)

        assert [e.name for e in processed] == ["b1"]
        assert len(queue) == 1
        assert queue[0].name == "a2"

    def test_complex_handshake_processing(self):
        """Test complex multi-process event ordering."""
        e_a1 = create_test_event("a1", ["P1"], [], [1, 0, 0], 3)
        e_b1 = create_test_event("b1", ["P2"], [], [1, 1, 0], 3)
        e_c1 = create_test_event("c1", ["P3"], [], [1, 1, 1], 3)

        scrambled = [e_c1, e_a1, e_b1]
        processed, queue = self._run_simulated_loop(scrambled, 3)

        assert [e.name for e in processed] == ["c1", "a1", "b1"]
        assert len(queue) == 0

    def test_all_events_in_order(self):
        """Test trivial case with all events in valid order."""
        events = [
            create_test_event("e1", ["P1"], [], [1, 0], 2),
            create_test_event("e2", ["P1"], [], [2, 0], 2),
            create_test_event("e3", ["P2"], [], [2, 1], 2),
        ]
        processed, queue = self._run_simulated_loop(events, 2)
        assert [e.name for e in processed] == ["e1", "e2", "e3"]
        assert len(queue) == 0

    def test_all_events_out_of_order(self):
        """Test processing reversed event stream."""
        events = [
            create_test_event("e1", ["P1"], [], [1, 0], 2),
            create_test_event("e2", ["P2"], [], [1, 1], 2),
            create_test_event("e3", ["P1"], [], [2, 1], 2),
        ]
        scrambled = list(reversed(events))
        processed, queue = self._run_simulated_loop(scrambled, 2)

        assert [e.name for e in processed] == ["e2", "e1", "e3"]
        assert len(queue) == 0

    def test_large_queue_processing(self):
        """Test queue handling with many events."""
        events = [
            create_test_event(f"e{i}", ["P1"], [], [i, 0], 2) for i in range(1, 11)
        ]
        processed, queue = self._run_simulated_loop(list(reversed(events)), 2)
        assert len(processed) == 10
        assert len(queue) == 0

    def test_complex_handshake_blocking(self):
        """Test handshake event blocking due to ordering."""
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
        """Test handling empty event stream."""
        processed, queue = self._run_simulated_loop([], 3)
        assert len(processed) == 0
        assert len(queue) == 0


class TestVectorClockManager:
    """Test VectorClockManager class directly."""

    def setup_method(self):
        """Set up test manager."""
        self.vc_manager = VectorClockManager(num_processes=3)

    def test_manager_initialization(self):
        """Test manager initialization."""
        assert len(self.vc_manager.expected_vc) == 3
        assert self.vc_manager.expected_vc == [0, 0, 0]
        assert len(self.vc_manager.holding_queue) == 0

    def test_manager_event_ordering(self):
        """Test high-level event ordering method."""
        event = create_test_event("test", ["P1"], [], [1, 0, 0], 3)
        assert self.vc_manager.is_event_in_order(event) is True

    def test_manager_update_vector_clock(self):
        """Test vector clock update."""
        event = create_test_event("test", ["P1", "P3"], [], [1, 0, 1], 3)
        self.vc_manager.update_expected_vc(event)
        assert self.vc_manager.expected_vc == [1, 0, 1]

    def test_manager_queue_operations(self):
        """Test holding queue operations."""
        event = create_test_event("test", ["P1"], [], [2, 0, 0], 3)

        self.vc_manager.add_to_holding_queue(event)
        assert self.vc_manager.has_pending_events() is True
        assert len(self.vc_manager.get_pending_event_names()) == 1

        ready = self.vc_manager.get_ready_events_from_queue()
        assert len(ready) == 0
        assert self.vc_manager.has_pending_events() is True

    def test_manager_statistics(self):
        """Test statistics tracking."""
        event = create_test_event("test", ["P1"], [], [1, 0, 0], 3)

        self.vc_manager.is_event_in_order(event)
        stats = self.vc_manager.get_statistics()

        assert stats["events_checked"] == 1
        assert stats["events_in_order"] == 1
        assert stats["events_out_of_order"] == 0

    def test_manager_queue_analysis(self):
        """Test queue state analysis."""
        event = create_test_event("test", ["P1"], [], [2, 0, 0], 3)
        self.vc_manager.add_to_holding_queue(event)

        analysis = self.vc_manager.analyze_queue_state()
        assert analysis["queue_size"] == 1
        assert len(analysis["events"]) == 1
