#!/usr/bin/env python3
"""
Vector Clock Fixer for PoET Traces

This script takes a JSON trace file without vector clocks and adds proper
Fidge-Mattern vector clocks to make it compatible with PoET.

The script properly handles:
- Local events (single process)
- Inter-process communication (multiple processes)
- Causal ordering preservation
- Concurrent event detection

Usage:
    python vector_clock_fixer.py input_trace.json output_trace.json
    python vector_clock_fixer.py input_trace.json  # overwrites input file
"""

import json
import sys
from typing import List, Dict, Any, Set, Tuple


class VectorClockGenerator:
    """Generates Fidge-Mattern vector clocks for distributed system traces."""

    def __init__(self, num_processes: int):
        self.num_processes = num_processes
        # Each process maintains its own vector clock
        self.process_clocks = [[0] * num_processes for _ in range(num_processes)]

    def parse_process_ids(self, processes: List[str]) -> List[int]:
        """
        Parse process IDs like ["P1", "P2"] into indices [0, 1].

        Args:
            processes: List of process strings like ["P1", "P2"]

        Returns:
            List of zero-based process indices
        """
        indices = []
        for proc in processes:
            if isinstance(proc, str):
                # Handle both "P1" and "P2,P3" formats
                if "," in proc:
                    # Split comma-separated processes
                    sub_procs = [p.strip() for p in proc.split(",")]
                    for sub_proc in sub_procs:
                        if sub_proc.startswith("P"):
                            try:
                                index = int(sub_proc[1:]) - 1
                                if 0 <= index < self.num_processes:
                                    indices.append(index)
                            except ValueError:
                                print(f"Warning: Invalid process ID format: {sub_proc}")
                elif proc.startswith("P"):
                    try:
                        index = int(proc[1:]) - 1
                        if 0 <= index < self.num_processes:
                            indices.append(index)
                    except ValueError:
                        print(f"Warning: Invalid process ID format: {proc}")
                else:
                    print(f"Warning: Unexpected process format: {proc}")
            else:
                print(f"Warning: Process must be string, got: {type(proc)}")

        # Remove duplicates while preserving order
        unique_indices = []
        for idx in indices:
            if idx not in unique_indices:
                unique_indices.append(idx)

        return unique_indices

    def generate_event_vector_clock(self, involved_processes: List[int]) -> List[int]:
        """
        Generate vector clock for an event involving specified processes.

        Implements Fidge-Mattern algorithm:
        - For local event: increment own clock
        - For communication: merge clocks and increment all involved

        Args:
            involved_processes: List of process indices involved in this event

        Returns:
            Vector clock for this event
        """
        if not involved_processes:
            return [0] * self.num_processes

        if len(involved_processes) == 1:
            # Local event: increment own clock
            proc_idx = involved_processes[0]
            self.process_clocks[proc_idx][proc_idx] += 1
            return self.process_clocks[proc_idx].copy()
        else:
            # Inter-process communication event
            # Step 1: Merge vector clocks (take maximum for each position)
            merged_clock = [0] * self.num_processes
            for i in range(self.num_processes):
                merged_clock[i] = max(self.process_clocks[proc][i]
                                      for proc in involved_processes)

            # Step 2: Increment clocks for all involved processes
            for proc_idx in involved_processes:
                merged_clock[proc_idx] += 1

            # Step 3: Update all involved processes' clocks
            for proc_idx in involved_processes:
                self.process_clocks[proc_idx] = merged_clock.copy()

            return merged_clock.copy()

    def add_vector_clocks_to_trace(self, trace_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add vector clocks to all events in the trace.

        Args:
            trace_data: Dictionary containing 'processes' and 'events'

        Returns:
            Updated trace data with vector clocks added
        """
        events = trace_data["events"]
        print(f"Processing trace with {self.num_processes} processes and {len(events)} events...")

        updated_events = []

        for i, event in enumerate(events):
            # Parse event structure: [name, processes, propositions, ...]
            if len(event) < 3:
                print(f"Error: Event {i} has invalid format: {event}")
                continue

            event_name = event[0]
            event_processes = event[1]
            event_propositions = event[2]

            # Parse which processes are involved
            involved_indices = self.parse_process_ids(event_processes)

            if not involved_indices:
                print(f"Warning: Event {event_name} has no valid processes, skipping")
                continue

            # Generate vector clock for this event
            vector_clock = self.generate_event_vector_clock(involved_indices)

            # Create new event with vector clock
            new_event = [event_name, event_processes, event_propositions, vector_clock]

            # Preserve any additional fields from original event
            if len(event) > 3:
                new_event.extend(event[3:])

            updated_events.append(new_event)

            # Debug output for first few events
            if i < 10:
                proc_info = ", ".join([f"P{idx + 1}" for idx in involved_indices])
                event_type = "local" if len(involved_indices) == 1 else "communication"
                print(f"Event {i:2d}: {event_name:15s} [{proc_info:8s}] {event_type:13s} -> VC: {vector_clock}")

        # Create updated trace data
        updated_trace = trace_data.copy()
        updated_trace["events"] = updated_events

        print(f"\nSuccessfully added vector clocks to {len(updated_events)} events")

        # Show final state of all process clocks
        print("\nFinal vector clock state for each process:")
        for i, clock in enumerate(self.process_clocks):
            print(f"  P{i + 1}: {clock}")

        return updated_trace


def validate_trace_format(trace_data: Dict[str, Any]) -> bool:
    """
    Validate that the trace has the required format.

    Args:
        trace_data: Trace dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["processes", "events"]

    for field in required_fields:
        if field not in trace_data:
            print(f"Error: Missing required field '{field}' in trace data")
            return False

    if not isinstance(trace_data["processes"], int):
        print("Error: 'processes' field must be an integer")
        return False

    if not isinstance(trace_data["events"], list):
        print("Error: 'events' field must be a list")
        return False

    if trace_data["processes"] <= 0:
        print("Error: Number of processes must be positive")
        return False

    # Validate event structure
    for i, event in enumerate(trace_data["events"]):
        if not isinstance(event, list) or len(event) < 3:
            print(f"Error: Event {i} must be a list with at least 3 elements: [name, processes, propositions]")
            return False

        if not isinstance(event[1], list):
            print(f"Error: Event {i} processes field must be a list")
            return False

        if not isinstance(event[2], list):
            print(f"Error: Event {i} propositions field must be a list")
            return False

    return True


def analyze_trace_causality(trace_data: Dict[str, Any]) -> None:
    """
    Analyze the trace to understand causality patterns.

    Args:
        trace_data: Trace data to analyze
    """
    events = trace_data["events"]
    num_processes = trace_data["processes"]

    print(f"\n=== TRACE ANALYSIS ===")
    print(f"Total events: {len(events)}")
    print(f"Total processes: {num_processes}")

    # Count event types
    local_events = 0
    communication_events = 0
    process_event_counts = [0] * num_processes

    generator = VectorClockGenerator(num_processes)

    for event in events:
        involved = generator.parse_process_ids(event[1])

        if len(involved) == 1:
            local_events += 1
            process_event_counts[involved[0]] += 1
        elif len(involved) > 1:
            communication_events += 1
            for proc in involved:
                process_event_counts[proc] += 1

    print(f"Local events: {local_events}")
    print(f"Communication events: {communication_events}")
    print(f"Events per process:")
    for i, count in enumerate(process_event_counts):
        print(f"  P{i + 1}: {count} events")


def main():
    """Main function to process command line arguments and fix trace file."""
    if len(sys.argv) < 2:
        print("Usage: python vector_clock_fixer.py <input_trace.json> [output_trace.json]")
        print("If output file is not specified, input file will be overwritten.")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file

    # Read input trace
    try:
        with open(input_file, 'r') as f:
            trace_data = json.load(f)
        print(f"Loaded trace from: {input_file}")
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{input_file}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading '{input_file}': {e}")
        sys.exit(1)

    # Validate trace format
    if not validate_trace_format(trace_data):
        print("Error: Invalid trace format")
        sys.exit(1)

    # Analyze trace before processing
    analyze_trace_causality(trace_data)

    # Add vector clocks
    try:
        generator = VectorClockGenerator(trace_data["processes"])
        updated_trace = generator.add_vector_clocks_to_trace(trace_data)
    except Exception as e:
        print(f"Error adding vector clocks: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Write output trace
    try:
        with open(output_file, 'w') as f:
            json.dump(updated_trace, f, indent=2)
        print(f"\nFixed trace written to: {output_file}")
    except Exception as e:
        print(f"Error writing to '{output_file}': {e}")
        sys.exit(1)

    # Summary
    original_events = len(trace_data["events"])
    fixed_events = len(updated_trace["events"])

    if original_events != fixed_events:
        print(f"Warning: {original_events - fixed_events} events were skipped due to errors")

    print("Vector clock fixing completed successfully!")

    # Show sample of first few events
    print("\nSample of fixed events:")
    for i, event in enumerate(updated_trace["events"][:5]):
        vc_str = f"VC:{event[3]}" if len(event) > 3 else "No VC"
        print(f"  {i}: {event[0]} {event[1]} -> {vc_str}")

    if len(updated_trace["events"]) > 5:
        print(f"  ... and {len(updated_trace['events']) - 5} more events")


if __name__ == "__main__":
    main()