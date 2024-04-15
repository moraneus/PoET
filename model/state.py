from typing import Dict, Set, Union, Tuple, Optional
from typing import List

from model.base_entity import BaseEntity
from model.event import Event
from model.process_modes import ProcessModes


class State(BaseEntity):
    __COUNTER = 0
    __SUBFORMULAS = None

    def __init__(self, i_processes: List[Union[ProcessModes, str]], i_formulas: List[str] = None):
        """
        Initialize the instance.

        :param i_processes: A list of processes, which can be instances of ProcessModes or strings.
        :param i_formulas: A list of formulas represented as strings.
        """
        super().__init__(f"S{self.get_counter()}", i_processes)

        if i_formulas is not None:
            State.__SUBFORMULAS = i_formulas

        # Successors dictionary, initially empty.
        self.__m_successors = {}

        self.__m_evaluated_value = False

        # Propositions set by a dedicated method.
        self.__m_propositions = self.__set_propositions()

        # Initializing now and pre dictionaries with formulas set to False.
        self.__m_now: Dict[str, bool] = self.__initialize_formula_dict()
        if self.name == 'S0':
            self.__m_pre: Dict[str, Dict[str, bool]] = {'_': self.__initialize_formula_dict()}
        else:
            self.__m_pre: Dict[str, Dict[str, bool]] = {}

        # Enabled state of the object, initially True.
        self.__m_enabled = True

    def __str__(self):
        value = f"EVALUATED VALUE: {self.value}"
        return f"[{self.name}]: {value}"

    def __repr__(self):
        newline = '\n\t'
        processes =  f"PROCESSES: ({', '.join([str(p) for p in self._m_processes])})"
        transitions = "TRANSITIONS: (" + \
                      ', '.join([f"{self.name} -> {k} ({v[0]})" for k, v in self.__m_successors.items()]) + ")"
        propositions = f"PROPOSITIONS: ({', '.join([p for p in self.__m_propositions])})"
        summary = f"SUMMARY: \n\t{newline.join([f'{k}: {v}' for k, v in self.__m_now.items()])}"
        value = f"EVALUATED VALUE: {self.value}"

        return f"[{self.name}]: {value}, {processes} {transitions}, {propositions}\n" \
               f"{summary}"

    def __contains__(self, m):
        return m in self.__m_propositions

    def __or__(self, other) -> Tuple[Optional['State'], Optional[Set[Tuple[Event, int]]]]:
        if isinstance(other, Event):
            state_processes, closed_event = self.__compare_to_event(other)
            if ProcessModes.ERROR not in state_processes:
                new_state = State(i_processes=state_processes)

                new_state.pre[self.name] = self.now

                state_name = new_state.name
                self.__add_successors(i_event=other, i_state_name=state_name, i_state=new_state)
                return new_state, closed_event
            else:
                return None, None

        elif isinstance(other, State):
            pass
        else:
            raise TypeError(
                "Operation not supported between instances of 'State' and '{}'".format(type(other).__name__))

    @property
    def value(self) -> bool:
        return self.__m_evaluated_value

    @value.setter
    def value(self, i_value: bool):
        self.__m_evaluated_value = i_value

    @property
    def propositions(self):
        return self.__m_propositions

    @property
    def successors(self) -> Dict[str, Tuple[Event, 'State']]:
        return self.__m_successors

    @property
    def enabled(self) -> bool:
        return self.__m_enabled

    @enabled.setter
    def enabled(self, value):
        self.__m_enabled = value

    @property
    def now(self) -> Dict[str, bool]:
        return self.__m_now

    @property
    def pre(self) -> Dict[str, Dict[str, bool]]:
        return self.__m_pre

    @classmethod
    def increment_counter(cls):
        cls.__COUNTER += 1

    @classmethod
    def get_counter(cls):
        current = cls.__COUNTER
        cls.increment_counter()
        return current

    def get_now_subformula(self, i_key: str):
        return self.__m_now.get(i_key)

    def set_now_subformula(self, i_key: str, i_value: bool) -> bool:
        if i_key in self.__m_now:
            self.__m_now[i_key] = i_value
            return True
        return False

    def get_pre_subformula(self, i_key: str):
        return self.__m_pre[i_key]

    def set_pre_subformula(self, i_key: str, i_value: bool) -> bool:
        if i_key in self.__m_pre:
            self.__m_pre[i_key] = i_value
            return True
        return False

    def __add_successors(self, i_event: Event, i_state: 'State', i_state_name: str):
        self.__m_successors.update({i_state_name: (i_event, i_state)})

    def __set_propositions(self):
        state_propositions = set()
        for process in self._m_processes:
            if isinstance(process, Event):
                state_propositions.update(process.propositions)

            # # TODO: Think if needed
            # elif process == ProcessModes.IOTA:
            #     state_propositions.update(['i'])

        return state_propositions

    def __compare_to_event(self, i_event: Event):
        """
        Compares this object's process states to another event, producing a result state list.
        Updates self.__m_processes with the comparison result.

        Parameters:
            i_event (Event): The event to compare against.

        Returns:
            list: A list representing the result state after comparison.

        Raises:
            ValueError: If the objects are not of the same length.
        """
        if len(self._m_processes) != len(i_event.processes):
            raise ValueError("Objects are not of the same length.")

        result_state = []
        closed_event = set()

        for index, (process_state, event_state) in enumerate(zip(self._m_processes, i_event.processes)):
            updated_state = None

            # -,-,- | -,-,- = -,-,- (-,-,- -> -,-,-)
            if process_state == ProcessModes.IOTA and event_state == ProcessModes.IOTA:
                result_state.append(ProcessModes.IOTA)

            # -,-,- | a,-,- = a,-,- (-,-,- -> +,-,-)
            elif process_state == ProcessModes.IOTA and not isinstance(event_state, ProcessModes):
                result_state.append(i_event)
                updated_state = ProcessModes.CLOSED

            # a,-,- | -,-,b = a,-,b
            elif isinstance(process_state, Event) and event_state == ProcessModes.IOTA:
                result_state.append(process_state)

            # +,-,- | -,-,b = ?,-,b
            elif State.is_proc_closed(process_state, index) and event_state == ProcessModes.IOTA:
                result_state.append(ProcessModes.UNDEFINED)

            # +,-,- | a,-,- = *,-,-
            elif State.is_proc_closed(process_state, index) and not isinstance(event_state, ProcessModes):
                result_state.append(ProcessModes.ERROR)

            elif not isinstance(process_state, ProcessModes) and not isinstance(event_state, ProcessModes):
                if not State.is_proc_closed(process_state, index):
                    if process_state != event_state:
                        result_state.append(i_event)
                        closed_event.add((process_state, index))

            else:
                result_state.append(None)  # Handle unspecified cases

            if updated_state is not None:
                self._m_processes[index] = updated_state  # Update the process state

        return result_state, closed_event

    def edges_completion(self, other_states, i_processes):
        """
        Update the state's processes by replacing '?' with '+' based on comparisons with other states.
        """
        for other_state in other_states:

            # Avoid self-comparison.
            if self == other_state:
                continue

            potential_replacements = {}

            for index, (self_proc, other_proc) in enumerate(zip(self.processes, other_state.processes)):

                # If both are the same continue to next state proc
                if self_proc == other_proc:
                    continue

                # If both are ProcessModes (OPEN or UNDEFINED)
                elif isinstance(self_proc, ProcessModes) and isinstance(other_proc, ProcessModes):
                    continue

                # If the difference is bigger than 1 break and check the next state
                order_differences = State.event_order_differences(i_processes[f'P{index + 1}'], self_proc, other_proc)

                if order_differences == 1:
                    potential_replacements[index] = other_proc
                elif order_differences > 1:
                    potential_replacements = None
                    break

            if potential_replacements is not None:
                potential_set = set(potential_replacements.values())
                if len(potential_set) > 1:
                    continue
                else:
                    self.__add_successors(
                        i_event=potential_set.pop(), i_state_name=other_state.name, i_state=other_state)

                    # # TODO: Remove
                    # other_state.predecessors = self

                    other_state.pre[self.name] = self.now

        for index, self_proc in enumerate(self.processes):
            if self_proc == ProcessModes.UNDEFINED:
                self.processes[index] = ProcessModes.CLOSED

    @staticmethod
    def is_proc_closed(i_proc: ProcessModes | Event, i_index: int) -> bool:
        return State.__get_proc_mode(i_proc, i_index) == ProcessModes.CLOSED

    @staticmethod
    def __get_proc_mode(i_proc: ProcessModes | Event, i_index: int):
        if isinstance(i_proc, Event):
            a = i_proc.mode[i_index]
            return a
        elif isinstance(i_proc, List):
            return State.__get_proc_mode(i_proc[i_index], i_index)
        else:
            return i_proc

    @staticmethod
    def event_order_differences(i_process, i_event_a, i_event_b) -> int:
        current_timestamp = i_process.find_event(i_event_a)
        other_timestamp = i_process.find_event(i_event_b)
        return abs(other_timestamp - current_timestamp)

    @staticmethod
    def get_unique_indexes(lst) -> Set[int]:
        # Dictionary to store unique elements and their first index
        unique_indexes = set()
        unique_items = set()
        for index, item in enumerate(lst):
            # If item is not yet in the dictionary, add it with its index
            if str(item) not in unique_items:
                unique_items.add(str(item))
                unique_indexes.add(item[0])
        return unique_indexes

    def __initialize_formula_dict(self) -> Dict[str, bool]:
        """
        Initialize a dictionary from a list of formulas where each is set to False.

        :param formulas: A list of formulas as strings.
        :return: A dictionary with each formula as a key and False as its value.
        """
        return {formula: False for formula in State.__SUBFORMULAS}
