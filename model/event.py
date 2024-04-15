from typing import List

from model.base_entity import BaseEntity
from model.process_modes import ProcessModes


class Event(BaseEntity):
    __TIMELINE = 0

    def __init__(self, i_name: str, i_processes: List[ProcessModes | str], i_propositions: List[str] = None):
        super().__init__(i_name, i_processes)
        self.__m_active_processes = self.get_active_processes_in_event()
        self.__m_time = self.get_timeline()
        self.__m_propositions = i_propositions
        self.__m_event_procs_mode = [ProcessModes.IOTA] * len(i_processes)

    def __str__(self):
        return f"""{self.name}"""

    def __repr__(self):
        return f"""{self.name}{self.__mode()}"""

    def __getitem__(self, key):
        return self.__m_event_procs_mode[key]

    def __setitem__(self, key, value):
        self.__m_event_procs_mode[key] = value

    def __contains__(self, m):
        return m in self.__m_propositions

    @property
    def time(self) -> int:
        return self.__m_time

    @property
    def active_processes(self):
        return self.__m_active_processes

    @property
    def mode(self):
        return self.__m_event_procs_mode

    @property
    def propositions(self) -> List[str]:
        return self.__m_propositions

    def update_mode(self, i_value: ProcessModes, i_proc_index: int):
        self.__m_event_procs_mode[i_proc_index] = i_value

    @classmethod
    def get_timeline(cls):
        current_time = cls.__TIMELINE
        cls.increment_time()
        return current_time

    @classmethod
    def increment_time(cls, amount=1):
        cls.__TIMELINE += amount

    def __mode(self) -> str:
        return ''.join([self.__m_event_procs_mode[i].value for i in self.__m_active_processes])

    def get_active_processes_in_event(self):
        """
        Returns the indexes of elements in the input list that are not ProcessModes.OPEN.
        """
        return [index for index, value in enumerate(self._m_processes) if value != ProcessModes.IOTA]
