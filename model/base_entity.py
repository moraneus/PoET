# model/base_entity.py

from typing import List

from model.process_modes import ProcessModes


class BaseEntity:
    def __init__(self, i_name: str, i_processes: List[ProcessModes | str]):
        self.__m_name = i_name
        self._m_processes = self.__initialize_processes(i_processes)

    @property
    def name(self) -> str:
        return self.__m_name

    @property
    def processes(self):
        return self._m_processes

    def __initialize_processes(self, i_processes: List[ProcessModes | str]):
        a = [ProcessModes.IOTA if x == '-' else x for x in i_processes]
        return a

    def __len__(self):
        return len(self._m_processes)
