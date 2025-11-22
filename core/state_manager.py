# core/state_manager.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Global state and frontier management for runtime verification. Handles creation,
# evaluation, and transitions of states during monitoring, including concurrency
# aspects and PCTL formula evaluation.

from typing import List, Dict, Any, Optional

from model.event import Event
from model.process import Process
from model.process_modes import ProcessModes
from model.state import State
from parser.ast import Formula
from utils.config import Config
from utils.logger import get_logger, LogCategory
from core.sliding_window_graph import SlidingWindowGraph, SlidingWindowNode


class StateManager:
    """Manages lifecycle of states (frontiers) in the monitoring process."""

    def __init__(self, config: Config, num_processes: int, formula: Formula):
        self.config = config
        self.num_processes = num_processes
        self.formula = formula
        self.states: List[State] = []
        self.processes_map: Dict[str, Process] = {}
        self.logger = get_logger()

        # Add sliding window graph from paper's algorithm
        self.sliding_window = SlidingWindowGraph(num_processes)
        self.node_to_state_map: Dict[str, State] = {}

        self._initialize_processes()
        self._initialize_states()
        self.logger.debug(
            "StateManager initialized.",
            LogCategory.STATE,
            num_processes=self.num_processes,
        )

    def _initialize_processes(self) -> None:
        """Initialize processes_map with Process objects for each process ID."""
        self.processes_map = {
            f"P{i + 1}": Process(f"P{i + 1}") for i in range(self.num_processes)
        }
        self.logger.trace(
            f"Initialized processes_map with keys: {list(self.processes_map.keys())}",
            LogCategory.STATE,
        )

    def _initialize_states(self) -> None:
        """Initialize monitoring with initial state (S0) and evaluate PCTL formula."""
        all_subformulas = Formula.collect_formulas(self.formula)

        State._State__SUBFORMULAS = all_subformulas if all_subformulas else []
        State._State__COUNTER = 0

        initial_processes_modes = [ProcessModes.IOTA] * self.num_processes
        initial_state = State(i_processes=initial_processes_modes)

        initial_verdict = self.formula.eval(state=initial_state)
        initial_state.value = initial_verdict

        self.states = [initial_state]

        # Initialize sliding window graph with initial node
        initial_node = self.sliding_window.create_or_get_node(initial_processes_modes)
        self.sliding_window.maximal_node = initial_node
        self.node_to_state_map[initial_node.node_id] = initial_state

        self.logger.info(
            f"Initial state S0 ({initial_state.name}) created and evaluated with sliding window.",
            LogCategory.STATE,
            initial_verdict=initial_verdict,
        )
        if self.config.is_debug:
            print(
                f"DEBUG_CONSOLE: S0 ({initial_state.name}) initial PCTL verdict: {initial_verdict}"
            )

    def process_event(self, event: Event) -> List[State]:
        """
        Process new event using the paper's sliding window algorithm.
        Main entry point for incorporating events into the state graph.
        """
        self.logger.debug(
            f"StateManager: Processing event '{event.name}' using sliding window algorithm.",
            LogCategory.STATE,
            event_vc=event.vector_clock,
        )
        if self.config.is_debug:
            print(f"DEBUG_CONSOLE: StateManager processing event {event.name} with paper's algorithm")

        self._attach_event_to_processes(event)

        # Use paper's algorithm: sliding window graph with backward propagation
        new_nodes = self.sliding_window.add_new_event(event)
        all_new_states = self._convert_nodes_to_states(new_nodes)

        # Evaluate PCTL on new states
        self._evaluate_pctl_on_new_states(all_new_states)

        # Add to global states list
        self.states.extend(all_new_states)

        # Establish successor relationships for all nodes after processing event
        self._establish_successor_relationships()

        self.logger.debug(
            f"Completed processing for event '{event.name}' using paper's algorithm. "
            f"Generated {len(all_new_states)} new states.",
            LogCategory.STATE,
            total_states_now=len(self.states),
        )
        if self.config.is_debug:
            print(
                f"DEBUG_CONSOLE: Event {event.name} processing generated "
                f"{len(all_new_states)} new states using paper's algorithm."
            )

        return all_new_states

    def _convert_nodes_to_states(self, nodes: List[SlidingWindowNode]) -> List[State]:
        """Convert sliding window nodes to State objects for PCTL evaluation."""
        new_states = []

        for node in nodes:
            # Check if we already have a state for this node
            if node.node_id in self.node_to_state_map:
                continue

            # Create new State from node's frontier
            state = State(i_processes=list(node.frontier))
            self.node_to_state_map[node.node_id] = state
            new_states.append(state)

            self.logger.trace(
                f"Converted node {node.node_id} to state {state.name}",
                LogCategory.STATE
            )

        return new_states

    def _establish_successor_relationships(self):
        """Convert sliding window graph edges to State successor relationships."""
        all_nodes = self.sliding_window.get_all_nodes()

        for node in all_nodes:
            if node.node_id not in self.node_to_state_map:
                continue

            source_state = self.node_to_state_map[node.node_id]

            # Add successors based on outgoing edges
            for target_node, event in node.outgoing_edges:
                if target_node.node_id in self.node_to_state_map:
                    target_state = self.node_to_state_map[target_node.node_id]

                    # Use State's internal method to add successor
                    source_state.add_successors(
                        i_event=event,
                        i_state=target_state,
                        i_state_name=target_state.name
                    )

                    self.logger.trace(
                        f"Established successor: {source_state.name} --{event.name}--> {target_state.name}",
                        LogCategory.STATE
                    )

    def _attach_event_to_processes(self, event: Event) -> None:
        """Associate event with each process involved in its execution."""
        for proc_designator_str in event.processes:
            if (
                    isinstance(proc_designator_str, str)
                    and proc_designator_str in self.processes_map
            ):
                self.processes_map[proc_designator_str].add_event(event)
                self.logger.trace(
                    f"Attached event '{event.name}' to process '{proc_designator_str}' history.",
                    LogCategory.STATE,
                )

    def _evaluate_pctl_on_new_states(self, states_to_evaluate: List[State]) -> None:
        """Evaluate PCTL formula on newly created and enabled states."""
        self.logger.debug(
            f"Evaluating PCTL formula on {len(states_to_evaluate)} new/updated states.",
            LogCategory.PCTL,
        )

        for state_obj in states_to_evaluate:
            if state_obj.enabled:
                pctl_result = self.formula.eval(state=state_obj)
                state_obj.value = pctl_result
                self.logger.trace(
                    f"State '{state_obj.name}' PCTL evaluation result: {pctl_result}",
                    LogCategory.PCTL,
                )
                if self.config.is_debug:
                    print(f"DEBUG_CONSOLE: {state_obj.name}.PCTL_value = {pctl_result}")

    def get_enabled_states(self) -> List[State]:
        """Return list of all currently enabled states."""
        return [state for state in self.states if state.enabled]

    def get_maximal_states(self) -> List[State]:
        """Return list of maximal enabled states (states with no enabled successors)."""
        maximal = []

        for state_obj in self.states:
            if state_obj.enabled and not self._has_enabled_successors(state_obj):
                maximal.append(state_obj)

        return maximal

    def _has_enabled_successors(self, state_obj: State) -> bool:
        """Check if state has any enabled successors."""
        if not state_obj.successors:
            return False

        for _succ_name, (_event, succ_obj) in state_obj.successors.items():
            if succ_obj.enabled:
                return True
        return False

    def get_final_verdict(self) -> str:
        """Determine final PCTL verdict based on maximal enabled states."""
        self.logger.debug("Determining final PCTL verdict...", LogCategory.PCTL)

        chosen_state = self._select_state_for_verdict()

        if chosen_state:
            return str(chosen_state.value).upper()

        self.logger.warn(
            "Could not determine a final verdict; no states available or an issue occurred.",
            LogCategory.PCTL,
        )
        return "UNDETERMINED (No suitable state for final verdict)"

    def _select_state_for_verdict(self) -> Optional[State]:
        """Select appropriate state for final verdict determination."""
        maximal_enabled_states = self.get_maximal_states()

        if maximal_enabled_states:
            return self._get_newest_state(maximal_enabled_states, "maximal enabled")
        elif self.states:
            enabled_states = self.get_enabled_states()
            if enabled_states:
                return self._get_newest_state(enabled_states, "enabled")
            else:
                return self._get_newest_state(self.states, "overall")

        return None

    def _get_newest_state(self, states: List[State], state_type: str) -> State:
        """Get the newest state from list and log selection."""
        states.sort(key=lambda s: int(s.name[1:]))
        newest_state = states[-1]

        if state_type == "maximal enabled":
            self.logger.info(
                f"Final verdict based on newest maximal enabled state: '{newest_state.name}'.",
                LogCategory.PCTL,
            )
        elif state_type == "enabled":
            self.logger.info(
                f"No maximal enabled states found. Using newest enabled state: '{newest_state.name}'.",
                LogCategory.PCTL,
            )
        else:
            self.logger.info(
                f"All states disabled. Using newest overall state: '{newest_state.name}'.",
                LogCategory.PCTL,
            )

        return newest_state

    def find_state_by_frontier(
            self, target_frontier_components: List[Any]
    ) -> Optional[State]:
        """Find existing enabled state that exactly matches given frontier components."""
        self.logger.trace(
            f"Searching for state with frontier: "
            f"{[str(c.name if isinstance(c, Event) else c) for c in target_frontier_components]}",
            LogCategory.STATE,
        )

        if len(target_frontier_components) != self.num_processes:
            self.logger.warn(
                f"Target frontier length ({len(target_frontier_components)}) doesn't match "
                f"num_processes ({self.num_processes}). Cannot find state.",
                LogCategory.STATE,
            )
            return None

        for state_obj in reversed(self.states):
            if not state_obj.enabled or len(state_obj.processes) != self.num_processes:
                continue

            if self._frontiers_match(target_frontier_components, state_obj.processes):
                self.logger.trace(
                    f"Found matching enabled state: '{state_obj.name}'.",
                    LogCategory.STATE,
                )
                return state_obj

        self.logger.trace(
            "No enabled state found matching the target frontier.", LogCategory.STATE
        )
        return None

    def _frontiers_match(
            self, target_frontier: List[Any], state_frontier: List[Any]
    ) -> bool:
        """Check if two frontiers match exactly."""
        for i in range(self.num_processes):
            target_comp = target_frontier[i]
            state_comp = state_frontier[i]

            if type(target_comp) != type(state_comp):
                return False

            if isinstance(target_comp, Event):
                if target_comp is not state_comp:
                    return False
            elif isinstance(target_comp, ProcessModes):
                if target_comp != state_comp:
                    return False
            else:
                return False

        return True
