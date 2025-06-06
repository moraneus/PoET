# model/event.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Event model representing distributed system events with process associations,
# propositions, vector clocks, and timeline management for runtime verification.

from typing import List, Union

from model.base_entity import BaseEntity
from model.process_modes import ProcessModes


class Event(BaseEntity):
    """Represents an event in distributed system execution."""

    __TIMELINE = 0

    def __init__(
        self,
        i_name: str,
        i_processes: List[Union[ProcessModes, str]],
        i_propositions: List[str] = None,
        vector_clock: List[int] = None,
    ):
        super().__init__(i_name, i_processes)
        self.__m_active_processes = self._get_active_processes_in_event()
        self.__m_time = self._get_timeline()
        self.__m_propositions = i_propositions or []
        self.__m_event_procs_mode = [ProcessModes.IOTA] * len(i_processes)
        self.vector_clock = (
            vector_clock if vector_clock is not None else [0] * len(i_processes)
        )

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{self.name}{self._get_mode_string()}"

    def __getitem__(self, key: int) -> ProcessModes:
        return self.__m_event_procs_mode[key]

    def __setitem__(self, key: int, value: ProcessModes) -> None:
        self.__m_event_procs_mode[key] = value

    def __contains__(self, item: str) -> bool:
        return item in self.__m_propositions

    @property
    def time(self) -> int:
        """Get event timeline position."""
        return self.__m_time

    @property
    def active_processes(self) -> List[int]:
        """Get list of active process indices."""
        return self.__m_active_processes

    @property
    def mode(self) -> List[ProcessModes]:
        """Get event process modes."""
        return self.__m_event_procs_mode

    @property
    def propositions(self) -> List[str]:
        """Get event propositions."""
        return self.__m_propositions

    def update_mode(self, value: ProcessModes, proc_index: int) -> None:
        """Update process mode for specific process index."""
        self.__m_event_procs_mode[proc_index] = value

    @classmethod
    def _get_timeline(cls) -> int:
        """Get current timeline value and increment it."""
        current_time = cls.__TIMELINE
        cls._increment_time()
        return current_time

    @classmethod
    def _increment_time(cls, amount: int = 1) -> None:
        """Increment timeline counter."""
        cls.__TIMELINE += amount

    def _get_mode_string(self) -> str:
        """Get string representation of modes for active processes."""
        return "".join(
            [self.__m_event_procs_mode[i].value for i in self.__m_active_processes]
        )

    def _get_active_processes_in_event(self) -> List[int]:
        """Get indices of processes that are not in IOTA mode."""
        return [
            index
            for index, value in enumerate(self._m_processes)
            if value != ProcessModes.IOTA
        ]
