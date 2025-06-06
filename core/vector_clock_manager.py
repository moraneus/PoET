# core/vector_clock_manager.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Vector clock management for event ordering in distributed systems using
# Fidge-Mattern algorithm to determine event deliverability and maintain
# proper causality ordering.

from typing import List, Dict, Any
from model.event import Event
from utils.logger import get_logger, LogCategory


class VectorClockManager:
    """Manages vector clock ordering for events in distributed systems."""

    def __init__(self, num_processes: int):
        self.num_processes = num_processes
        self.expected_vc = [0] * num_processes
        self.holding_queue: List[Event] = []
        self.logger = get_logger()

        self.stats = {
            "events_checked": 0,
            "events_in_order": 0,
            "events_out_of_order": 0,
            "queue_operations": 0,
            "vc_updates": 0,
        }

        self.logger.debug(
            f"VectorClockManager initialized for {num_processes} processes",
            LogCategory.VECTOR_CLOCK,
            expected_vc=self.expected_vc,
        )

    def get_involved_indices(self, event: Event) -> List[int]:
        """Get indices of processes involved in the event."""
        indices = []
        self.logger.trace(
            f"Getting involved indices for event {event.name}",
            LogCategory.VECTOR_CLOCK,
            event_processes=event.processes,
        )

        for proc_repr in event.processes:
            if isinstance(proc_repr, str) and proc_repr.startswith("P"):
                try:
                    index = int(proc_repr[1:]) - 1
                    indices.append(index)
                    self.logger.trace(
                        f"Process {proc_repr} -> index {index}",
                        LogCategory.VECTOR_CLOCK,
                    )
                except ValueError:
                    self.logger.warn(
                        f"Invalid process representation: {proc_repr}",
                        LogCategory.VECTOR_CLOCK,
                        event_name=event.name,
                    )
                    continue

        self.logger.trace(
            f"Event {event.name} involves processes at indices: {indices}",
            LogCategory.VECTOR_CLOCK,
        )
        return indices

    def is_event_in_order(self, event: Event) -> bool:
        """Check if event can be delivered according to vector clock ordering."""
        self.stats["events_checked"] += 1

        involved_indices = self.get_involved_indices(event)
        is_in_order = self._is_event_in_order_multi(
            event.vector_clock, self.expected_vc, involved_indices
        )

        self._update_order_statistics(is_in_order)
        self._log_order_check(event, involved_indices, is_in_order)

        return is_in_order

    def _update_order_statistics(self, is_in_order: bool) -> None:
        """Update order statistics."""
        if is_in_order:
            self.stats["events_in_order"] += 1
        else:
            self.stats["events_out_of_order"] += 1

    def _log_order_check(
        self, event: Event, involved_indices: List[int], is_in_order: bool
    ) -> None:
        """Log order check results."""
        self.logger.debug(
            f"Vector clock order check for {event.name}",
            LogCategory.VECTOR_CLOCK,
            event_vc=event.vector_clock,
            expected_vc=self.expected_vc,
            involved_indices=involved_indices,
            in_order=is_in_order,
        )

        if not is_in_order:
            self._log_order_violation(event, involved_indices)

    def _is_event_in_order_multi(
        self, event_vc: List[int], expected_vc: List[int], involved: List[int]
    ) -> bool:
        """Check if event is in order for multiple involved processes."""
        self.logger.trace(
            "Multi-process order check",
            LogCategory.VECTOR_CLOCK,
            event_vc=event_vc,
            expected_vc=expected_vc,
            involved_processes=involved,
        )

        for i in involved:
            if not self._is_process_order_valid(event_vc, expected_vc, i):
                return False

        return True

    def _is_process_order_valid(
        self, event_vc: List[int], expected_vc: List[int], process_idx: int
    ) -> bool:
        """Check if process order is valid for given index."""
        if process_idx >= len(event_vc) or process_idx >= len(expected_vc):
            self.logger.error(
                f"Vector clock index out of bounds: {process_idx}",
                LogCategory.VECTOR_CLOCK,
                event_vc_length=len(event_vc),
                expected_vc_length=len(expected_vc),
                involved_index=process_idx,
            )
            return False

        if event_vc[process_idx] != expected_vc[process_idx] + 1:
            self.logger.trace(
                f"Process {process_idx}: event_vc[{process_idx}]={event_vc[process_idx]} != "
                f"expected[{process_idx}]+1={expected_vc[process_idx] + 1}",
                LogCategory.VECTOR_CLOCK,
            )
            return False

        self.logger.trace(
            f"Process {process_idx}: order check passed "
            f"({event_vc[process_idx]} == {expected_vc[process_idx] + 1})",
            LogCategory.VECTOR_CLOCK,
        )
        return True

    def _log_order_violation(self, event: Event, involved_indices: List[int]) -> None:
        """Log detailed information about why an event is out of order."""
        violations = self._collect_order_violations(event, involved_indices)

        self.logger.debug(
            f"Event {event.name} order violations:", LogCategory.VECTOR_CLOCK
        )
        for violation in violations:
            self.logger.debug(
                f"  Process {violation['process']}: expected {violation['expected']}, "
                f"got {violation['actual']} (diff: {violation['difference']})",
                LogCategory.VECTOR_CLOCK,
            )

    def _collect_order_violations(
        self, event: Event, involved_indices: List[int]
    ) -> List[Dict[str, Any]]:
        """Collect order violations for logging."""
        violations = []

        for i in involved_indices:
            if i < len(event.vector_clock) and i < len(self.expected_vc):
                expected_val = self.expected_vc[i] + 1
                actual_val = event.vector_clock[i]
                if actual_val != expected_val:
                    violations.append(
                        {
                            "process": i,
                            "expected": expected_val,
                            "actual": actual_val,
                            "difference": actual_val - expected_val,
                        }
                    )

        return violations

    def update_expected_vc(self, event: Event) -> None:
        """Update expected vector clock after processing an event."""
        self.stats["vc_updates"] += 1

        old_vc = self.expected_vc.copy()
        involved_indices = self.get_involved_indices(event)

        self._update_vector_clock_components(event, involved_indices)
        self._log_vector_clock_update(event, old_vc, involved_indices)

    def _update_vector_clock_components(
        self, event: Event, involved_indices: List[int]
    ) -> None:
        """Update vector clock components for involved processes."""
        for i in involved_indices:
            if i < len(self.expected_vc):
                self.expected_vc[i] = event.vector_clock[i]

    def _log_vector_clock_update(
        self, event: Event, old_vc: List[int], involved_indices: List[int]
    ) -> None:
        """Log vector clock update details."""
        self.logger.debug(
            f"Updated expected VC after processing {event.name}",
            LogCategory.VECTOR_CLOCK,
            old_vc=old_vc,
            new_vc=self.expected_vc,
            involved_processes=involved_indices,
            event_vc=event.vector_clock,
        )

        for i in involved_indices:
            if i < len(old_vc):
                self.logger.trace(
                    f"Process {i}: {old_vc[i]} -> {self.expected_vc[i]}",
                    LogCategory.VECTOR_CLOCK,
                )

    def add_to_holding_queue(self, event: Event) -> None:
        """Add event to holding queue for later processing."""
        self.stats["queue_operations"] += 1

        queue_size_before = len(self.holding_queue)
        self.holding_queue.append(event)

        self._log_queue_addition(event, queue_size_before)
        self.logger.increment_counter("events_queued")

    def _log_queue_addition(self, event: Event, queue_size_before: int) -> None:
        """Log queue addition details."""
        self.logger.debug(
            f"Added {event.name} to holding queue",
            LogCategory.VECTOR_CLOCK,
            event_vc=event.vector_clock,
            queue_size_before=queue_size_before,
            queue_size_after=len(self.holding_queue),
        )

        if self._should_trace_queue_state():
            queue_events = [e.name for e in self.holding_queue]
            self.logger.trace(
                f"Current holding queue: {queue_events}", LogCategory.VECTOR_CLOCK
            )

    def _should_trace_queue_state(self) -> bool:
        """Check if queue state should be traced."""
        return (
            self.logger._should_log(self.logger.level, LogCategory.VECTOR_CLOCK)
            and self.logger.level.value == "debug"
        )

    def get_ready_events_from_queue(self) -> List[Event]:
        """Get events from holding queue that are now ready for processing."""
        if not self.holding_queue:
            return []

        self.stats["queue_operations"] += 1

        ready_events, remaining_events = self._partition_queue_events()
        self._update_holding_queue(remaining_events)
        self._log_queue_flush_results(ready_events, remaining_events)

        return ready_events

    def _partition_queue_events(self) -> tuple[List[Event], List[Event]]:
        """Partition queue events into ready and remaining."""
        ready_events = []
        remaining_events = []

        self.logger.debug(
            f"Checking {len(self.holding_queue)} queued events for readiness",
            LogCategory.VECTOR_CLOCK,
            expected_vc=self.expected_vc,
        )

        for event in self.holding_queue:
            if self.is_event_in_order(event):
                ready_events.append(event)
                self.logger.debug(
                    f"Event {event.name} is now ready for processing",
                    LogCategory.VECTOR_CLOCK,
                    event_vc=event.vector_clock,
                )
            else:
                remaining_events.append(event)
                self.logger.trace(
                    f"Event {event.name} still not ready",
                    LogCategory.VECTOR_CLOCK,
                    event_vc=event.vector_clock,
                )

        return ready_events, remaining_events

    def _update_holding_queue(self, remaining_events: List[Event]) -> None:
        """Update holding queue with remaining events."""
        self.holding_queue = remaining_events

    def _log_queue_flush_results(
        self, ready_events: List[Event], remaining_events: List[Event]
    ) -> None:
        """Log queue flush results."""
        self.logger.debug(
            f"Queue flush result: {len(ready_events)} ready, {len(remaining_events)} remaining",
            LogCategory.VECTOR_CLOCK,
        )

        if ready_events:
            ready_names = [e.name for e in ready_events]
            self.logger.info(
                f"Ready events from queue: {ready_names}", LogCategory.VECTOR_CLOCK
            )
            self.logger.increment_counter("events_dequeued", len(ready_events))

    def has_pending_events(self) -> bool:
        """Check if there are events in the holding queue."""
        has_pending = len(self.holding_queue) > 0

        if has_pending:
            self.logger.trace(
                f"Holding queue has {len(self.holding_queue)} pending events",
                LogCategory.VECTOR_CLOCK,
            )

        return has_pending

    def get_pending_event_names(self) -> List[str]:
        """Get names of events in the holding queue."""
        names = [event.name for event in self.holding_queue]

        if names:
            self.logger.debug(
                f"Pending events in queue: {names}", LogCategory.VECTOR_CLOCK
            )

        return names

    def analyze_queue_state(self) -> Dict[str, Any]:
        """Analyze the current state of the holding queue."""
        if not self.holding_queue:
            return {"queue_size": 0, "analysis": "Queue is empty"}

        analysis = {
            "queue_size": len(self.holding_queue),
            "events": [],
            "blocking_reasons": {},
            "earliest_event": None,
            "process_gaps": {},
        }

        self._analyze_queued_events(analysis)
        self._analyze_process_gaps(analysis)

        self.logger.debug(
            "Queue state analysis completed",
            LogCategory.VECTOR_CLOCK,
            queue_size=analysis["queue_size"],
            process_gaps=len(analysis["process_gaps"]),
        )

        return analysis

    def _analyze_queued_events(self, analysis: Dict[str, Any]) -> None:
        """Analyze individual events in the queue."""
        for event in self.holding_queue:
            involved = self.get_involved_indices(event)
            violations = self._analyze_event_violations(event, involved)

            event_analysis = {
                "name": event.name,
                "vector_clock": event.vector_clock,
                "involved_processes": involved,
                "violations": violations,
            }

            analysis["events"].append(event_analysis)

    def _analyze_event_violations(
        self, event: Event, involved: List[int]
    ) -> List[Dict[str, Any]]:
        """Analyze violations for a specific event."""
        violations = []

        for i in involved:
            if i < len(event.vector_clock) and i < len(self.expected_vc):
                expected = self.expected_vc[i] + 1
                actual = event.vector_clock[i]
                if actual != expected:
                    violations.append(
                        {
                            "process": i,
                            "expected": expected,
                            "actual": actual,
                            "gap": actual - expected,
                        }
                    )

        return violations

    def _analyze_process_gaps(self, analysis: Dict[str, Any]) -> None:
        """Analyze process gaps (missing events)."""
        for i in range(self.num_processes):
            max_seen = max(
                (
                    e.vector_clock[i]
                    for e in self.holding_queue
                    if i < len(e.vector_clock)
                ),
                default=0,
            )
            current_expected = self.expected_vc[i]

            if max_seen > current_expected:
                analysis["process_gaps"][f"P{i + 1}"] = {
                    "current": current_expected,
                    "max_seen": max_seen,
                    "missing_count": max_seen - current_expected,
                }

    def log_queue_analysis(self) -> None:
        """Log detailed analysis of the current queue state."""
        if not self.holding_queue:
            self.logger.debug("Holding queue is empty", LogCategory.VECTOR_CLOCK)
            return

        analysis = self.analyze_queue_state()
        self._log_queue_analysis_header(analysis)
        self._log_queue_events_analysis(analysis)
        self._log_process_gaps_analysis(analysis)

    def _log_queue_analysis_header(self, analysis: Dict[str, Any]) -> None:
        """Log queue analysis header information."""
        self.logger.debug("=== HOLDING QUEUE ANALYSIS ===", LogCategory.VECTOR_CLOCK)
        self.logger.debug(
            f"Queue size: {analysis['queue_size']}", LogCategory.VECTOR_CLOCK
        )
        self.logger.debug(
            f"Current expected VC: {self.expected_vc}", LogCategory.VECTOR_CLOCK
        )

    def _log_queue_events_analysis(self, analysis: Dict[str, Any]) -> None:
        """Log analysis of individual events in queue."""
        for event_info in analysis["events"]:
            self.logger.debug(f"Event {event_info['name']}:", LogCategory.VECTOR_CLOCK)
            self.logger.debug(
                f"  VC: {event_info['vector_clock']}", LogCategory.VECTOR_CLOCK
            )
            self.logger.debug(
                f"  Involved: {event_info['involved_processes']}",
                LogCategory.VECTOR_CLOCK,
            )

            if event_info["violations"]:
                self.logger.debug("  Violations:", LogCategory.VECTOR_CLOCK)
                for v in event_info["violations"]:
                    self.logger.debug(
                        f"    P{v['process']}: expected {v['expected']}, got {v['actual']} (gap: {v['gap']})",
                        LogCategory.VECTOR_CLOCK,
                    )

    def _log_process_gaps_analysis(self, analysis: Dict[str, Any]) -> None:
        """Log analysis of process gaps."""
        if analysis["process_gaps"]:
            self.logger.debug(
                "Process gaps (missing events):", LogCategory.VECTOR_CLOCK
            )
            for proc, gap_info in analysis["process_gaps"].items():
                self.logger.debug(
                    f"  {proc}: current={gap_info['current']}, max_seen={gap_info['max_seen']}, "
                    f"missing={gap_info['missing_count']}",
                    LogCategory.VECTOR_CLOCK,
                )

    def get_statistics(self) -> Dict[str, Any]:
        """Get vector clock management statistics."""
        stats = self.stats.copy()
        stats.update(
            {
                "current_expected_vc": self.expected_vc.copy(),
                "holding_queue_size": len(self.holding_queue),
                "num_processes": self.num_processes,
            }
        )

        self._calculate_derived_statistics(stats)
        return stats

    def _calculate_derived_statistics(self, stats: Dict[str, Any]) -> None:
        """Calculate derived statistics."""
        if stats["events_checked"] > 0:
            stats["in_order_percentage"] = (
                stats["events_in_order"] / stats["events_checked"]
            ) * 100
            stats["out_of_order_percentage"] = (
                stats["events_out_of_order"] / stats["events_checked"]
            ) * 100
        else:
            stats["in_order_percentage"] = 0
            stats["out_of_order_percentage"] = 0

    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        old_stats = self.stats.copy()
        self.stats = {
            "events_checked": 0,
            "events_in_order": 0,
            "events_out_of_order": 0,
            "queue_operations": 0,
            "vc_updates": 0,
        }

        self.logger.debug(
            "Vector clock statistics reset",
            LogCategory.VECTOR_CLOCK,
            previous_stats=old_stats,
        )

    def are_concurrent(self, vc1: List[int], vc2: List[int]) -> bool:
        """Check if two vector clocks represent concurrent events."""
        if len(vc1) != len(vc2):
            return False

        vc1_le_vc2 = all(vc1[i] <= vc2[i] for i in range(len(vc1)))
        vc2_le_vc1 = all(vc2[i] <= vc1[i] for i in range(len(vc2)))

        return not (vc1_le_vc2 or vc2_le_vc1)

    def find_concurrent_events(
        self, event: Event, recent_events: List[Event]
    ) -> List[Event]:
        """Find events that are concurrent with the given event."""
        concurrent = []
        event_vc = event.vector_clock

        for recent_event in recent_events:
            if self.are_concurrent(event_vc, recent_event.vector_clock):
                concurrent.append(recent_event)

        return concurrent

    def __str__(self) -> str:
        """String representation of the vector clock manager state."""
        queue_events = [e.name for e in self.holding_queue]
        return (
            f"VectorClockManager(expected_vc={self.expected_vc}, "
            f"queue_size={len(self.holding_queue)}, "
            f"queued_events={queue_events})"
        )

    def __repr__(self) -> str:
        """Detailed representation of the vector clock manager."""
        return self.__str__()
