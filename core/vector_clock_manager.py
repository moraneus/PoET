# core/vector_clock_manager.py
"""Vector clock management for event ordering in distributed systems."""

from typing import List
from model.event import Event


class VectorClockManager:
    """Manages vector clock ordering for events in distributed systems."""

    def __init__(self, num_processes: int):
        """Initialize vector clock manager.

        Args:
            num_processes: Number of processes in the distributed system
        """
        self.num_processes = num_processes
        self.expected_vc = [0] * num_processes
        self.holding_queue: List[Event] = []

    def get_involved_indices(self, event: Event) -> List[int]:
        """Get indices of processes involved in the event.

        Args:
            event: Event to analyze

        Returns:
            List of 0-based process indices involved in the event
        """
        indices = []
        for proc_repr in event.processes:
            if isinstance(proc_repr, str) and proc_repr.startswith("P"):
                try:
                    indices.append(int(proc_repr[1:]) - 1)
                except ValueError:
                    continue
        return indices

    def is_event_in_order(self, event: Event) -> bool:
        """Check if event can be delivered according to vector clock ordering.

        Args:
            event: Event to check

        Returns:
            True if event can be delivered, False otherwise
        """
        involved_indices = self.get_involved_indices(event)
        return self._is_event_in_order_multi(
            event.vector_clock, self.expected_vc, involved_indices
        )

    def _is_event_in_order_multi(self, event_vc: List[int], expected_vc: List[int],
                                 involved: List[int]) -> bool:
        """Check if event is in order for multiple involved processes.

        Args:
            event_vc: Event's vector clock
            expected_vc: Expected vector clock state
            involved: List of involved process indices

        Returns:
            True if event is in correct order
        """
        for i in involved:
            if i >= len(event_vc) or i >= len(expected_vc):
                return False
            if event_vc[i] != expected_vc[i] + 1:
                return False
        return True

    def update_expected_vc(self, event: Event) -> None:
        """Update expected vector clock after processing an event.

        Args:
            event: Event that was processed
        """
        involved_indices = self.get_involved_indices(event)
        for i in involved_indices:
            self.expected_vc[i] = event.vector_clock[i]

    def add_to_holding_queue(self, event: Event) -> None:
        """Add event to holding queue for later processing.

        Args:
            event: Event to queue
        """
        self.holding_queue.append(event)

    def get_ready_events_from_queue(self) -> List[Event]:
        """Get events from holding queue that are now ready for processing.

        Returns:
            List of events ready for processing
        """
        ready_events = []
        remaining_events = []

        for event in self.holding_queue:
            if self.is_event_in_order(event):
                ready_events.append(event)
            else:
                remaining_events.append(event)

        self.holding_queue = remaining_events
        return ready_events

    def has_pending_events(self) -> bool:
        """Check if there are events in the holding queue.

        Returns:
            True if holding queue is not empty
        """
        return len(self.holding_queue) > 0

    def get_pending_event_names(self) -> List[str]:
        """Get names of events in the holding queue.

        Returns:
            List of event names in holding queue
        """
        return [event.name for event in self.holding_queue]