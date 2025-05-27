# model/process_modes.py


from enum import Enum


class ProcessModes(Enum):
    OPEN = '-'
    IOTA = 'i'
    CLOSED = '+'
    UNDEFINED = '?'
    ERROR = '*'

    def __str__(self):
        return self.value
