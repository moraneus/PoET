# core/state_manager.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Global state and frontier management for runtime verification. Handles creation,
# evaluation, and transitions of states during monitoring, including concurrency
# aspects and PCTL formula evaluation.

from typing import List, Dict, Set, Tuple, Any, Optional

from model.event import Event
from model.process import Process
from model.process_modes import ProcessModes
from model.state import State
from parser.ast import Formula
from utils.config import Config
from utils.logger import get_logger, LogCategory


class StateManager:
    """Manages lifecycle of states (frontiers) in the monitoring process."""

    def __init__(self, config: Config, num_processes: int, formula: Formula):
        self.config = config
        self.num_processes = num_processes
        self.formula = formula
        self.states: List[State] = []
        self.processes_map: Dict[str, Process] = {}
        self.recent_events: List[Event] = []
        self.max_recent_events: int = 10
        self.logger = get_logger()

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

        self.logger.info(
            f"Initial state S0 ({initial_state.name}) created and evaluated.",
            LogCategory.STATE,
            initial_verdict=initial_verdict,
        )
        if self.config.is_debug:
            print(
                f"DEBUG_CONSOLE: S0 ({initial_state.name}) initial PCTL verdict: {initial_verdict}"
            )

    def process_event(self, event: Event) -> List[State]:
        """
        Process new event to generate subsequent states.
        Main entry point for incorporating events into the state graph.
        """
        self.logger.debug(
            f"StateManager: Processing event '{event.name}'.",
            LogCategory.STATE,
            event_vc=event.vector_clock,
        )
        if self.config.is_debug:
            print(f"DEBUG_CONSOLE: StateManager processing event {event.name}")

        # Special handling for INIT event - update S0's propositions and re-evaluate
        if event.name == "INIT":
            return self._process_init_event(event)

        self._update_recent_events(event)
        self._attach_event_to_processes(event)

        concurrent_events = self._find_concurrent_events(event, self.recent_events[:-1])
        self._log_concurrent_events_if_debug(event, concurrent_events)

        # Generate direct successor states
        direct_states, closed_events_info = self._find_new_states_from_event(event)
        all_new_states = list(direct_states)

        # Handle concurrent event interleavings
        if concurrent_events:
            concurrent_states = self._create_states_for_concurrent_interleaving(
                event, concurrent_events
            )
            all_new_states.extend(
                self._filter_unique_states(concurrent_states, all_new_states)
            )

        # Complete processing pipeline
        self._update_event_modes_after_superseded(closed_events_info)
        self._complete_graph_edges(all_new_states)
        self._evaluate_pctl_on_new_states(all_new_states)
        self._disable_states_with_all_processes_closed()

        if self.config.reduce_enabled:
            self._apply_full_reduction_of_disabled_states()

        self._add_unique_states_to_global_list(all_new_states)

        self.logger.debug(
            f"Completed processing for event '{event.name}'. Generated {len(all_new_states)} new unique states.",
            LogCategory.STATE,
            total_states_now=len(self.states),
        )
        if self.config.is_debug:
            print(
                f"DEBUG_CONSOLE: Event {event.name} processing generated {len(all_new_states)} new states."
            )

        return all_new_states

    def _process_init_event(self, event: Event) -> List[State]:
        """
        Process INIT event specially - update initial state S0 with INIT propositions.
        INIT event represents the initial configuration, not a transition.
        """
        self.logger.debug(
            f"Processing INIT event with propositions: {event.propositions}",
            LogCategory.STATE,
        )

        if not self.states or self.states[0].name != "S0":
            self.logger.error(
                "No initial state S0 found when processing INIT event",
                LogCategory.ERROR,
            )
            return []

        initial_state = self.states[0]

        # Update S0's propositions with INIT event propositions
        if event.propositions:
            # Update the state's propositions
            initial_state._State__m_propositions.update(event.propositions)

            # Re-evaluate PCTL formula with updated propositions
            initial_verdict = self.formula.eval(state=initial_state)
            initial_state.value = initial_verdict

            self.logger.info(
                f"Updated S0 with INIT propositions {event.propositions}, new verdict: {initial_verdict}",
                LogCategory.STATE,
            )

            if self.config.is_debug:
                print(
                    f"DEBUG_CONSOLE: S0 updated with INIT propositions: {event.propositions}, verdict: {initial_verdict}"
                )

        # INIT doesn't create new states, just updates S0
        return []

    def _update_recent_events(self, event: Event) -> None:
        """Update recent events sliding window."""
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events.pop(0)

    def _log_concurrent_events_if_debug(
        self, event: Event, concurrent_events: List[Event]
    ) -> None:
        """Log concurrent events information if debug mode is enabled."""
        if concurrent_events and self.config.is_debug:
            concurrent_names = [e.name for e in concurrent_events]
            print(
                f"DEBUG_CONSOLE: Event {event.name} identified as concurrent with: {concurrent_names}"
            )
            self.logger.debug(
                f"Event '{event.name}' concurrent with: {concurrent_names}",
                LogCategory.STATE,
            )

    def _filter_unique_states(
        self, new_states: List[State], existing_states: List[State]
    ) -> List[State]:
        """Filter out duplicate states based on frontier composition."""
        unique_states = []
        for state in new_states:
            # Check against both existing_states and global states
            is_duplicate = any(
                existing_s.processes == state.processes
                for existing_s in existing_states
            ) or any(s.processes == state.processes for s in self.states)

            if not is_duplicate:
                unique_states.append(state)
            else:
                # Clean up successor references before discarding
                self._remove_successor_references(state)
                self.logger.trace(
                    f"Filtered out duplicate state {state.name} with frontier: {[str(p) for p in state.processes]}",
                    LogCategory.STATE,
                )

        return unique_states

    def _add_unique_states_to_global_list(self, new_states: List[State]) -> None:
        """Add unique new states to global states list."""
        for new_s in new_states:
            if not any(
                s.processes == new_s.processes and s.name != new_s.name
                for s in self.states
            ):
                self.states.append(new_s)

    def _are_concurrent(self, vc1: List[int], vc2: List[int]) -> bool:
        """Check if two vector clocks represent concurrent events."""
        if len(vc1) != len(vc2):
            self.logger.warn(
                "Attempted to compare vector clocks of different lengths.",
                LogCategory.VECTOR_CLOCK,
                vc1_len=len(vc1),
                vc2_len=len(vc2),
            )
            return False

        vc1_less_eq_vc2 = all(vc1[i] <= vc2[i] for i in range(len(vc1)))
        vc2_less_eq_vc1 = all(vc2[i] <= vc1[i] for i in range(len(vc2)))

        return (
            not (vc1_less_eq_vc2 and any(vc1[i] < vc2[i] for i in range(len(vc1))))
            and not (vc2_less_eq_vc1 and any(vc2[i] < vc1[i] for i in range(len(vc1))))
            and (vc1 != vc2)
        )

    def _find_concurrent_events(
        self, current_event: Event, events_to_check: List[Event]
    ) -> List[Event]:
        """Find events concurrent with current_event based on vector clocks."""
        concurrent_events = []
        current_event_vc = current_event.vector_clock

        for recent_event in events_to_check:
            if hasattr(recent_event, "vector_clock") and self._are_concurrent(
                current_event_vc, recent_event.vector_clock
            ):
                concurrent_events.append(recent_event)

        return concurrent_events

    def _create_states_for_concurrent_interleaving(
        self, current_event: Event, concurrent_events: List[Event]
    ) -> List[State]:
        """Create intermediate states by exploring alternative orderings of concurrent events."""
        intermediate_states = []
        if self.config.is_debug:
            print(
                f"DEBUG_CONSOLE: StateManager attempting to create intermediate states for '{current_event.name}' due to concurrency."
            )

        self.logger.debug(
            f"Exploring concurrent interleavings for '{current_event.name}' with {len(concurrent_events)} concurrent events.",
            LogCategory.STATE,
        )

        for concurrent_e in concurrent_events:
            candidate_states = self._find_candidate_states_before_event(concurrent_e)
            intermediate_states.extend(
                self._create_states_from_candidates(current_event, candidate_states)
            )

        return intermediate_states

    def _create_states_from_candidates(
        self, current_event: Event, candidate_states: List[State]
    ) -> List[State]:
        """Create new states by applying current_event to candidate states."""
        new_states = []

        for candidate_state in candidate_states:
            if not candidate_state.enabled:
                continue

            self.logger.trace(
                f"Testing concurrent path: Applying '{current_event.name}' to state '{candidate_state.name}'.",
                LogCategory.STATE,
            )

            new_state, _ = candidate_state | current_event

            if new_state is not None:
                if not self._is_duplicate_frontier(new_state, new_states):
                    new_states.append(new_state)
                    self.logger.debug(
                        f"Added new intermediate state '{new_state.name}' from concurrent path exploration.",
                        LogCategory.STATE,
                    )
                else:
                    self.logger.trace(
                        f"Intermediate state candidate resulted in duplicate frontier; discarding {new_state.name}.",
                        LogCategory.STATE,
                    )
                    State._State__COUNTER -= 1

        return new_states

    def _is_duplicate_frontier(
        self, new_state: State, existing_states: List[State]
    ) -> bool:
        """Check if new_state has duplicate frontier in existing states or global states."""
        return any(s.processes == new_state.processes for s in self.states) or any(
            s.processes == new_state.processes for s in existing_states
        )

    def _find_candidate_states_before_event(self, specific_event: Event) -> List[State]:
        """Find recently enabled states whose frontiers do NOT contain specific_event."""
        candidate_states = []

        for state_obj in reversed(self.states):
            if not state_obj.enabled:
                continue

            if not self._event_in_state_frontier(specific_event, state_obj):
                candidate_states.append(state_obj)
                if len(candidate_states) >= 3:
                    break

        self.logger.trace(
            f"Found {len(candidate_states)} candidate states before event '{specific_event.name}': "
            f"{[s.name for s in reversed(candidate_states)]}",
            LogCategory.STATE,
        )

        return list(reversed(candidate_states))

    def _event_in_state_frontier(self, event: Event, state: State) -> bool:
        """Check if event is in the state's frontier."""
        return any(
            process_comp is event
            for process_comp in state.processes
            if isinstance(process_comp, Event)
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

    def _find_new_states_from_event(
        self, event: Event
    ) -> Tuple[List[State], Set[Tuple[Event, int]]]:
        """Generate direct successor states by applying event to all enabled states."""
        newly_created_states: List[State] = []
        all_closed_events_info: Set[Tuple[Event, int]] = set()

        self.logger.debug(
            f"Finding direct new states from event '{event.name}' applied to enabled states.",
            LogCategory.STATE,
        )

        enabled_states = self.get_enabled_states()

        for current_state in enabled_states:
            new_state, closed_events = self._create_successor_state(
                current_state, event
            )

            if new_state is not None:
                if not self._is_duplicate_in_batch(new_state, newly_created_states):
                    newly_created_states.append(new_state)
                    self.logger.trace(
                        f"Created new direct state '{new_state.name}' from '{current_state.name}' | '{event.name}'.",
                        LogCategory.STATE,
                    )
                    if closed_events:
                        all_closed_events_info.update(closed_events)
                else:
                    self._handle_duplicate_state(
                        new_state, current_state, event, newly_created_states
                    )

        self.logger.debug(
            f"Found {len(newly_created_states)} new unique direct states from event '{event.name}'.",
            LogCategory.STATE,
        )
        return newly_created_states, all_closed_events_info

    def _create_successor_state(
        self, current_state: State, event: Event
    ) -> Tuple[Optional[State], Set[Tuple[Event, int]]]:
        """Create successor state from current state and event."""
        return current_state | event

    def _is_duplicate_in_batch(
        self, new_state: State, newly_created_states: List[State]
    ) -> bool:
        """Check if new_state has duplicate frontier in current batch."""
        return any(s.processes == new_state.processes for s in newly_created_states)

    def _find_duplicate_in_batch(
        self, new_state: State, newly_created_states: List[State]
    ) -> Optional[State]:
        """Find and return the existing state with matching frontier, or None."""
        for s in newly_created_states:
            if s.processes == new_state.processes:
                return s
        return None

    def _handle_duplicate_state(
        self,
        duplicate_state: State,
        source_state: State,
        event: Event,
        newly_created_states: List[State],
    ) -> None:
        """Handle duplicate state creation by merging predecessor relationships.

        When multiple enabled states transition to the same frontier (diamond pattern),
        we keep only one state but add all source states as predecessors.
        """
        self.logger.trace(
            f"Duplicate frontier resulted from '{source_state.name}' | '{event.name}'. "
            f"Discarding candidate {duplicate_state.name}.",
            LogCategory.STATE,
        )

        # Find the existing state with matching frontier and add source_state as predecessor
        existing_state = self._find_duplicate_in_batch(
            duplicate_state, newly_created_states
        )
        if existing_state is not None:
            # Add source_state's valuation as a predecessor of the existing state
            existing_state.pre[source_state.name] = source_state.now
            # Also establish successor relationship from source_state to existing_state
            source_state._add_successors(
                i_event=event, i_state_name=existing_state.name, i_state=existing_state
            )
            self.logger.trace(
                f"Added '{source_state.name}' as additional predecessor of '{existing_state.name}'.",
                LogCategory.STATE,
            )

        State._State__COUNTER -= 1

    def _update_event_modes_after_superseded(
        self, closed_events_info: Set[Tuple[Event, int]]
    ) -> None:
        """Update mode of events superseded by new events."""
        if not closed_events_info:
            return

        self.logger.trace(
            f"Updating modes for {len(closed_events_info)} superseded frontier events.",
            LogCategory.STATE,
        )

        for event_obj, process_idx in closed_events_info:
            if isinstance(event_obj, Event):
                event_obj.update_mode(ProcessModes.CLOSED, process_idx)
                self.logger.trace(
                    f"Set mode of event '{event_obj.name}' to CLOSED for process index {process_idx}.",
                    LogCategory.STATE,
                )

    def _disable_states_with_all_processes_closed(self) -> None:
        """Disable states where all processes in their frontier are in CLOSED mode."""
        disabled_count = 0

        for state_obj in self.states:
            if state_obj.enabled and self._is_state_fully_closed(state_obj):
                state_obj.enabled = False
                disabled_count += 1
                self.logger.debug(
                    f"Disabled state '{state_obj.name}' as all its process frontiers are closed.",
                    LogCategory.STATE,
                )
                if self.config.is_debug:
                    print(
                        f"DEBUG_CONSOLE: Disabling state {state_obj.name} (all processes components closed)"
                    )

        if disabled_count > 0:
            self.logger.info(
                f"Disabled {disabled_count} states where all process frontiers are closed.",
                LogCategory.STATE,
            )

    def _is_state_fully_closed(self, state_obj: State) -> bool:
        """Check if all components in state's frontier are effectively closed."""
        if not state_obj.processes or len(state_obj.processes) != self.num_processes:
            if len(state_obj.processes) != self.num_processes:
                self.logger.warn(
                    f"State '{state_obj.name}' has inconsistent number of process components "
                    f"({len(state_obj.processes)}) vs system ({self.num_processes}). Cannot determine if fully closed.",
                    LogCategory.STATE,
                )
            return False

        for i in range(self.num_processes):
            if not State.is_proc_closed(state_obj.processes[i], i):
                return False
        return True

    def _complete_graph_edges(self, new_states_this_step: List[State]) -> None:
        """Complete graph edges between states to form proper predecessor/successor relationships.

        This handles both:
        1. Edges between new states created in the same step
        2. Edges from existing states to new states (for diamond patterns in concurrent execution)
        """
        self.logger.debug(
            f"Performing edge completion for {len(new_states_this_step)} new states.",
            LogCategory.STATE,
        )

        # Complete edges between new states created in this step
        for i, new_state in enumerate(new_states_this_step):
            if new_state.enabled:
                new_state.edges_completion(
                    new_states_this_step[i + 1 :], self.processes_map
                )

        # Also check existing states as potential predecessors for new states
        # This handles diamond patterns where concurrent events join at a common successor
        for existing_state in self.states:
            if not existing_state.enabled:
                continue
            # Check if existing_state could be an immediate predecessor of any new state
            existing_state.edges_completion(new_states_this_step, self.processes_map)

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

    def _apply_full_reduction_of_disabled_states(self) -> None:
        """Remove all disabled states from main states list if reduction is enabled."""
        if not self.config.reduce_enabled:
            return

        original_state_count = len(self.states)
        states_before_reduction = [s.name for s in self.states if not s.enabled]

        self.states = [s for s in self.states if s.enabled]

        num_removed = original_state_count - len(self.states)
        if num_removed > 0:
            self.logger.info(
                f"State reduction applied: Removed {num_removed} disabled states. "
                f"(States disabled: {states_before_reduction})",
                LogCategory.STATE,
            )
            if self.config.is_debug:
                print(f"DEBUG_CONSOLE: State reduction removed {num_removed} states.")

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
        """Get newest state from list and log selection."""
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

    def _remove_successor_references(self, duplicate_state: State) -> None:
        """Remove references to a duplicate state from all existing states' successors."""
        state_name = duplicate_state.name

        for existing_state in self.states:
            # Remove from successors if present
            if state_name in existing_state.successors:
                del existing_state.successors[state_name]
                self.logger.trace(
                    f"Removed successor reference {state_name} from {existing_state.name}",
                    LogCategory.STATE,
                )
