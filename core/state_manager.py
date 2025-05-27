# core/state_manager.py
"""State management for the PoET monitor."""

from typing import List, Dict, Set, Tuple, Any
from model.event import Event
from model.process import Process
from model.process_modes import ProcessModes
from model.state import State
from parser.ast import Formula
from utils.config import Config


class StateManager:
    """Manages state creation, evaluation, and transitions."""

    def __init__(self, config: Config, num_processes: int, formula: Formula):
        """Initialize state manager.

        Args:
            config: Configuration object
            num_processes: Number of processes in the system
            formula: PCTL formula to evaluate
        """
        self.config = config
        self.num_processes = num_processes
        self.formula = formula
        self.states: List[State] = []
        self.processes_map: Dict[str, Process] = {}

        # Initialize
        self._initialize_processes()
        self._initialize_states()

    def _initialize_processes(self) -> None:
        """Initialize process map."""
        self.processes_map = {
            f"P{i + 1}": Process(f"P{i + 1}")
            for i in range(self.num_processes)
        }

    def _initialize_states(self) -> None:
        """Initialize the initial state S0."""
        all_subformulas = Formula.collect_formulas(self.formula)

        # Set class variables
        if all_subformulas:
            State._State__SUBFORMULAS = all_subformulas
        else:
            State._State__SUBFORMULAS = []
        State._State__COUNTER = 0

        # Create initial state
        initial_state = State(
            i_processes=[ProcessModes.IOTA] * self.num_processes,
            i_formulas=all_subformulas
        )

        # Evaluate initial state
        initial_verdict = self.formula.eval(state=initial_state)
        initial_state.value = initial_verdict

        self.states = [initial_state]

        if self.config.is_debug:
            print(f"DEBUG: S0 ({initial_state.name}) initial PCTL verdict: {initial_verdict}")

    def process_event(self, event: Event) -> List[State]:
        """Process an event and generate new states.

        Args:
            event: Event to process

        Returns:
            List of newly created states
        """
        if self.config.is_debug:
            print(f"DEBUG: Processing event {event.name}")

        # Attach event to processes
        self._attach_event_to_processes(event)

        # Generate new states
        new_states, closed_events = self._find_new_states(event)

        # Update closed events
        self._update_closed_events(closed_events)

        # Disable states with all closed processes
        self._disable_completed_states()

        # Complete edges for new states
        self._complete_edges(new_states)

        # Evaluate new states
        self._evaluate_states(new_states)

        # Apply reduction if enabled
        if self.config.reduce_enabled:
            self._apply_reduction()

        # Add new states to collection
        self.states.extend(new_states)

        if self.config.is_debug:
            print(f"DEBUG: Generated {len(new_states)} new states")

        return new_states

    def _attach_event_to_processes(self, event: Event) -> None:
        """Attach event to the processes it belongs to."""
        for proc_designator in event.processes:
            if isinstance(proc_designator, str) and proc_designator in self.processes_map:
                self.processes_map[proc_designator].add_event(event)

    def _find_new_states(self, event: Event) -> Tuple[List[State], Set[Tuple[Event, int]]]:
        """Find new states by applying event to current enabled states."""
        new_states = []
        all_closed_events = set()

        for state in self.states:
            if state.enabled:
                new_state, closed_events = state | event
                if new_state is not None:
                    new_states.append(new_state)
                    if closed_events:
                        all_closed_events.update(closed_events)

        return new_states, all_closed_events

    def _update_closed_events(self, closed_events: Set[Tuple[Event, int]]) -> None:
        """Update mode of closed events."""
        for event_obj, index in filter(None, closed_events):
            if isinstance(event_obj, Event):
                event_obj.update_mode(ProcessModes.CLOSED, index)

    def _disable_completed_states(self) -> None:
        """Disable states where all processes are closed."""
        for state in self.states:
            if state.enabled and self._all_processes_closed(state):
                if self.config.is_debug:
                    print(f"DEBUG: Disabling state {state.name} (all processes closed)")
                state.enabled = False

    def _all_processes_closed(self, state: State) -> bool:
        """Check if all processes in a state are closed."""
        if not state.processes:
            return False

        for i in range(len(state.processes)):
            if not State.is_proc_closed(state.processes[i], i):
                return False
        return True

    def _complete_edges(self, new_states: List[State]) -> None:
        """Complete edges for new states."""
        for i, state in enumerate(new_states):
            state.edges_completion(new_states[i:], self.processes_map)

    def _evaluate_states(self, new_states: List[State]) -> None:
        """Evaluate PCTL formula on new states."""
        for state in new_states:
            if state.enabled:
                result = self.formula.eval(state=state)
                state.value = result

                if self.config.is_debug:
                    print(f"DEBUG: {state.name}.value = {result}")

    def _apply_reduction(self) -> None:
        """Remove disabled states if reduction is enabled."""
        i = len(self.states) - 1
        while i >= 0:
            if not self.states[i].enabled:
                if self.config.is_debug:
                    print(f"DEBUG: Removing disabled state {self.states[i].name}")
                del self.states[i]
            i -= 1

    def get_enabled_states(self) -> List[State]:
        """Get all enabled states."""
        return [state for state in self.states if state.enabled]

    def get_maximal_states(self) -> List[State]:
        """Get maximal states (states with no successors)."""
        return [state for state in self.states if not state.successors and state.enabled]

    def get_final_verdict(self) -> str:
        """Get the final verdict from maximal states."""
        maximal_states = self.get_maximal_states()

        if maximal_states:
            return str(maximal_states[0].value).upper()
        elif self.states:
            # Fallback to newest state
            newest_states = sorted(self.states, key=lambda s: int(s.name[1:]), reverse=True)
            if newest_states:
                return str(newest_states[0].value).upper()

        return "UNDETERMINED"

    def find_state_by_frontier(self, target_frontier: List[Any]) -> State | None:
        """Find state matching a specific frontier definition.

        Args:
            target_frontier: List of events/modes defining the frontier

        Returns:
            Matching state or None
        """
        for state in reversed(self.states):
            if not state.enabled or len(state.processes) != self.num_processes:
                continue

            # Check exact match
            is_match = True
            for i in range(self.num_processes):
                target_comp = target_frontier[i]
                state_comp = state.processes[i]

                if type(target_comp) != type(state_comp):
                    is_match = False
                    break

                if isinstance(target_comp, Event):
                    if target_comp is not state_comp:
                        is_match = False
                        break
                elif isinstance(target_comp, ProcessModes):
                    if target_comp != state_comp:
                        is_match = False
                        break

            if is_match:
                return state

        return None
