# model/process.py


import sys
import traceback
from typing import List, Tuple

from graphics.prints import Prints
from model.event import Event
from model.process_modes import ProcessModes


class Process:
    def __init__(self, i_name: str, i_propositions: Tuple[str, ...] = None):
        self.__m_name = i_name
        self.__m_events = []
        self.__m_propositions = i_propositions

    @property
    def events(self) -> List[Event]:
        return self.__m_events

    def add_event(self, i_event: Event):
        self.__m_events.append(i_event)

    def find_event(self, i_event: Event | ProcessModes) -> int:
        if i_event in [ProcessModes.UNDEFINED, ProcessModes.IOTA]:
            return -1
        return self.__m_events.index(i_event)

    @staticmethod
    def distribute_processes(i_processes: List[str], i_num_of_processes: int) -> List[str]:
        result = ['-'] * i_num_of_processes

        for process in i_processes:
            index = int(process[1:]) - 1
            try:
                result[index] = process
            except IndexError as e:
                Prints.process_error(e)
                sys.exit(1)

        return result

