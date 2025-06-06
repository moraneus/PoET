# model/process.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Process model representing individual processes in the distributed system
# with event history management and process ID distribution utilities.

from typing import List, Tuple, Union

from model.event import Event
from model.process_modes import ProcessModes


class Process:
    """Represents a process in the distributed system with event history."""

    def __init__(self, i_name: str, i_propositions: Tuple[str, ...] = None):
        self.__m_name = i_name
        self.__m_events: List[Event] = []

    @property
    def name(self) -> str:
        """Get process name."""
        return self.__m_name

    @property
    def events(self) -> List[Event]:
        """Get list of events associated with this process."""
        return self.__m_events

    def add_event(self, event: Event) -> None:
        """Add event to process history."""
        self.__m_events.append(event)

    def find_event(self, event: Union[Event, ProcessModes]) -> int:
        """Find event index in process history, return -1 if not found."""
        if isinstance(event, ProcessModes):
            return -1

        try:
            return self.__m_events.index(event)
        except ValueError:
            return -1

    @staticmethod
    def distribute_processes(process_ids: List[str], num_processes: int) -> List[str]:
        """Distribute process IDs across available process slots."""
        result = ["-"] * num_processes

        for process_id in process_ids:
            index = Process._parse_process_id(process_id, num_processes)
            result[index] = process_id

        return result

    @staticmethod
    def _parse_process_id(process_id: str, num_processes: int) -> int:
        """Parse process ID and return corresponding index."""
        Process._validate_process_id_format(process_id)

        try:
            index = int(process_id[1:]) - 1
        except ValueError:
            raise ValueError(f"Invalid format for process ID: {process_id}")

        Process._validate_process_index(process_id, index, num_processes)
        return index

    @staticmethod
    def _validate_process_id_format(process_id: str) -> None:
        """Validate process ID format."""
        if not isinstance(process_id, str) or not process_id.startswith("P"):
            raise ValueError(f"Invalid format for process ID: {process_id}")

    @staticmethod
    def _validate_process_index(
        process_id: str, index: int, num_processes: int
    ) -> None:
        """Validate process index is within bounds."""
        if not (0 <= index < num_processes):
            raise IndexError(
                f"Process ID {process_id} results in out-of-bounds index {index} "
                f"for {num_processes} processes."
            )
