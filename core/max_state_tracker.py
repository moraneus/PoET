# core/max_state_tracker.py
"""Max state tracking for detailed frontier analysis."""

from typing import List, Any, Dict
from model.event import Event
from model.process import Process
from model.process_modes import ProcessModes
from model.state import State
from core.state_manager import StateManager
from core.vector_clock_manager import VectorClockManager
from graphics.prints import Prints


class MaxStateTracker:
    """Tracks and reports maximal state information for frontier analysis."""

    def __init__(self, state_manager: StateManager, vc_manager: VectorClockManager,
                 processes_map: Dict[str, Process], num_processes: int):
        """Initialize max state tracker.

        Args:
            state_manager: State manager instance
            vc_manager: Vector clock manager instance
            processes_map: Map of process IDs to Process objects
            num_processes: Number of processes in the system
        """
        self.state_manager = state_manager
        self.vc_manager = vc_manager
        self.processes_map = processes_map
        self.num_processes = num_processes
        self.history: List[str] = []

        # Process aliases for display (customize as needed)
        self.proc_aliases = self._initialize_process_aliases()

    def _initialize_process_aliases(self) -> List[str]:
        """Initialize process aliases for display.

        Returns:
            List of process aliases
        """
        # Default mapping for common cases
        alias_map = {0: "M", 1: "S", 2: "A"}
        return [alias_map.get(i, f"P{i + 1}") for i in range(self.num_processes)]

    def track_frontier_state(self, triggering_event_name: str,
                             event_obj: Event = None) -> None:
        """Track and report the current frontier state.

        Args:
            triggering_event_name: Name of the event that triggered this tracking
            event_obj: Event object for process alias determination
        """
        # Build header string
        header_str = self._build_header_string(triggering_event_name, event_obj)

        # Find target frontier components
        target_frontier = self._build_target_frontier()

        # Find matching state
        target_state = self.state_manager.find_state_by_frontier(target_frontier)

        # Generate summary
        if target_state:
            summary = self._generate_state_summary(header_str, target_state)
        else:
            summary = f"{header_str} → frontiers=['<state_not_found_for_vc>'], verdict=NOT_FOUND"

        # Print the summary immediately and flush to ensure it appears
        print(summary)
        import sys
        sys.stdout.flush()  # Ensure output is immediately visible

        # Still add to history for potential future use
        self.history.append(summary)

    def _build_header_string(self, triggering_event_name: str, event_obj: Event = None) -> str:
        """Build header string for the frontier state report.

        Args:
            triggering_event_name: Name of triggering event
            event_obj: Event object for alias determination

        Returns:
            Formatted header string
        """
        # Build current vector clock string
        vc_parts = [f"{self.proc_aliases[i]}:{self.vc_manager.expected_vc[i]}"
                    for i in range(self.num_processes)]
        current_vc_str = f"[{', '.join(vc_parts)}]"

        # Add process alias if event provided
        trigger_alias_part = ""
        if event_obj:
            involved_indices = self.vc_manager.get_involved_indices(event_obj)
            if involved_indices and involved_indices[0] < len(self.proc_aliases):
                trigger_alias_part = f"@{self.proc_aliases[involved_indices[0]]}"

        return f"{triggering_event_name}{trigger_alias_part}:{current_vc_str}"

    def _build_target_frontier(self) -> List[Any]:
        """Build target frontier components based on current vector clock.

        Returns:
            List of frontier components (Events or ProcessModes)
        """
        target_frontier = []

        for i in range(self.num_processes):
            proc_id = f"P{i + 1}"
            count = self.vc_manager.expected_vc[i]

            if count > 0:
                process_obj = self.processes_map.get(proc_id)
                if process_obj and count <= len(process_obj.events):
                    # Get the event at this count (1-based to 0-based conversion)
                    event = process_obj.events[count - 1]
                    target_frontier.append(event)
                else:
                    # Fallback if event not found
                    target_frontier.append(ProcessModes.IOTA)
            else:
                # No events from this process yet
                target_frontier.append(ProcessModes.IOTA)

        return target_frontier

    def _generate_state_summary(self, header_str: str, state: State) -> str:
        """Generate summary string for a state.

        Args:
            header_str: Header string
            state: State object

        Returns:
            Formatted summary string
        """
        frontier_parts = []
        for i, item in enumerate(state.processes):
            proc_alias = self.proc_aliases[i]
            item_desc = item.name if isinstance(item, Event) else 'iota'
            frontier_parts.append(f"{proc_alias}:{item_desc}")

        frontier_str = f"⟨{', '.join(frontier_parts)}⟩"
        verdict = str(state.value).upper()

        return f"{header_str} → frontiers=['{frontier_str}'], verdict={verdict}"

    def _print_state_info(self, triggering_event_name: str, header_str: str,
                          state: State) -> None:
        """Print detailed state information.

        Args:
            triggering_event_name: Name of triggering event
            header_str: Header string
            state: State object
        """
        print(f"\n--- Max State Info (Trigger: {triggering_event_name}) ---")

        frontier_parts = [f"{self.proc_aliases[i]}:{item.name if isinstance(item, Event) else 'iota'}"
                          for i, item in enumerate(state.processes)]
        frontier_str = f"⟨{', '.join(frontier_parts)}⟩"
        verdict = str(state.value).upper()

        print(f"  {header_str} → frontiers=['{frontier_str}'], verdict={verdict}")

        # Additional debug info
        if hasattr(Prints, 'CURRENT_OUTPUT_LEVEL') and Prints.CURRENT_OUTPUT_LEVEL == "debug":
            print(f"    State Object: {state.name}, Propositions: {sorted(list(state.propositions))}")
            print(f"    Is Graph Maximal (no successors)?: {not bool(state.successors)}")

        print("------------------------------------")

    def _print_not_found_info(self, triggering_event_name: str, header_str: str) -> None:
        """Print information when target state is not found.

        Args:
            triggering_event_name: Name of triggering event
            header_str: Header string
        """
        print(f"\n--- Max State Info (Trigger: {triggering_event_name}) ---")
        print(f"  Monitor Expected VC: {self.vc_manager.expected_vc}")
        print(f"  Target Frontier State matching Expected VC was not found or not enabled.")
        print("------------------------------------")

    def print_history_summary(self) -> None:
        """Print summary of all tracked states."""
        if not self.history:
            return

        Prints.seperator("MAXIMAL STATES HISTORY (Monitor's VC Cut @ Trigger)")
        for summary_line in self.history:
            print(summary_line)
        Prints.seperator("END MAXIMAL STATES HISTORY")

    def clear_history(self) -> None:
        """Clear the tracking history."""
        self.history.clear()