# model/base_entity.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Base entity class providing common functionality for named entities
# with process associations in the distributed system model.

from typing import List, Union

from model.process_modes import ProcessModes


class BaseEntity:
    """Base class for entities with name and process associations."""

    def __init__(self, name: str, processes: List[Union[ProcessModes, str]]):
        self.__m_name = name
        self._m_processes = self._initialize_processes(processes)

    @property
    def name(self) -> str:
        """Get entity name."""
        return self.__m_name

    @property
    def processes(self) -> List[Union[ProcessModes, str]]:
        """Get list of associated processes."""
        return self._m_processes

    def _initialize_processes(
        self, processes: List[Union[ProcessModes, str]]
    ) -> List[Union[ProcessModes, str]]:
        """Initialize processes list, converting '-' markers to IOTA mode."""
        return [
            ProcessModes.IOTA if process == "-" else process for process in processes
        ]

    def __len__(self) -> int:
        """Return number of associated processes."""
        return len(self._m_processes)
