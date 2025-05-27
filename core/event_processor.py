# core/event_processor.py
"""Event processing and initialization for the PoET monitor."""

from typing import List, Any
from model.event import Event
from model.process import Process
from utils.config import Config


class EventProcessor:
    """Handles event initialization and processing logic."""

    def __init__(self, config: Config, num_processes: int):
        """Initialize event processor.

        Args:
            config: Configuration object
            num_processes: Number of processes in the system
        """
        self.config = config
        self.num_processes = num_processes

        # Reset timeline counter
        Event._Event__TIMELINE = 0

    def initialize_event(self, event_data: List[Any]) -> Event:
        """Initialize an event from trace data.

        Args:
            event_data: Raw event data from trace file

        Returns:
            Initialized Event object

        Raises:
            ValueError: If event data is invalid
        """
        if len(event_data) < 3:
            raise ValueError(f"Invalid event data: {event_data}")

        event_name = str(event_data[0])

        # Process distribution (can raise SystemExit on error)
        try:
            event_processes = Process.distribute_processes(
                event_data[1], self.num_processes
            )
        except SystemExit as e:
            raise ValueError(f"Invalid process specification in event {event_name}: {event_data[1]}")

        propositions = event_data[2]

        # Handle vector clock
        vector_clock = self._process_vector_clock(event_data, event_name)

        # Create event
        event = Event(
            i_name=event_name,
            i_processes=event_processes,
            i_propositions=propositions,
            vector_clock=vector_clock
        )

        if self.config.is_debug:
            print(f"DEBUG: Initialized event {event_name} with VC: {vector_clock}")

        return event

    def _process_vector_clock(self, event_data: List[Any], event_name: str) -> List[int]:
        """Process and validate vector clock from event data.

        Args:
            event_data: Raw event data
            event_name: Name of the event (for debugging)

        Returns:
            Processed vector clock
        """
        if len(event_data) > 3:
            raw_vc = event_data[3]
        else:
            raw_vc = [0] * self.num_processes

        # Ensure correct length
        if len(raw_vc) != self.num_processes:
            if self.config.is_debug:
                print(f"VC_WARNING: Event '{event_name}' has VC length {len(raw_vc)}, "
                      f"system has {self.num_processes} processes. Adjusting VC.")

            # Pad or truncate to correct length
            final_vc = (raw_vc + [0] * self.num_processes)[:self.num_processes]
        else:
            final_vc = raw_vc[:]

        return final_vc

    def validate_event_data(self, event_data: List[Any]) -> bool:
        """Validate event data structure.

        Args:
            event_data: Raw event data to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(event_data, list) or len(event_data) < 3:
            return False

        # Check event name
        if not event_data[0]:
            return False

        # Check process specification
        if not isinstance(event_data[1], list):
            return False

        # Check propositions (can be empty list)
        if not isinstance(event_data[2], list):
            return False

        # Check vector clock if present
        if len(event_data) > 3:
            vc = event_data[3]
            if not isinstance(vc, list) or not all(isinstance(x, int) for x in vc):
                return False

        return True