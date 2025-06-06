# model/state.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# State model representing global states (frontiers) in distributed system
# execution with PCTL evaluation support and state transition management.

from typing import Dict, Set, Union, Tuple, Optional, List

from model.base_entity import BaseEntity
from model.event import Event
from model.process_modes import ProcessModes


class State(BaseEntity):
    """Represents a global state (frontier) in distributed system execution."""

    __COUNTER = 0
    __SUBFORMULAS = None

    def __init__(
        self, i_processes: List[Union[ProcessModes, str]], i_formulas: List[str] = None
    ):
        super().__init__(f"S{self._get_counter()}", i_processes)

        if i_formulas is not None:
            State.__SUBFORMULAS = i_formulas

        self.__m_successors = {}
        self.__m_evaluated_value = False
        self.__m_propositions = self._set_propositions()
        self.__m_now: Dict[str, bool] = self._initialize_formula_dict()

        if self.name == "S0":
            self.__m_pre: Dict[str, Dict[str, bool]] = {
                "_": self._initialize_formula_dict()
            }
        else:
            self.__m_pre: Dict[str, Dict[str, bool]] = {}

        self.__m_enabled = True

    def __str__(self) -> str:
        value = f"EVALUATED VALUE: {self.value}"
        return f"[{self.name}]: {value}"

    def __repr__(self) -> str:
        newline = "\n\t"
        processes = f"PROCESSES: ({', '.join([str(p) for p in self._m_processes])})"
        transitions = (
            "TRANSITIONS: ("
            + ", ".join(
                [f"{self.name} -> {k} ({v[0]})" for k, v in self.__m_successors.items()]
            )
            + ")"
        )
        propositions = (
            f"PROPOSITIONS: ({', '.join([p for p in self.__m_propositions])})"
        )
        summary = f"SUMMARY: \n\t{newline.join([f'{k}: {v}' for k, v in self.__m_now.items()])}"
        value = f"EVALUATED VALUE: {self.value}"

        return f"[{self.name}]: {value}, {processes} {transitions}, {propositions}\n{summary}"

    def __contains__(self, item: str) -> bool:
        return item in self.__m_propositions

    def __or__(
        self, other
    ) -> Tuple[Optional["State"], Optional[Set[Tuple[Event, int]]]]:
        """Create new state by applying event transition."""
        if isinstance(other, Event):
            state_processes, closed_event = self._compare_to_event(other)
            if ProcessModes.ERROR not in state_processes:
                new_state = State(i_processes=state_processes)

                new_state.pre.update(self.pre)
                new_state.pre[self.name] = self.now

                state_name = new_state.name
                self._add_successors(
                    i_event=other, i_state_name=state_name, i_state=new_state
                )
                return new_state, closed_event
            else:
                return None, None
        elif isinstance(other, State):
            pass
        else:
            raise TypeError(
                f"Operation not supported between instances of 'State' and '{type(other).__name__}'"
            )

    @property
    def value(self) -> bool:
        """Get evaluated PCTL value."""
        return self.__m_evaluated_value

    @value.setter
    def value(self, value: bool) -> None:
        """Set evaluated PCTL value."""
        self.__m_evaluated_value = value

    @property
    def propositions(self) -> Set[str]:
        """Get state propositions."""
        return self.__m_propositions

    @property
    def successors(self) -> Dict[str, Tuple[Event, "State"]]:
        """Get successor states."""
        return self.__m_successors

    @property
    def enabled(self) -> bool:
        """Get enabled status."""
        return self.__m_enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set enabled status."""
        self.__m_enabled = value

    @property
    def now(self) -> Dict[str, bool]:
        """Get current formula evaluations."""
        return self.__m_now

    @property
    def pre(self) -> Dict[str, Dict[str, bool]]:
        """Get predecessor formula evaluations."""
        return self.__m_pre

    @classmethod
    def _get_counter(cls) -> int:
        """Get current counter value and increment it."""
        current = cls.__COUNTER
        cls._increment_counter()
        return current

    @classmethod
    def _increment_counter(cls) -> None:
        """Increment state counter."""
        cls.__COUNTER += 1

    def _add_successors(
        self, i_event: Event, i_state: "State", i_state_name: str
    ) -> None:
        """Add successor state."""
        self.__m_successors.update({i_state_name: (i_event, i_state)})

    def _set_propositions(self) -> Set[str]:
        """Calculate cumulative propositions from process histories."""
        state_propositions = set()

        from graphics.prints import Prints

        debug_enabled = (
            hasattr(Prints, "CURRENT_OUTPUT_LEVEL")
            and Prints.CURRENT_OUTPUT_LEVEL == "debug"
        )

        for i, process in enumerate(self._m_processes):
            if isinstance(process, Event):
                process_id = f"P{i + 1}"

                if hasattr(self, "_processes_map"):
                    process_events = self._get_process_history(process_id, process)
                    cumulative_props = set()

                    for event in process_events:
                        if hasattr(event, "propositions") and event.propositions:
                            cumulative_props.update(event.propositions)

                    state_propositions.update(cumulative_props)

                    if debug_enabled:
                        print(
                            f"      P{i + 1}: Cumulative props from {len(process_events)} events: {cumulative_props}"
                        )
                else:
                    event_props = (
                        process.propositions if hasattr(process, "propositions") else []
                    )
                    if event_props:
                        state_propositions.update(event_props)

                    if debug_enabled:
                        print(
                            f"      P{i + 1}: {process.name} → {event_props} (frontier only - may be incomplete)"
                        )

        return state_propositions

    def _get_process_history(
        self, process_id: str, frontier_event: Event
    ) -> List[Event]:
        """Get all events from a process up to the frontier event."""
        if not hasattr(self, "_processes_map"):
            return [frontier_event]

        process_obj = self._processes_map.get(process_id)
        if not process_obj:
            return [frontier_event]

        try:
            frontier_index = process_obj.events.index(frontier_event)
            return process_obj.events[: frontier_index + 1]
        except ValueError:
            return [frontier_event]

    def _compare_to_event(self, event: Event) -> Tuple[List, Set[Tuple[Event, int]]]:
        """Compare state processes to event, producing result state list."""
        if len(self._m_processes) != len(event.processes):
            raise ValueError("Objects are not of the same length.")

        result_state = []
        closed_event = set()

        for index, (process_state, event_state) in enumerate(
            zip(self._m_processes, event.processes)
        ):
            updated_state = None

            if process_state == ProcessModes.IOTA and event_state == ProcessModes.IOTA:
                result_state.append(ProcessModes.IOTA)
            elif process_state == ProcessModes.IOTA and not isinstance(
                event_state, ProcessModes
            ):
                result_state.append(event)
                updated_state = ProcessModes.CLOSED
            elif isinstance(process_state, Event) and event_state == ProcessModes.IOTA:
                result_state.append(process_state)
            elif (
                State.is_proc_closed(process_state, index)
                and event_state == ProcessModes.IOTA
            ):
                result_state.append(ProcessModes.UNDEFINED)
            elif State.is_proc_closed(process_state, index) and not isinstance(
                event_state, ProcessModes
            ):
                result_state.append(ProcessModes.ERROR)
            elif not isinstance(process_state, ProcessModes) and not isinstance(
                event_state, ProcessModes
            ):
                if not State.is_proc_closed(process_state, index):
                    if process_state != event_state:
                        result_state.append(event)
                        closed_event.add((process_state, index))
            else:
                result_state.append(None)

            if updated_state is not None:
                self._m_processes[index] = updated_state

        return result_state, closed_event

    def edges_completion(
        self, other_states: List["State"], processes_map: Dict
    ) -> None:
        """Update state processes and establish successor relationships."""
        for other_state in other_states:
            if self == other_state:
                continue

            potential_replacements = self._find_potential_replacements(
                other_state, processes_map
            )

            if potential_replacements is not None:
                self._process_potential_replacements(
                    potential_replacements, other_state
                )

        self._close_undefined_processes()

    def _find_potential_replacements(
        self, other_state: "State", processes_map: Dict
    ) -> Optional[Dict]:
        """Find potential process replacements for edge completion."""
        potential_replacements = {}

        for index, (self_proc, other_proc) in enumerate(
            zip(self.processes, other_state.processes)
        ):
            if self_proc == other_proc:
                continue
            elif isinstance(self_proc, ProcessModes) and isinstance(
                other_proc, ProcessModes
            ):
                continue

            order_differences = State.event_order_differences(
                processes_map[f"P{index + 1}"], self_proc, other_proc
            )

            if order_differences == 1:
                potential_replacements[index] = other_proc
            elif order_differences > 1:
                return None

        return potential_replacements

    def _process_potential_replacements(
        self, potential_replacements: Dict, other_state: "State"
    ) -> None:
        """Process potential replacements and establish successors."""
        potential_set = set(potential_replacements.values())
        if len(potential_set) == 1:
            self._add_successors(
                i_event=potential_set.pop(),
                i_state_name=other_state.name,
                i_state=other_state,
            )
            other_state.pre[self.name] = self.now

    def _close_undefined_processes(self) -> None:
        """Close processes that are in UNDEFINED state."""
        for index, proc in enumerate(self.processes):
            if proc == ProcessModes.UNDEFINED:
                self.processes[index] = ProcessModes.CLOSED

    @staticmethod
    def is_proc_closed(proc: Union[ProcessModes, Event], index: int) -> bool:
        """Check if process is in CLOSED state."""
        return State._get_proc_mode(proc, index) == ProcessModes.CLOSED

    @staticmethod
    def _get_proc_mode(
        proc: Union[ProcessModes, Event, List], index: int
    ) -> ProcessModes:
        """Get process mode for given process and index."""
        if isinstance(proc, Event):
            return proc.mode[index]
        elif isinstance(proc, List):
            return State._get_proc_mode(proc[index], index)
        else:
            return proc

    @staticmethod
    def event_order_differences(process, event_a, event_b) -> int:
        """Calculate order difference between two events in process history."""
        current_timestamp = process.find_event(event_a)
        other_timestamp = process.find_event(event_b)
        return abs(other_timestamp - current_timestamp)

    @staticmethod
    def get_unique_indexes(lst) -> Set[int]:
        """Get unique indexes from list."""
        unique_indexes = set()
        unique_items = set()
        for index, item in enumerate(lst):
            if str(item) not in unique_items:
                unique_items.add(str(item))
                unique_indexes.add(item[0])
        return unique_indexes

    def _initialize_formula_dict(self) -> Dict[str, bool]:
        """Initialize formula dictionary with all formulas set to False."""
        return {formula: False for formula in State.__SUBFORMULAS}
