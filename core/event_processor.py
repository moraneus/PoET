# core/event_processor.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Event initialization and processing from raw trace data, including validation
# of input structure, process distribution, propositions, and vector clocks.

from typing import List, Any

from model.event import Event
from model.process import Process
from utils.config import Config
from utils.logger import get_logger, LogCategory


class EventProcessor:
    """Handles event initialization and processing logic."""

    def __init__(self, config: Config, num_processes: int):
        self.config = config
        self.num_processes = num_processes
        self.logger = get_logger()
        Event._Event__TIMELINE = 0

    def initialize_event(self, event_data: List[Any]) -> Event:
        """Initialize an Event object from raw trace data."""
        self._validate_basic_structure(event_data)

        event_name = str(event_data[0])
        self.logger.trace(f"Initializing event: '{event_name}'", LogCategory.EVENT)

        # Special handling for INIT event
        if event_name == "INIT":
            return self._create_init_event(event_data)

        if not self.validate_event_data_format(event_data):
            raise ValueError(
                f"Event data validation failed for '{event_name}'. Data: {event_data}"
            )

        event_processes_dist = self._process_event_processes(event_data[1], event_name)
        propositions = event_data[2]
        vector_clock = self._process_vector_clock(event_data, event_name)

        event = Event(
            i_name=event_name,
            i_processes=event_processes_dist,
            i_propositions=propositions,
            vector_clock=vector_clock,
        )

        self._log_event_creation(event)

        if self.config.is_debug:
            self._debug_event_validation(event)

        return event

    def _create_init_event(self, event_data: List[Any]) -> Event:
        """Create the special INIT event that belongs to all processes with zero vector clock."""
        event_name = "INIT"

        # INIT event format: ["INIT", ["P1", "P2", ...], propositions, [0, 0, ...]]
        # The process list should contain all process names
        if len(event_data) >= 2 and isinstance(event_data[1], list):
            # Use provided process list for INIT
            event_processes_dist = self._process_event_processes(
                event_data[1], event_name
            )
        else:
            # If not provided, INIT belongs to all processes
            event_processes_dist = [f"P{i+1}" for i in range(self.num_processes)]

        # Get propositions if provided
        propositions = (
            event_data[2]
            if len(event_data) > 2 and isinstance(event_data[2], list)
            else []
        )

        # INIT always has zero vector clock for all processes
        vector_clock = [0] * self.num_processes

        # Log the INIT event creation
        self.logger.info(
            f"Creating INIT event with {self.num_processes} processes and zero vector clock",
            LogCategory.EVENT,
            processes=event_processes_dist,
            vector_clock=vector_clock,
        )

        event = Event(
            i_name=event_name,
            i_processes=event_processes_dist,
            i_propositions=propositions,
            vector_clock=vector_clock,
        )

        self._log_event_creation(event)

        if self.config.is_debug:
            self._debug_event_validation(event)
            print(
                f"DEBUG: INIT event created with VC: {vector_clock} for all {self.num_processes} processes"
            )

        return event

    def _validate_basic_structure(self, event_data: List[Any]) -> None:
        """Validate basic event data structure."""
        if not isinstance(event_data, list) or len(event_data) < 3:
            error_msg = f"Invalid event data structure (must be a list with at least 3 elements): {event_data}"
            self.logger.error(error_msg, LogCategory.EVENT)
            raise ValueError(error_msg)

        event_name = str(event_data[0])
        if not event_name:
            error_msg = f"Event name cannot be empty. Event data: {event_data}"
            self.logger.error(error_msg, LogCategory.EVENT)
            raise ValueError(error_msg)

    def _process_event_processes(
        self, raw_process_list: List[Any], event_name: str
    ) -> List[Any]:
        """Process and validate event processes."""
        try:
            event_processes_dist = Process.distribute_processes(
                raw_process_list, self.num_processes
            )
            self.logger.trace(
                f"Event '{event_name}' process distribution: {raw_process_list} -> {event_processes_dist}",
                LogCategory.EVENT,
            )
            return event_processes_dist
        except (ValueError, IndexError) as e:
            error_msg = f"Invalid process specification for event '{event_name}': {raw_process_list}. Error: {e}"
            self.logger.error(error_msg, LogCategory.EVENT)
            raise ValueError(error_msg) from e

    def _process_vector_clock(
        self, event_data: List[Any], event_name: str
    ) -> List[int]:
        """Process and validate the vector clock from event data."""
        raw_vc = self._extract_raw_vector_clock(event_data, event_name)
        return self._adjust_vector_clock_length(raw_vc, event_name)

    def _extract_raw_vector_clock(
        self, event_data: List[Any], event_name: str
    ) -> List[int]:
        """Extract raw vector clock from event data."""
        if len(event_data) > 3 and event_data[3] is not None:
            raw_vc = event_data[3]
            if not isinstance(raw_vc, list) or not all(
                isinstance(x, int) for x in raw_vc
            ):
                self.logger.warn(
                    f"Event '{event_name}': Invalid vector clock format {raw_vc}. Using default.",
                    LogCategory.VECTOR_CLOCK,
                    event_name=event_name,
                    provided_vc=raw_vc,
                )
                return [0] * self.num_processes
            return raw_vc
        else:
            default_vc = [0] * self.num_processes
            self.logger.trace(
                f"Event '{event_name}': No VC provided, using default {default_vc}.",
                LogCategory.VECTOR_CLOCK,
            )
            return default_vc

    def _adjust_vector_clock_length(
        self, raw_vc: List[int], event_name: str
    ) -> List[int]:
        """Adjust vector clock length to match number of processes."""
        if len(raw_vc) != self.num_processes:
            self.logger.warn(
                f"Event '{event_name}' has VC length {len(raw_vc)}, "
                f"system has {self.num_processes} processes. Adjusting VC.",
                LogCategory.VECTOR_CLOCK,
                event_name=event_name,
                raw_vc_length=len(raw_vc),
                expected_length=self.num_processes,
                raw_vc_value=raw_vc,
            )
            if self.config.is_debug:
                print(
                    f"VC_WARNING: Event '{event_name}' has VC length {len(raw_vc)}, "
                    f"system has {self.num_processes} processes. Adjusting VC."
                )

            final_vc = (list(raw_vc) + [0] * self.num_processes)[: self.num_processes]
            self.logger.debug(
                f"Event '{event_name}': Adjusted VC from {raw_vc} to {final_vc}.",
                LogCategory.VECTOR_CLOCK,
            )
            return final_vc

        return list(raw_vc)

    def validate_event_data_format(self, event_data: List[Any]) -> bool:
        """Validate the basic structure and types of raw event data elements."""
        return (
            self._validate_process_specification(event_data)
            and self._validate_propositions(event_data)
            and self._validate_vector_clock_format(event_data)
        )

    def _validate_process_specification(self, event_data: List[Any]) -> bool:
        """Validate process specification format."""
        if not isinstance(event_data[1], list):
            self.logger.warn(
                f"Process specification for event '{event_data[0]}' must be a list, "
                f"got {type(event_data[1]).__name__}.",
                LogCategory.EVENT,
                event_name=str(event_data[0]),
                process_spec_type=type(event_data[1]).__name__,
            )
            return False
        return True

    def _validate_propositions(self, event_data: List[Any]) -> bool:
        """Validate propositions format."""
        if not isinstance(event_data[2], list):
            self.logger.warn(
                f"Propositions for event '{event_data[0]}' must be a list, "
                f"got {type(event_data[2]).__name__}.",
                LogCategory.EVENT,
                event_name=str(event_data[0]),
                propositions_type=type(event_data[2]).__name__,
            )
            return False

        if not all(isinstance(p, str) for p in event_data[2]):
            invalid_prop_types = [
                type(p).__name__ for p in event_data[2] if not isinstance(p, str)
            ]
            self.logger.warn(
                f"All propositions for event '{event_data[0]}' must be strings. Found: {invalid_prop_types}.",
                LogCategory.EVENT,
                event_name=str(event_data[0]),
                propositions_value=event_data[2],
            )
            return False
        return True

    def _validate_vector_clock_format(self, event_data: List[Any]) -> bool:
        """Validate vector clock format if present."""
        if len(event_data) > 3 and event_data[3] is not None:
            vc = event_data[3]
            if not isinstance(vc, list) or not all(isinstance(x, int) for x in vc):
                self.logger.warn(
                    f"Vector clock for event '{event_data[0]}' must be a list of integers if provided. "
                    f"Got type {type(vc).__name__} or non-int elements.",
                    LogCategory.EVENT,
                    event_name=str(event_data[0]),
                    vc_value=vc,
                )
                return False
        return True

    def _log_event_creation(self, event: Event) -> None:
        """Log event creation details."""
        self.logger.event(
            event_name=event.name,
            vector_clock=event.vector_clock,
            propositions=event.propositions,
            processes=[p for p in event.processes if isinstance(p, str)],
            timeline=event.time,
        )

    def _debug_event_validation(self, event: Event) -> None:
        """Detailed validation of the created Event object for debug mode."""
        self.logger.debug(
            f"Detailed Event Object Validation for '{event.name}':", LogCategory.EVENT
        )

        self._debug_validate_propositions(event)
        self._debug_validate_vector_clock(event)
        self._debug_validate_processes(event)

        print(f"DEBUG: Initialized event '{event.name}' with VC: {event.vector_clock}")

    def _debug_validate_propositions(self, event: Event) -> None:
        """Debug validation for event propositions."""
        if not hasattr(event, "propositions") or event.propositions is None:
            self.logger.warn(
                f"Event '{event.name}' propositions attribute missing or None.",
                LogCategory.EVENT,
            )
        elif not isinstance(event.propositions, list) or not all(
            isinstance(p, str) for p in event.propositions
        ):
            self.logger.warn(
                f"Event '{event.name}' propositions are not a list of strings: "
                f"{event.propositions} (type: {type(event.propositions)})",
                LogCategory.EVENT,
            )
        else:
            self.logger.debug(
                f"Event '{event.name}' propositions: {event.propositions}",
                LogCategory.EVENT,
            )

    def _debug_validate_vector_clock(self, event: Event) -> None:
        """Debug validation for event vector clock."""
        if not hasattr(event, "vector_clock") or event.vector_clock is None:
            self.logger.warn(
                f"Event '{event.name}' vector_clock attribute missing or None.",
                LogCategory.EVENT,
            )
        elif not isinstance(event.vector_clock, list) or not all(
            isinstance(vc_val, int) for vc_val in event.vector_clock
        ):
            self.logger.warn(
                f"Event '{event.name}' vector_clock is not a list of integers: "
                f"{event.vector_clock} (type: {type(event.vector_clock)})",
                LogCategory.EVENT,
            )
        elif len(event.vector_clock) != self.num_processes:
            self.logger.warn(
                f"Event '{event.name}' vector_clock length {len(event.vector_clock)} "
                f"does not match system num_processes {self.num_processes}.",
                LogCategory.EVENT,
            )
        else:
            self.logger.debug(
                f"Event '{event.name}' vector_clock: {event.vector_clock} (length: {len(event.vector_clock)})",
                LogCategory.EVENT,
            )

    def _debug_validate_processes(self, event: Event) -> None:
        """Debug validation for event processes."""
        if not hasattr(event, "processes") or event.processes is None:
            self.logger.warn(
                f"Event '{event.name}' processes attribute missing or None.",
                LogCategory.EVENT,
            )
        elif not isinstance(event.processes, list):
            self.logger.warn(
                f"Event '{event.name}' processes attribute is not a list: {type(event.processes)}.",
                LogCategory.EVENT,
            )
        else:
            active_procs = [p for p in event.processes if isinstance(p, str)]
            self.logger.debug(
                f"Event '{event.name}' object's active processes: {active_procs}",
                LogCategory.EVENT,
            )

    def get_processing_stats(self) -> dict:
        """Returns statistics related to event processing."""
        return {
            "events_initialized_from_trace": self.logger.get_counter(
                "events_initialized_from_trace"
            ),
            "event_initialization_errors": self.logger.get_counter(
                "event_initialization_errors"
            ),
            "vector_clock_adjustments": self.logger.get_counter(
                "vector_clock_adjustments"
            ),
        }

    def increment_stat(self, stat_name: str, amount: int = 1) -> None:
        """Increments a named statistic counter."""
        self.logger.increment_counter(stat_name, amount=amount)
