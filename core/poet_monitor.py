# core/poet_monitor.py
"""Main PoET monitor class that orchestrates the entire monitoring process."""

import time
from typing import List, Optional
from utils.config import Config
from utils.generic_utils import GenericUtils
from parser.parser import parse
from parser.ast import Formula
from graphics.prints import Prints
from graphics.automaton import Automaton
from core.state_manager import StateManager
from core.vector_clock_manager import VectorClockManager
from core.event_processor import EventProcessor
from core.max_state_tracker import MaxStateTracker


class PoETMonitor:
    """Main monitor class that coordinates all components."""

    def __init__(self, config: Config):
        """Initialize the PoET monitor.

        Args:
            config: Configuration object
        """
        self.config = config
        self.performance_metrics = PerformanceMetrics()

        # Set global output level for Prints class
        Prints.CURRENT_OUTPUT_LEVEL = config.output_level

        # Components (initialized during run)
        self.state_manager: Optional[StateManager] = None
        self.vc_manager: Optional[VectorClockManager] = None
        self.event_processor: Optional[EventProcessor] = None
        self.max_state_tracker: Optional[MaxStateTracker] = None

        # Data
        self.property_formula: Optional[Formula] = None
        self.trace_events: List = []
        self.num_processes: int = 0

    def run(self) -> None:
        """Run the complete monitoring process."""
        try:
            # Setup phase
            self._setup()

            # Processing phase
            self._process_trace()

            # Results phase
            self._report_results()

        except Exception as e:
            Prints.process_error(f"Monitor execution failed: {e}")
            raise

    def _setup(self) -> None:
        """Setup phase: load files, parse property, initialize components."""
        if self.config.show_banner:
            Prints.banner()

        if self.config.is_debug:
            print(f"DEBUG: Output Level: {self.config.output_level}")
            print("DEBUG: Using PoET's standard vector clock deliverability rule.")
        elif not self.config.is_quiet:
            print(f"Output Level: {self.config.output_level}. Using PoET's standard VC rule.")

        # Load and parse property
        self._load_property()

        # Load trace
        self._load_trace()

        # Initialize components
        self._initialize_components()

        if self.config.output_level == "experiment":
            Prints.total_events(len(self.trace_events))

    def _load_property(self) -> None:
        """Load and parse the property file."""
        try:
            raw_prop = GenericUtils.read_property(self.config.property_file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Property file not found: {self.config.property_file}")

        self.property_formula = parse(raw_prop)
        if not self.property_formula:
            raise ValueError(f"Failed to parse property: {''.join(raw_prop).strip()}")

        if not self.config.is_quiet:
            Prints.raw_property(''.join(raw_prop))
            Prints.compiled_property(self.property_formula)

    def _load_trace(self) -> None:
        """Load the trace file."""
        try:
            trace_data = GenericUtils.read_json(self.config.trace_file)
            self.trace_events = trace_data['events']
            self.num_processes = trace_data['processes']
        except FileNotFoundError:
            raise FileNotFoundError(f"Trace file not found: {self.config.trace_file}")
        except KeyError as e:
            raise ValueError(f"Invalid trace file format, missing key: {e}")

    def _initialize_components(self) -> None:
        """Initialize all monitoring components."""
        # Core components
        self.state_manager = StateManager(
            self.config, self.num_processes, self.property_formula
        )
        self.vc_manager = VectorClockManager(self.num_processes)
        self.event_processor = EventProcessor(self.config, self.num_processes)

        # Max state tracker (only if needed)
        if self.config.is_max_state:
            self.max_state_tracker = MaxStateTracker(
                self.state_manager,
                self.vc_manager,
                self.state_manager.processes_map,
                self.num_processes
            )

    def _process_trace(self) -> None:
        """Process all events in the trace."""
        # Track initial state if max_state mode
        if self.max_state_tracker:
            self.max_state_tracker.track_frontier_state("Initial_S0")

        # Process each event
        for event_idx, event_data in enumerate(self.trace_events):
            start_time = time.time() if self.config.output_level == "experiment" else None

            try:
                event = self.event_processor.initialize_event(event_data)
            except (ValueError, SystemExit) as e:
                Prints.process_error(f"Could not initialize event {event_idx}: {e}")
                continue

            self._process_single_event(event)

            if start_time is not None:
                duration = time.time() - start_time
                self.performance_metrics.add_event_time(duration)

        # Final queue flush
        self._flush_holding_queue("End_Of_Trace")

        # Track final state
        if self.max_state_tracker:
            self.max_state_tracker.track_frontier_state("End_Of_Trace")

    def _process_single_event(self, event) -> None:
        """Process a single event through the monitoring pipeline."""
        if self.config.is_debug:
            Prints.event(event, i_debug=True)
            print(f"DEBUG: Handling event {event.name}. Current Expected VC: {self.vc_manager.expected_vc}")
        elif not self.config.is_quiet:
            print(f"\nProcessing Event: {event.name} (VC: {event.vector_clock})")

        # Check if event can be processed immediately
        if self.vc_manager.is_event_in_order(event):
            if self.config.is_debug:
                print(f"DEBUG: Event {event.name} is IN ORDER.")

            # Process event
            self.state_manager.process_event(event)
            self.vc_manager.update_expected_vc(event)

            # Flush any queued events that are now ready
            self._flush_holding_queue(f"{event.name}")

            # Track state if in max_state mode
            if self.max_state_tracker:
                self.max_state_tracker.track_frontier_state(event.name, event)
        else:
            if self.config.is_debug:
                print(f"DEBUG: Event {event.name} is OUT OF ORDER. Adding to holding queue.")

            self.vc_manager.add_to_holding_queue(event)

    def _flush_holding_queue(self, context: str = "") -> None:
        """Flush events from holding queue that are now ready."""
        if self.config.is_debug and context:
            print(f"DEBUG: Flushing queue after {context}")
            import sys
            sys.stdout.flush()

        iterations = 0
        max_iterations = 1000  # Prevent infinite loops

        while iterations < max_iterations:
            ready_events = self.vc_manager.get_ready_events_from_queue()
            if not ready_events:
                if self.config.is_debug:
                    print(f"DEBUG: Queue flush complete after {iterations} iterations")
                    sys.stdout.flush()
                break

            for event in ready_events:
                if self.config.is_debug:
                    print(f"DEBUG: Flushing {event.name} (VC: {event.vector_clock}) from queue.")
                    sys.stdout.flush()

                self.state_manager.process_event(event)
                self.vc_manager.update_expected_vc(event)

                if self.config.is_debug:
                    print(f"DEBUG: After flushing {event.name}, new expected_vc: {self.vc_manager.expected_vc}")
                    sys.stdout.flush()

                # Track state for flushed events
                if self.max_state_tracker:
                    self.max_state_tracker.track_frontier_state(f"{event.name} (from queue)", event)

            iterations += 1

        if iterations >= max_iterations:
            print(f"WARNING: Queue flush stopped after {max_iterations} iterations to prevent infinite loop")
            import sys
            sys.stdout.flush()

    def _report_results(self) -> None:
        """Report final results and statistics."""
        print("DEBUG: Starting _report_results")
        import sys
        sys.stdout.flush()

        # Max state history summary
        if self.max_state_tracker:
            print("DEBUG: Printing max state history")
            sys.stdout.flush()
            self.max_state_tracker.print_history_summary()

        # Display final states
        if not self.config.is_quiet:
            print("DEBUG: Displaying final states")
            sys.stdout.flush()
            Prints.display_states(
                self.state_manager.states,
                i_title="ALL FINAL STATES",
                i_debug=self.config.is_debug
            )

        # Performance metrics for experiment mode
        if self.config.output_level == "experiment":
            print("DEBUG: Reporting performance metrics")
            sys.stdout.flush()
            self._report_performance_metrics()

        # Final verdict
        if self.config.output_level != "nothing":
            print("DEBUG: Getting final verdict")
            sys.stdout.flush()
            final_verdict = self.state_manager.get_final_verdict()
            print(f"[FINAL VERDICT]: {final_verdict}")
            sys.stdout.flush()

        # Visual output
        if self.config.visual_enabled:
            print("DEBUG: Generating visual output")
            sys.stdout.flush()
            self._generate_visual_output()

        # Warning for pending events
        if self.vc_manager.has_pending_events() and not self.config.is_quiet:
            pending_names = self.vc_manager.get_pending_event_names()
            print(f"WARNING: Program ended with events still in holding queue: {pending_names}")
            sys.stdout.flush()

        print("DEBUG: _report_results completed")
        sys.stdout.flush()

    def _report_performance_metrics(self) -> None:
        """Report performance metrics for experiment mode."""
        Prints.total_states(len(self.state_manager.states))

        if self.performance_metrics.has_data():
            max_time, max_idx = self.performance_metrics.get_max_time()
            min_time, min_idx = self.performance_metrics.get_min_time()
            avg_time = self.performance_metrics.get_average_time()

            # Get event names for max/min indices
            max_event = self.trace_events[max_idx][0] if max_idx < len(self.trace_events) else "N/A"
            min_event = self.trace_events[min_idx][0] if min_idx < len(self.trace_events) else "N/A"

            Prints.events_time((max_time, max_event), (min_time, min_event), avg_time)

    def _generate_visual_output(self) -> None:
        """Generate visual output (automaton graphs)."""
        states_for_visualization = (
            self.state_manager.get_enabled_states()
            if self.config.reduce_enabled
            else self.state_manager.states
        )

        if states_for_visualization:
            self._create_automaton(states_for_visualization)

            if self.config.is_debug:
                Automaton.make_gif('output')

    def _create_automaton(self, states: List) -> None:
        """Create automaton visualization from states."""
        if not states:
            if not self.config.is_quiet:
                print("VISUAL_WARN: No states to create automaton for visualization.")
            return

        state_names, transitions = set(), []
        for state in states:
            state_names.add(state.name)
            for pred_name, (event, _) in state.successors.items():
                event_name = getattr(event, 'name', 'ERROR_NO_EVENT_NAME')
                transitions.append((pred_name, state.name, event_name))

        Automaton.create_automaton(states, transitions)


class PerformanceMetrics:
    """Helper class to track performance metrics."""

    def __init__(self):
        """Initialize performance metrics."""
        self.event_times: List[float] = []

    def add_event_time(self, duration: float) -> None:
        """Add event processing time."""
        self.event_times.append(duration)

    def has_data(self) -> bool:
        """Check if we have performance data."""
        return len(self.event_times) > 0

    def get_max_time(self) -> tuple:
        """Get maximum processing time and its index."""
        if not self.event_times:
            return 0.0, 0
        max_time = max(self.event_times)
        max_idx = self.event_times.index(max_time)
        return max_time, max_idx

    def get_min_time(self) -> tuple:
        """Get minimum processing time and its index."""
        if not self.event_times:
            return 0.0, 0
        min_time = min(self.event_times)
        min_idx = self.event_times.index(min_time)
        return min_time, min_idx

    def get_average_time(self) -> float:
        """Get average processing time."""
        if not self.event_times:
            return 0.0
        return sum(self.event_times) / len(self.event_times)