# core/poet_monitor.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Main monitor class orchestrating the complete runtime verification process,
# coordinating event loading, processing, state management, PCTL evaluation,
# and output generation.

import time
import sys
from typing import List, Optional, Dict, Any

from utils.config import Config
from utils.generic_utils import GenericUtils
from utils.logger import init_logger, get_logger, LogCategory, LogLevel
from parser.parser import parse
from parser.ast import Formula
from graphics.prints import Prints
from graphics.automaton import Automaton
from core.state_manager import StateManager
from core.vector_clock_manager import VectorClockManager
from core.event_processor import EventProcessor
from core.max_state_tracker import MaxStateTracker
from model.event import Event


class PerformanceMetrics:
    """Tracks event processing time metrics."""

    def __init__(self):
        self.event_times: List[float] = []

    def add_event_time(self, duration: float) -> None:
        self.event_times.append(duration)

    def has_data(self) -> bool:
        return bool(self.event_times)

    def get_max_time(self) -> tuple[float, int]:
        if not self.event_times:
            return 0.0, -1
        max_val = max(self.event_times)
        return max_val, self.event_times.index(max_val)

    def get_min_time(self) -> tuple[float, int]:
        if not self.event_times:
            return 0.0, -1
        min_val = min(self.event_times)
        return min_val, self.event_times.index(min_val)

    def get_average_time(self) -> float:
        if not self.event_times:
            return 0.0
        return sum(self.event_times) / len(self.event_times)


class PoETMonitor:
    """Main monitor class coordinating runtime verification of PCTL properties against event traces."""

    def __init__(self, config: Config):
        self.config = config
        self.performance_metrics = PerformanceMetrics()

        self.logger = init_logger(
            level=config.log_level,
            output_file=config.log_file,
            allowed_categories=config.log_categories,
        )
        Prints.CURRENT_OUTPUT_LEVEL = config.output_level

        self.logger.info(
            "PoET Monitor core initialized.",
            LogCategory.GENERAL,
            initial_config_output_level=config.output_level,
            initial_config_log_level=config.log_level,
        )

        # Component placeholders
        self.state_manager: Optional[StateManager] = None
        self.vc_manager: Optional[VectorClockManager] = None
        self.event_processor: Optional[EventProcessor] = None
        self.max_state_tracker: Optional[MaxStateTracker] = None

        # Data placeholders
        self.property_formula: Optional[Formula] = None
        self.trace_events: List[Any] = []
        self.num_processes: int = 0
        self.process_names_aliases: List[str] = []

    def run(self) -> None:
        """Execute complete monitoring process: setup, trace processing, and results reporting."""
        try:
            self.logger.start_timer("total_execution_time")
            self.logger.section("POET MONITORING PROCESS STARTED")

            self._setup()
            self._process_trace()
            self._report_results()

            total_time = self.logger.end_timer("total_execution_time")
            self.logger.performance("Total PoET execution time", total_time, "s")

        except Exception as e:
            self.logger.error(
                f"PoET monitor execution failed critically: {e}",
                LogCategory.ERROR,
                exc_info=True,
            )
            Prints.process_error(f"A critical error occurred in the PoET monitor: {e}")
            raise
        finally:
            if not self._is_max_state_with_filtered_categories():
                self.logger.print_summary()

    def _is_max_state_with_filtered_categories(self) -> bool:
        """Check if in max_state mode with category filtering."""
        return (
            self.config.is_max_state
            and self.config.log_categories is not None
            and not self.config.log_categories
        )

    def _setup(self) -> None:
        """Handle setup phase: banner display, configuration logging, property/trace loading, component initialization."""
        self.logger.start_timer("setup_phase_time")

        if (
            self.config.show_banner
            and not self._is_max_state_with_filtered_categories()
        ):
            Prints.banner()

        self._log_configuration()
        self._load_property()
        self._load_trace()
        self._initialize_components()

        if self.config.output_level == "experiment":
            Prints.total_events(len(self.trace_events))

        setup_time = self.logger.end_timer("setup_phase_time")
        self.logger.performance("Setup phase duration", setup_time, "s")

    def _log_configuration(self) -> None:
        """Log key configuration settings."""
        self.logger.info("PoET Runtime Verification Starting", LogCategory.GENERAL)
        self.logger.info(
            f"Property File: {self.config.property_file}", LogCategory.GENERAL
        )
        self.logger.info(f"Trace File: {self.config.trace_file}", LogCategory.GENERAL)
        self.logger.info(
            f"Output Level: {self.config.output_level}", LogCategory.GENERAL
        )
        self.logger.info(
            f"Reduce Mode: {self.config.reduce_enabled}", LogCategory.GENERAL
        )
        self.logger.info(
            f"Visual Output: {self.config.visual_enabled}", LogCategory.GENERAL
        )
        self.logger.info(
            f"Trace Validation: {getattr(self.config, 'validate_enabled', False)}",
            LogCategory.GENERAL,
        )

        self.logger.debug(
            f"Effective PoET monitor output level: {self.config.output_level}",
            LogCategory.GENERAL,
        )
        self.logger.debug(
            "Using PoET's standard vector clock deliverability rule for event processing.",
            LogCategory.VECTOR_CLOCK,
        )

        self._print_console_configuration()

    def _print_console_configuration(self) -> None:
        """Print configuration to console if appropriate."""
        if self._is_max_state_with_filtered_categories():
            return

        if self.config.is_debug:
            print(
                f"DEBUG_CONSOLE: PoET Output Level set to: {self.config.output_level}"
            )
            print(
                "DEBUG_CONSOLE: Using standard Fidge-Mattern based VC deliverability."
            )
        elif not self.config.is_quiet:
            print(
                f"Console Output Level: {self.config.output_level}. Using standard VC rules."
            )

    def _load_property(self) -> None:
        """Load PCTL property from file and parse it."""
        self.logger.debug(
            f"Loading PCTL property from file: {self.config.property_file}",
            LogCategory.PARSER,
        )

        raw_prop_content = self._read_property_file()
        self.property_formula = self._parse_property(raw_prop_content)

        self._log_parsed_property(raw_prop_content)

    def _read_property_file(self) -> str:
        """Read and validate property file."""
        try:
            raw_prop_content = GenericUtils.read_property(self.config.property_file)
            raw_display = (
                raw_prop_content
                if isinstance(raw_prop_content, str)
                else "".join(raw_prop_content)
            )
            self.logger.trace(
                f"Raw property content loaded: '{raw_display[:100].strip()}...'",
                LogCategory.PARSER,
            )
            return raw_display
        except FileNotFoundError:
            error_msg = f"Property file not found: {self.config.property_file}"
            self.logger.error(error_msg, LogCategory.ERROR)
            raise FileNotFoundError(error_msg)

    def _parse_property(self, raw_prop_content: str) -> Formula:
        """Parse property content into Formula object."""
        property_formula = parse(raw_prop_content)
        if not property_formula:
            error_msg = f"Failed to parse PCTL property from '{self.config.property_file}'. Content: '{raw_prop_content.strip()}'"
            self.logger.error(error_msg, LogCategory.PARSER)
            raise ValueError(error_msg)
        return property_formula

    def _log_parsed_property(self, raw_display: str) -> None:
        """Log parsed property information."""
        self.logger.info(
            f"Property (parsed): {str(self.property_formula)}", LogCategory.PARSER
        )
        self.logger.info(
            f"Internal AST representation: {repr(self.property_formula)}",
            LogCategory.PARSER,
        )

        # Always show property information regardless of output mode
        Prints.raw_property(raw_display.strip())
        Prints.compiled_property(self.property_formula)

    def _load_trace(self) -> None:
        """Load and validate event trace file in JSON format."""
        self.logger.debug(
            f"Loading event trace from file: {self.config.trace_file}",
            LogCategory.TRACE,
        )

        trace_data = self._read_trace_file()
        self._extract_trace_components(trace_data)
        self._setup_process_aliases(trace_data)
        self._log_trace_information()

    def _read_trace_file(self) -> Dict[str, Any]:
        """Read and validate trace file."""
        try:
            return GenericUtils.read_json(self.config.trace_file)
        except FileNotFoundError:
            error_msg = f"Trace file not found: {self.config.trace_file}"
            self.logger.error(error_msg, LogCategory.ERROR)
            raise FileNotFoundError(error_msg)
        except KeyError as e:
            error_msg = f"Invalid trace file format in '{self.config.trace_file}', missing essential key: {e}"
            self.logger.error(error_msg, LogCategory.TRACE)
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Unexpected error loading trace file '{self.config.trace_file}': {e}"
            )
            self.logger.error(error_msg, LogCategory.TRACE, exc_info=True)
            raise RuntimeError(error_msg) from e

    def _extract_trace_components(self, trace_data: Dict[str, Any]) -> None:
        """Extract events and process count from trace data."""
        try:
            self.trace_events = trace_data["events"]
            self.num_processes = trace_data["processes"]
        except KeyError as e:
            error_msg = f"Missing required key in trace file: {e}"
            self.logger.error(error_msg, LogCategory.TRACE)
            raise ValueError(error_msg) from e

    def _setup_process_aliases(self, trace_data: Dict[str, Any]) -> None:
        """Setup process name aliases from trace data or defaults."""
        if (
            "process_names" in trace_data
            and isinstance(trace_data["process_names"], list)
            and len(trace_data["process_names"]) == self.num_processes
        ):

            self.process_names_aliases = trace_data["process_names"]
            self.logger.info(
                f"Using process names from trace file: {self.process_names_aliases}",
                LogCategory.GENERAL,
            )
        else:
            self.process_names_aliases = [
                f"P{i + 1}" for i in range(self.num_processes)
            ]
            log_msg = f"Trace 'process_names' key not found or invalid. Defaulting to: {self.process_names_aliases}."

            if "process_names" in trace_data:
                self.logger.warn(log_msg, LogCategory.GENERAL)
            else:
                self.logger.info(log_msg, LogCategory.GENERAL)

    def _log_trace_information(self) -> None:
        """Log trace loading information."""
        self.logger.info(
            f"Loading trace from: {self.config.trace_file}", LogCategory.TRACE
        )
        self.logger.info(
            f"Loaded {len(self.trace_events)} events from trace.", LogCategory.TRACE
        )
        self.logger.info(
            f"System processes defined: {self.process_names_aliases}",
            LogCategory.GENERAL,
        )

    def _initialize_components(self) -> None:
        """Initialize all core monitoring components."""
        self.logger.info(
            "Initializing core monitoring components...", LogCategory.GENERAL
        )

        if self.property_formula is None:
            err_msg = "Cannot initialize components: PCTL property formula has not been loaded/parsed."
            self.logger.error(err_msg, LogCategory.GENERAL)
            raise RuntimeError(err_msg)

        self._create_core_components()
        self._create_max_state_tracker_if_needed()

        self.logger.info(
            "All monitoring components initialized successfully.", LogCategory.GENERAL
        )
        self.logger.info(
            f"Components initialized for processes: {self.process_names_aliases}",
            LogCategory.GENERAL,
        )

    def _create_core_components(self) -> None:
        """Create core components: StateManager, VectorClockManager, EventProcessor."""
        self.state_manager = StateManager(
            self.config, self.num_processes, self.property_formula
        )
        self.vc_manager = VectorClockManager(self.num_processes)
        self.event_processor = EventProcessor(self.config, self.num_processes)
        self.logger.debug(
            "StateManager, VectorClockManager, and EventProcessor initialized.",
            LogCategory.GENERAL,
        )

    def _create_max_state_tracker_if_needed(self) -> None:
        """Create MaxStateTracker if max_state output mode is active."""
        if self.config.output_level == "max_state":
            if not self.state_manager or not self.vc_manager:
                err_msg = "StateManager or VCManager not ready for MaxStateTracker initialization."
                self.logger.error(err_msg, LogCategory.STATE)
                raise RuntimeError(err_msg)

            self.max_state_tracker = MaxStateTracker(
                self.state_manager,
                self.vc_manager,
                self.state_manager.processes_map,
                self.num_processes,
                config=self.config,
                process_aliases_override=self.process_names_aliases,
            )
            self.logger.debug(
                "MaxStateTracker initialized for 'max_state' output mode.",
                LogCategory.STATE,
            )

    def _process_trace(self) -> None:
        """Process all trace events and handle max_state output."""
        self.logger.start_timer("trace_processing_time")
        self.logger.info(
            f"Starting processing of {len(self.trace_events)} events from trace.",
            LogCategory.TRACE,
        )

        self._output_initial_state_if_max_state()
        self._process_all_events()
        self._finalize_trace_processing()

        trace_processing_duration = self.logger.end_timer("trace_processing_time")
        self.logger.performance(
            "Total trace processing duration", trace_processing_duration, "s"
        )

    def _output_initial_state_if_max_state(self) -> None:
        """Output initial state for max_state mode."""
        if self.config.output_level == "max_state" and self.max_state_tracker:
            self.max_state_tracker.track_frontier_state(triggering_event_name="Initial")

    def _process_all_events(self) -> None:
        """Process each event in the trace."""
        for event_idx, event_data_item in enumerate(self.trace_events):
            self.logger.start_timer(f"event_processing_step_{event_idx}")

            current_event_obj = self._initialize_event_safely(
                event_data_item, event_idx
            )

            if current_event_obj:
                self._process_initialized_event(current_event_obj, event_idx)

                # Create graph after processing each event
                if self.config.visual_enabled:
                    self._create_iteration_graph(
                        f"After Event: {current_event_obj.name}"
                    )

            event_processing_duration = self.logger.end_timer(
                f"event_processing_step_{event_idx}"
            )
            if self.config.output_level == "experiment":
                self.performance_metrics.add_event_time(event_processing_duration)

    def _create_iteration_graph(self, context: str) -> None:
        """Create a graph for the current iteration state."""
        if not self.state_manager:
            self.logger.warn(
                "StateManager not available, cannot create iteration graph.",
                LogCategory.VISUAL,
            )
            return

        states_to_visualize = self._get_states_for_visualization()

        if states_to_visualize:
            self.logger.debug(
                f"Creating iteration graph for: {context}",
                LogCategory.VISUAL,
            )

            nodes_for_graph, edges_for_graph = self._prepare_visualization_data(
                states_to_visualize
            )

            try:
                # This will automatically increment the counter and create graph_N.svg
                Automaton.create_automaton(states_to_visualize, edges_for_graph)
                self.logger.debug(
                    f"Iteration graph created successfully for: {context}",
                    LogCategory.VISUAL,
                )
            except Exception as e:
                self.logger.error(
                    f"Error creating iteration graph for '{context}': {e}",
                    LogCategory.VISUAL,
                    exc_info=True,
                )
        else:
            self.logger.debug(
                f"No states available for iteration graph: {context}",
                LogCategory.VISUAL,
            )

    def _initialize_event_safely(
        self, event_data_item: Any, event_idx: int
    ) -> Optional[Event]:
        """Safely initialize event from raw data with error handling."""
        try:
            current_event_obj = self.event_processor.initialize_event(event_data_item)
            self.logger.increment_counter("events_initialized_from_trace_successfully")
            return current_event_obj
        except (ValueError, SystemExit) as e:
            self._handle_event_initialization_error(event_data_item, event_idx, e)
            return None

    def _handle_event_initialization_error(
        self, event_data_item: Any, event_idx: int, error: Exception
    ) -> None:
        """Handle event initialization errors."""
        error_msg = (
            f"Could not initialize event at index {event_idx} from data "
            f"{str(event_data_item)[:100]}... Error: {error}"
        )
        self.logger.error(
            error_msg,
            LogCategory.EVENT,
            event_index=event_idx,
            raw_event_data=str(event_data_item)[:200],
            exception_details=str(error),
            exc_info=False,
        )
        self.logger.increment_counter("event_initialization_errors")
        Prints.process_error(error_msg)

    def _process_initialized_event(
        self, current_event_obj: Event, event_idx: int
    ) -> None:
        """Process successfully initialized event."""
        self.logger.debug(
            f"PoETMonitor: Processing trace event '{current_event_obj.name}' (Index: {event_idx}).",
            LogCategory.EVENT,
        )

        self._process_single_event(current_event_obj)

        if self.config.output_level == "max_state" and self.max_state_tracker:
            self.max_state_tracker.track_frontier_state(
                triggering_event_name=current_event_obj.name,
                event_obj=current_event_obj,
            )

    def _finalize_trace_processing(self) -> None:
        """Finalize trace processing with queue flush and end state output."""
        self.logger.debug(
            "PoETMonitor: Performing final queue flush after processing all trace events.",
            LogCategory.VECTOR_CLOCK,
        )
        self._flush_holding_queue("EndOfTrace_FinalCleanupFlush")

        if self.config.output_level == "max_state" and self.max_state_tracker:
            self.max_state_tracker.track_frontier_state(
                triggering_event_name="End_Of_Trace"
            )

    def _process_single_event(self, event: Event) -> None:
        """Process single event: check order, process if ready or add to queue."""
        self.logger.debug(
            f"PoETMonitor: _process_single_event for '{event.name}'.",
            LogCategory.EVENT,
            event_vc=event.vector_clock,
            current_expected_system_vc=(
                self.vc_manager.expected_vc if self.vc_manager else "VCManager N/A"
            ),
        )

        if not self.vc_manager or not self.state_manager:
            self.logger.error(
                "VCManager or StateManager not properly initialized. Cannot proceed.",
                LogCategory.ERROR,
            )
            return

        is_in_order = self.vc_manager.is_event_in_order(event)
        self.logger.debug(
            f"Event '{event.name}' vector clock order check. EventVC: {event.vector_clock}, "
            f"ExpectedSystemVC: {self.vc_manager.expected_vc}, InOrder: {is_in_order}.",
            LogCategory.VECTOR_CLOCK,
        )

        if is_in_order:
            self._process_in_order_event(event)
        else:
            self._add_event_to_queue(event)

    def _process_in_order_event(self, event: Event) -> None:
        """Process event that arrived in order."""
        self.logger.debug(
            f"Event '{event.name}' is IN ORDER. Processing immediately.",
            LogCategory.VECTOR_CLOCK,
        )
        self.state_manager.process_event(event)
        self.vc_manager.update_expected_vc(event)
        self._flush_holding_queue(f"after_in_order_processing_of_{event.name}")
        self.logger.increment_counter("events_processed_directly_in_order")

    def _add_event_to_queue(self, event: Event) -> None:
        """Add out-of-order event to holding queue."""
        self.logger.debug(
            f"Event '{event.name}' is OUT OF ORDER. Current System ExpectedVC: {self.vc_manager.expected_vc}. "
            f"Adding to holding queue.",
            LogCategory.VECTOR_CLOCK,
        )
        self.vc_manager.add_to_holding_queue(event)
        self.logger.increment_counter("events_added_to_holding_queue")

    def _flush_holding_queue(self, context_info: str = "") -> None:
        """Process events from holding queue that are now deliverable."""
        if not self.vc_manager or not self.state_manager:
            self.logger.error(
                "VCManager or StateManager not properly initialized. Cannot proceed.",
                LogCategory.ERROR,
            )
            return

        if not self.vc_manager.has_pending_events():
            self.logger.trace(
                f"Holding queue is empty. No flush needed (context: '{context_info}').",
                LogCategory.VECTOR_CLOCK,
            )
            return

        self.logger.debug(
            f"PoETMonitor: Attempting to flush holding queue (context: '{context_info}').",
            LogCategory.VECTOR_CLOCK,
        )

        total_flushed = self._perform_queue_flush_iterations(context_info)

        if total_flushed > 0:
            self.logger.info(
                f"PoETMonitor: Flushed {total_flushed} events from holding queue "
                f"during this flush operation (context: '{context_info}').",
                LogCategory.VECTOR_CLOCK,
            )
            self.logger.increment_counter(
                "events_flushed_from_queue_cumulatively", total_flushed
            )

    def _perform_queue_flush_iterations(self, context_info: str) -> int:
        """Perform iterative queue flushing and return total events flushed."""
        iterations = 0
        max_iterations = 1000
        total_flushed = 0

        while iterations < max_iterations:
            ready_events = self.vc_manager.get_ready_events_from_queue()
            if not ready_events:
                self.logger.debug(
                    f"Queue flush for context '{context_info}' completed after {iterations} iterations. "
                    f"No more events currently ready from queue.",
                    LogCategory.VECTOR_CLOCK,
                )
                break

            self.logger.debug(
                f"Queue flush for context '{context_info}', pass {iterations + 1}: "
                f"Found {len(ready_events)} ready events: {[e.name for e in ready_events]}.",
                LogCategory.VECTOR_CLOCK,
            )

            total_flushed += self._process_ready_events(ready_events, context_info)
            iterations += 1

        if iterations >= max_iterations:
            self._log_max_iterations_warning(context_info, max_iterations)

        return total_flushed

    def _process_ready_events(
        self, ready_events: List[Event], context_info: str
    ) -> int:
        """Process list of ready events from queue."""
        processed_count = 0
        for event_from_queue in ready_events:
            self.logger.trace(
                f"PoETMonitor: Flushing '{event_from_queue.name}' from queue (context: '{context_info}').",
                LogCategory.VECTOR_CLOCK,
                event_vc=event_from_queue.vector_clock,
                expected_vc_at_flush_time=self.vc_manager.expected_vc,
            )
            self.state_manager.process_event(event_from_queue)
            self.vc_manager.update_expected_vc(event_from_queue)
            processed_count += 1
            self.logger.trace(
                f"PoETMonitor: Successfully flushed '{event_from_queue.name}'. "
                f"New system ExpectedVC: {self.vc_manager.expected_vc}.",
                LogCategory.VECTOR_CLOCK,
            )
        return processed_count

    def _log_max_iterations_warning(
        self, context_info: str, max_iterations: int
    ) -> None:
        """Log warning when max iterations reached in queue flush."""
        self.logger.warn(
            f"PoETMonitor: Queue flush operation stopped after {max_iterations} iterations "
            f"to prevent potential infinite loop (context: '{context_info}'). "
            f"Remaining in queue: {len(self.vc_manager.holding_queue) if self.vc_manager else 'N/A'}.",
            LogCategory.VECTOR_CLOCK,
        )

    def _report_results(self) -> None:
        """Handle final reporting: PCTL verdict, visual output, and summaries."""
        self.logger.start_timer("results_reporting_time")
        self.logger.debug("Starting results reporting phase.", LogCategory.GENERAL)

        self._display_final_states_if_needed()
        self._report_performance_if_experiment_mode()
        self._print_final_verdict_if_needed()
        self._generate_visual_output_if_enabled()
        self._warn_about_pending_events_if_needed()

        self.logger.end_timer("results_reporting_time")
        self.logger.debug("Results reporting phase completed.", LogCategory.GENERAL)

    def _display_final_states_if_needed(self) -> None:
        """Display all collected states for certain modes."""
        if not self.config.is_quiet and self.config.output_level != "max_state":
            self.logger.debug(
                "Displaying all final states (for non-max_state, non-quiet modes).",
                LogCategory.STATE,
            )
            if self.state_manager:
                Prints.display_states(
                    self.state_manager.states,
                    i_title="ALL FINAL STATES (Collected During Run)",
                    i_debug=self.config.is_debug,
                )

    def _report_performance_if_experiment_mode(self) -> None:
        """Report performance metrics for experiment mode."""
        if self.config.output_level == "experiment" and self.state_manager:
            self.logger.debug(
                "Reporting detailed performance metrics for 'experiment' mode.",
                LogCategory.PERFORMANCE,
            )
            self._report_performance_metrics()

    def _print_final_verdict_if_needed(self) -> None:
        """Print final PCTL verdict if not in nothing or max_state mode."""
        if (
            self.config.output_level != "nothing"
            and self.config.output_level != "max_state"
        ):
            if self.state_manager:
                final_verdict = self.state_manager.get_final_verdict()
                self.logger.info(
                    f"Final PCTL Verdict: {final_verdict}", LogCategory.PCTL
                )
                print(f"[FINAL VERDICT]: {final_verdict}")
                sys.stdout.flush()
            else:
                self.logger.warn(
                    "StateManager not available for determining final PCTL verdict.",
                    LogCategory.PCTL,
                )
                print(
                    "[FINAL VERDICT]: UNDETERMINED (StateManager not available or error occurred)"
                )

    def _generate_visual_output_if_enabled(self) -> None:
        """Generate visual output if enabled."""
        if self.config.visual_enabled:
            self.logger.info(
                "Generating visual output as configured...", LogCategory.VISUAL
            )
            self._generate_visual_output()

    def _warn_about_pending_events_if_needed(self) -> None:
        """Warn about events still pending in queue."""
        if (
            self.vc_manager
            and self.vc_manager.has_pending_events()
            and not self.config.is_quiet
        ):
            pending_event_names = self.vc_manager.get_pending_event_names()
            warning_msg = f"Execution finished with events still pending in the holding queue: {pending_event_names}"
            self.logger.warn(
                warning_msg,
                LogCategory.VECTOR_CLOCK,
                pending_events_list=pending_event_names,
            )
            print(f"WARNING: {warning_msg}")
            sys.stdout.flush()

    def _report_performance_metrics(self) -> None:
        """Log and print performance metrics for experiment mode."""
        if not self.state_manager:
            self.logger.warn(
                "Cannot report performance metrics: StateManager not available.",
                LogCategory.PERFORMANCE,
            )
            return

        self._report_state_metrics()
        self._report_timing_metrics()

    def _report_state_metrics(self) -> None:
        """Report state-related metrics."""
        total_states_created = len(self.state_manager.states)
        self.logger.performance(
            "Total states created during run", total_states_created, unit="states"
        )
        Prints.total_states(total_states_created)

    def _report_timing_metrics(self) -> None:
        """Report timing-related metrics."""
        if not self.performance_metrics.has_data():
            return

        max_time_val, max_idx_val = self.performance_metrics.get_max_time()
        min_time_val, min_idx_val = self.performance_metrics.get_min_time()
        avg_time_val = self.performance_metrics.get_average_time()

        max_event_name = self._get_event_name_for_index(max_idx_val)
        min_event_name = self._get_event_name_for_index(min_idx_val)

        # Remove the extra keyword arguments
        self.logger.performance("Maximum event processing time", max_time_val, "s")
        self.logger.performance("Minimum event processing time", min_time_val, "s")
        self.logger.performance("Average event processing time", avg_time_val, "s")

        # Log the event names separately if needed
        self.logger.info(f"Slowest event: {max_event_name}", LogCategory.PERFORMANCE)
        self.logger.info(f"Fastest event: {min_event_name}", LogCategory.PERFORMANCE)

        Prints.events_time(
            (max_time_val, max_event_name), (min_time_val, min_event_name), avg_time_val
        )

    def _get_event_name_for_index(self, event_idx: int) -> str:
        """Get event name for given index, with safety checks."""
        if (
            event_idx != -1
            and event_idx < len(self.trace_events)
            and isinstance(self.trace_events[event_idx], list)
            and self.trace_events[event_idx]
        ):
            return str(self.trace_events[event_idx][0])
        return "N/A"

    def _generate_visual_output(self) -> None:
        """Generate visual output (state automaton graphs) if states are available."""
        if not self.state_manager:
            self.logger.warn(
                "StateManager not available, cannot generate visual output.",
                LogCategory.VISUAL,
            )
            return

        states_to_visualize = self._get_states_for_visualization()

        if states_to_visualize:
            self._create_automaton_visualization(states_to_visualize)
        else:
            self._log_no_states_for_visualization()

    def _get_states_for_visualization(self) -> List[Any]:
        """Get states for visualization based on reduce mode setting."""
        return (
            self.state_manager.get_enabled_states()
            if self.config.reduce_enabled
            else self.state_manager.states
        )

    def _create_automaton_visualization(self, states_to_visualize: List[Any]) -> None:
        """Create automaton visualization from states."""
        self.logger.info(
            f"Preparing to visualize {len(states_to_visualize)} states. "
            f"(Reduce mode active: {self.config.reduce_enabled}).",
            LogCategory.VISUAL,
        )
        self.logger.info(
            "Generating visual output (image style with conditional blue)...",
            LogCategory.VISUAL,
        )

        nodes_for_graph, edges_for_graph = self._prepare_visualization_data(
            states_to_visualize
        )

        self.logger.debug(
            f"Creating automaton visualization with {len(nodes_for_graph)} nodes and {len(edges_for_graph)} transitions.",
            LogCategory.VISUAL,
        )

        try:
            Automaton.create_automaton(states_to_visualize, edges_for_graph)
            self.logger.info(
                "Automaton visualization SVG(s) created successfully in 'output' directory.",
                LogCategory.VISUAL,
            )

            if self.config.is_debug:
                self._create_animated_gif()
        except Exception as e:
            self.logger.error(
                f"Error during visual output generation: {e}",
                LogCategory.VISUAL,
                exc_info=True,
            )
            self.logger.info(
                "Automaton visualization may be incomplete or absent due to an error.",
                LogCategory.VISUAL,
            )

    def _prepare_visualization_data(
        self, states_to_visualize: List[Any]
    ) -> tuple[set, List[tuple]]:
        """Prepare nodes and edges data for visualization."""
        nodes_for_graph, edges_for_graph = set(), []

        for current_state_obj in states_to_visualize:
            nodes_for_graph.add(current_state_obj.name)
            for successor_name_str, (
                event_leading_to_successor,
                _,
            ) in current_state_obj.successors.items():
                event_name_label = getattr(
                    event_leading_to_successor, "name", "UNKNOWN_EVENT"
                )
                edges_for_graph.append(
                    (successor_name_str, current_state_obj.name, event_name_label)
                )

        return nodes_for_graph, edges_for_graph

    def _create_animated_gif(self) -> None:
        """Create animated GIF in debug mode."""
        self.logger.debug(
            "Attempting to create animated GIF from generated SVG files...",
            LogCategory.VISUAL,
        )
        Automaton.make_gif("output")
        self.logger.info(
            "Animated GIF (graph.gif) created in 'output' directory.",
            LogCategory.VISUAL,
        )

    def _log_no_states_for_visualization(self) -> None:
        """Log when no states are available for visualization."""
        self.logger.warn(
            "No states available for visualization (either no states generated or all pruned).",
            LogCategory.VISUAL,
        )
        self.logger.info(
            "Automaton visualization attempt complete (no states to draw).",
            LogCategory.VISUAL,
        )

    def get_execution_stats(self) -> Dict[str, Any]:
        """Return dictionary containing execution statistics and metrics."""
        stats_data: Dict[str, Any] = {
            "events_read_from_trace": self.logger.get_counter(
                "events_initialized_from_trace_successfully"
            ),
            "events_processed_immediately": self.logger.get_counter(
                "events_processed_directly_in_order"
            ),
            "events_added_to_holding_queue": self.logger.get_counter(
                "events_added_to_holding_queue"
            ),
            "events_flushed_from_queue_cumulatively": self.logger.get_counter(
                "events_flushed_from_queue_cumulatively"
            ),
            "queue_flush_operations_count": self.logger.get_counter(
                "queue_flush_operations"
            ),
            "event_initialization_errors": self.logger.get_counter(
                "event_initialization_errors"
            ),
            "total_states_created": (
                len(self.state_manager.states) if self.state_manager else 0
            ),
            "performance_metrics": None,
        }

        if self.performance_metrics.has_data():
            max_time_value, _ = self.performance_metrics.get_max_time()
            min_time_value, _ = self.performance_metrics.get_min_time()
            avg_time_value = self.performance_metrics.get_average_time()
            stats_data["performance_metrics"] = {
                "max_event_processing_time_seconds": max_time_value,
                "min_event_processing_time_seconds": min_time_value,
                "avg_event_processing_time_seconds": avg_time_value,
            }

        return stats_data
