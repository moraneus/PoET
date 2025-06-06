# model/process_modes.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Process mode enumeration defining the various states a process can be in
# during distributed system execution and monitoring.

from enum import Enum


class ProcessModes(Enum):
    """Enumeration of possible process states in distributed system execution."""

    OPEN = "-"
    IOTA = "i"
    CLOSED = "+"
    UNDEFINED = "?"
    ERROR = "*"

    def __str__(self) -> str:
        """Return string representation of the process mode value."""
        return self.value
