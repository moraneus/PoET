# core/max_state_tracker.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Manages tracking and reporting of maximal frontier states for the 'max_state'
# output mode, interfacing with StateManager and VectorClockManager to determine
# and format current global state information.

import sys
from typing import List, Any, Dict, Set, Optional

from model.event import Event
from model.process import Process
from model.process_modes import ProcessModes
from model.state import State
from core.state_manager import StateManager
from core.vector_clock_manager import VectorClockManager
from graphics.prints import Prints
from utils.config import Config
from utils.logger import get_logger, LogCategory, LogLevel


class MaxStateTracker:
    """Tracks and reports maximal state (frontier) information for console output."""

    def __init__(
        self,
        state_manager: StateManager,
        vc_manager: VectorClockManager,
        processes_map: Dict[str, Process],
        num_processes: int,
        config: Config,
        process_aliases_override: Optional[List[str]] = None,
    ):
        self.state_manager = state_manager
        self.vc_manager = vc_manager
        self.processes_map = processes_map
        self.num_processes = num_processes
        self.config = config
        self.history: List[str] = []
        self.logger = get_logger()
        self.all_seen_propositions: Set[str] = set()

        self.proc_aliases = self._initialize_process_aliases(process_aliases_override)

        self.logger.debug(
            f"MaxStateTracker initialized for {num_processes} processes.",
            LogCategory.STATE,
            final_aliases=self.proc_aliases,
        )

    def _initialize_process_aliases(
        self, process_aliases_override: Optional[List[str]]
    ) -> List[str]:
        """Initialize process aliases with override or defaults."""
        if (
            process_aliases_override
            and len(process_aliases_override) == self.num_processes
        ):
            self.logger.trace(
                f"MaxStateTracker using provided process aliases: {process_aliases_override}",
                LogCategory.STATE,
            )
            return process_aliases_override
        else:
            default_aliases = self._generate_default_process_aliases()
            if process_aliases_override:
                self.logger.warn(
                    f"MaxStateTracker: process_aliases_override was invalid (length mismatch or None). "
                    f"Defaulting to {default_aliases}.",
                    LogCategory.STATE,
                )
            return default_aliases

    def _generate_default_process_aliases(self) -> List[str]:
        """Generate default process aliases like 'P1', 'P2', etc."""
        aliases = [f"P{i + 1}" for i in range(self.num_processes)]
        self.logger.trace(
            f"Generated default process aliases: {aliases}", LogCategory.STATE
        )
        return aliases

    def track_frontier_state(
        self, triggering_event_name: str, event_obj: Optional[Event] = None
    ) -> None:
        """
        Determine current global state and print formatted output to console.
        Primary method for 'max_state' output mode.
        """
        self.logger.debug(
            f"MaxStateTracker: Formatting 'max_state' console output for trigger: '{triggering_event_name}'.",
            LogCategory.STATE,
        )

        current_expected_vc = self.vc_manager.expected_vc
        vc_str = self._format_vector_clock_display(current_expected_vc)

        target_frontier_components = self._build_target_frontier_from_current_vc()
        current_system_state = self.state_manager.find_state_by_frontier(
            target_frontier_components
        )

        state_info = self._extract_state_information(
            current_system_state,
            triggering_event_name,
            current_expected_vc,
            target_frontier_components,
            event_obj,
        )

        output_line = self._format_output_line(
            triggering_event_name, vc_str, state_info
        )
        self._print_and_store_output(output_line)

    def _format_vector_clock_display(self, current_expected_vc: List[int]) -> str:
        """Format vector clock for display."""
        vc_parts = [
            f"{self.proc_aliases[i]}:{current_expected_vc[i]}"
            for i in range(min(self.num_processes, len(self.proc_aliases)))
        ]
        return f"[{','.join(vc_parts)}]"

    def _extract_state_information(
        self,
        current_system_state: Optional[State],
        triggering_event_name: str,
        current_expected_vc: List[int],
        target_frontier_components: List[Any],
        event_obj: Optional[Event],
    ) -> Dict[str, str]:
        """Extract and format state information for display."""
        if current_system_state:
            state_props = current_system_state.propositions
            propositions_display = (
                str(sorted(list(state_props))) if state_props else "[]"
            )

            if state_props:
                self.all_seen_propositions.update(state_props)

            verdict_bool = current_system_state.value
            verdict_display = "TRUE" if verdict_bool else "FALSE"
            verdict_emoji = "✅" if verdict_bool else "❌"

            if self.logger._should_log(LogLevel.DEBUG, LogCategory.STATE):
                self._log_frontier_details_to_file(
                    triggering_event_name, current_system_state, event_obj
                )

            return {
                "state_name": current_system_state.name,
                "propositions": propositions_display,
                "verdict": verdict_display,
                "emoji": verdict_emoji,
            }
        else:
            self._log_state_not_found_warning(
                triggering_event_name, current_expected_vc, target_frontier_components
            )
            return {
                "state_name": "<state_not_found>",
                "propositions": "[]",
                "verdict": "NOT_FOUND",
                "emoji": "❓",
            }

    def _log_state_not_found_warning(
        self,
        triggering_event_name: str,
        current_expected_vc: List[int],
        target_frontier_components: List[Any],
    ) -> None:
        """Log warning when state corresponding to current VC is not found."""
        self.logger.warn(
            f"MaxStateTracker: State for VC (triggered by '{triggering_event_name}') NOT FOUND.",
            LogCategory.STATE,
            current_vc=current_expected_vc,
            target_frontier_repr=[
                (comp.name if isinstance(comp, Event) else str(comp))
                for comp in target_frontier_components
            ],
        )

    def _format_output_line(
        self, triggering_event_name: str, vc_str: str, state_info: Dict[str, str]
    ) -> str:
        """Format the complete output line for console display."""
        return (
            f"{triggering_event_name}:{vc_str} → state={state_info['state_name']}, "
            f"props={state_info['propositions']}, verdict={state_info['verdict']} {state_info['emoji']}"
        )

    def _print_and_store_output(self, output_line: str) -> None:
        """Print output line to console and store in history if debug mode."""
        print(output_line)
        sys.stdout.flush()

        if self.config.is_debug:
            self.history.append(output_line)

        self.logger.increment_counter("max_state_lines_printed_to_console")

    def _log_frontier_details_to_file(
        self,
        triggering_event_name: str,
        state: State,
        event_obj: Optional[Event] = None,
    ) -> None:
        """Log detailed frontier information to log file when DEBUG level is active."""
        frontier_details, proposition_sources = self._build_frontier_details(state)

        self.logger.debug(
            f"MaxStateTracker Detail: Frontier for '{triggering_event_name}' (State '{state.name}'):",
            LogCategory.STATE,
        )
        self.logger.indent()

        for alias, item_name in frontier_details.items():
            self.logger.debug(f"{alias}: {item_name}", LogCategory.STATE)

        self._log_state_propositions(state, proposition_sources)
        self.logger.debug(f"State PCTL verdict: {state.value}", LogCategory.STATE)
        self.logger.dedent()

    def _build_frontier_details(self, state: State) -> tuple[Dict[str, str], List[str]]:
        """Build frontier details and proposition sources for logging."""
        frontier_details: Dict[str, str] = {}
        proposition_sources: List[str] = []

        for i, component_in_frontier in enumerate(state.processes):
            proc_alias_display = (
                self.proc_aliases[i]
                if i < len(self.proc_aliases)
                else f"P{i + 1}_unaliased"
            )

            if isinstance(component_in_frontier, Event):
                frontier_details[proc_alias_display] = component_in_frontier.name
                props = component_in_frontier.propositions
                prop_str = str(sorted(list(props))) if props else "[]"
                proposition_sources.append(
                    f"{proc_alias_display}:{component_in_frontier.name} -> {prop_str}"
                )
            elif isinstance(component_in_frontier, ProcessModes):
                frontier_details[proc_alias_display] = str(component_in_frontier.value)
                proposition_sources.append(
                    f"{proc_alias_display}:{component_in_frontier.value} -> []"
                )
            else:
                frontier_details[proc_alias_display] = "<unknown_component_type>"
                proposition_sources.append(
                    f"{proc_alias_display}:<unknown_component_type> -> []"
                )

        return frontier_details, proposition_sources

    def _log_state_propositions(
        self, state: State, proposition_sources: List[str]
    ) -> None:
        """Log state propositions and their sources."""
        state_propositions = (
            state.propositions if state.propositions is not None else set()
        )
        if state_propositions:
            self.logger.debug(
                f"State propositions: {sorted(list(state_propositions))}",
                LogCategory.STATE,
            )
            self.logger.debug(
                "Proposition sources (from individual frontier events):",
                LogCategory.STATE,
            )
            for source_info in proposition_sources:
                self.logger.debug(f"  {source_info}", LogCategory.STATE)
        else:
            self.logger.debug("No propositions in this state.", LogCategory.STATE)

    def _build_target_frontier_from_current_vc(self) -> List[Any]:
        """Build target frontier based on current expected_vc from vc_manager."""
        target_frontier = []
        current_expected_vc = self.vc_manager.expected_vc
        self.logger.trace(
            "MaxStateTracker: Building target frontier components from current VC.",
            LogCategory.STATE,
            expected_vc=current_expected_vc,
        )

        for i in range(self.num_processes):
            process_map_key = f"P{i + 1}"
            event_count_for_process = current_expected_vc[i]

            if event_count_for_process > 0:
                event = self._get_event_for_process(
                    process_map_key, event_count_for_process
                )
                target_frontier.append(event)
            else:
                target_frontier.append(ProcessModes.IOTA)

        return target_frontier

    def _get_event_for_process(
        self, process_map_key: str, event_count_for_process: int
    ) -> Any:
        """Get event for process or return IOTA if not found."""
        process_object = self.processes_map.get(process_map_key)
        if process_object and event_count_for_process <= len(process_object.events):
            return process_object.events[event_count_for_process - 1]
        else:
            self.logger.warn(
                f"MaxStateTracker: Event at count {event_count_for_process} not found for {process_map_key}. "
                f"(Process has {len(process_object.events) if process_object else 'N/A'} events). Using IOTA.",
                LogCategory.STATE,
            )
            return ProcessModes.IOTA

    def print_history_summary(self) -> None:
        """Print collected history of 'max_state' lines if debug was active."""
        if not self.history:
            self.logger.debug(
                "No MaxStateTracker history to display (history list is empty or debug was off).",
                LogCategory.STATE,
            )
            return

        self.logger.info(
            f"MaxStateTracker history (collected during debug): {len(self.history)} entries.",
            LogCategory.STATE,
        )
        Prints.seperator(
            "MAXIMAL STATES HISTORY (Collected by MaxStateTracker during debug)"
        )
        for summary_line in self.history:
            print(summary_line)
        Prints.seperator("END MAXIMAL STATES HISTORY")

    def clear_history(self) -> None:
        """Clear the collected history list."""
        num_cleared = len(self.history)
        self.history.clear()
        self.logger.debug(
            f"Cleared MaxStateTracker history: {num_cleared} entries removed.",
            LogCategory.STATE,
        )

    def get_execution_summary(self) -> Dict[str, Any]:
        """Return summary of tracking activities."""
        return {
            "frontier_states_tracked_console": self.logger.get_counter(
                "max_state_lines_printed_to_console"
            ),
            "history_entries_debug": len(self.history),
            "process_aliases_used": self.proc_aliases,
            "num_processes": self.num_processes,
            "all_seen_propositions_unique": sorted(list(self.all_seen_propositions)),
            "total_unique_propositions_seen": len(self.all_seen_propositions),
        }

    def analyze_state_transitions(self) -> Dict[str, Any]:
        """Analyze verdict transitions from collected history if debug was active."""
        if len(self.history) < 2:
            return {
                "transitions_count": 0,
                "analysis_notes": "Insufficient history data (or debug was off) for transition analysis.",
            }

        verdicts_in_history = self._extract_verdicts_from_history()
        transitions_found = self._find_verdict_transitions(verdicts_in_history)

        return {
            "total_history_points_analyzed": len(self.history),
            "verdict_changes_count": len(transitions_found),
            "transitions_list": transitions_found,
            "final_verdict_in_history": (
                verdicts_in_history[-1] if verdicts_in_history else "UNKNOWN"
            ),
            "unique_verdicts_observed_in_history": (
                list(set(verdicts_in_history)) if verdicts_in_history else []
            ),
        }

    def _extract_verdicts_from_history(self) -> List[str]:
        """Extract verdict values from history entries."""
        verdicts = []
        for history_entry_str in self.history:
            if "verdict=" in history_entry_str:
                try:
                    verdict_value_str = history_entry_str.split("verdict=")[1].split(
                        " "
                    )[0]
                    verdicts.append(verdict_value_str)
                except IndexError:
                    verdicts.append("PARSE_ERROR_IN_HISTORY_LINE")
        return verdicts

    def _find_verdict_transitions(
        self, verdicts_in_history: List[str]
    ) -> List[Dict[str, Any]]:
        """Find transitions between different verdict values."""
        transitions = []
        for i in range(1, len(verdicts_in_history)):
            if verdicts_in_history[i] != verdicts_in_history[i - 1]:
                transitions.append(
                    {
                        "from_verdict": verdicts_in_history[i - 1],
                        "to_verdict": verdicts_in_history[i],
                        "at_history_step_index": i,
                    }
                )
        return transitions

    def __str__(self) -> str:
        return (
            f"MaxStateTracker(processes={self.num_processes}, "
            f"history_len_debug={len(self.history)}, "
            f"seen_props_count={len(self.all_seen_propositions)})"
        )

    def __repr__(self) -> str:
        return self.__str__()
