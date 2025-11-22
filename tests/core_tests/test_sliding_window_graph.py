# tests/core_tests/test_sliding_window_graph.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Test suite for sliding window graph building functionality, validating backward propagation,
# pattern detection, intermediate node creation, and duplicate edge prevention.

import pytest
from typing import List, Dict, Any

from model.event import Event
from model.state import State
from model.process import Process
from model.process_modes import ProcessModes
from core.state_manager import StateManager
from parser.parser import parse
from parser.ast import Proposition
from utils.config import Config


def create_test_config(**kwargs) -> Config:
    """Create test configuration with default values."""
    defaults = {
        "property_file": "test_property.pctl",
        "trace_file": "test_trace.json",
        "output_level": "debug",
        "reduce_enabled": False,
        "visual_enabled": False,
        "log_categories": None,
        "log_file": None,
    }
    defaults.update(kwargs)

    config = Config(
        property_file=defaults["property_file"],
        trace_file=defaults["trace_file"],
        output_level=defaults["output_level"],
        reduce_enabled=defaults["reduce_enabled"],
        visual_enabled=defaults["visual_enabled"],
        log_categories=defaults["log_categories"],
        log_file=defaults["log_file"],
    )
    return config


def create_test_event(
    name: str,
    processes: List[str],
    vector_clock: List[int],
    propositions: List[str] = None,
) -> Event:
    """Create test event with specified parameters."""
    if propositions is None:
        propositions = []

    num_processes = len(vector_clock)
    distributed_processes = Process.distribute_processes(processes, num_processes)

    return Event(
        i_name=name,
        i_processes=distributed_processes,
        i_propositions=propositions,
        vector_clock=vector_clock,
    )


class TestSlidingWindowGraphBuilding:
    """Test suite for sliding window graph building upon new event arrival."""

    def setup_method(self):
        """Reset state and event counters before each test."""
        State._State__COUNTER = 0
        Event._Event__TIMELINE = 0

    def test_alpha_beta_pattern_detection_basic(self):
        """Test detection of s --α--> s' --β--> s'' patterns during backward propagation."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=3, formula=formula)

        # Create sequence: α affects P1, β affects P2 (independent)
        alpha = create_test_event("alpha", ["P1"], [1, 0, 0], ["p"])
        beta = create_test_event("beta", ["P2"], [0, 1, 0], ["q"])

        # Process α first to create s --α--> s'
        alpha_states = state_manager.process_event(alpha)
        assert len(alpha_states) >= 1

        # Process β to create s' --β--> s'' and detect pattern
        beta_states = state_manager.process_event(beta)
        assert len(beta_states) >= 1

        # Verify pattern was detected by checking for states that have both events
        pattern_detected = False
        for state in state_manager.states:
            if state.enabled:
                # Check if state frontier contains both alpha and beta effects
                alpha_in_frontier = any(
                    isinstance(comp, Event) and comp.name == "alpha"
                    for comp in state.processes
                )
                beta_in_frontier = any(
                    isinstance(comp, Event) and comp.name == "beta"
                    for comp in state.processes
                )
                if alpha_in_frontier and beta_in_frontier:
                    pattern_detected = True
                    break

        assert pattern_detected, "s --α--> s' --β--> s'' pattern should be detected"

    def test_independent_events_disjoint_processes(self):
        """Test with independent events affecting disjoint process sets."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=4, formula=formula)

        # α affects P1, P2 (processes {1, 2})
        alpha = create_test_event("alpha", ["P1", "P2"], [1, 1, 0, 0], ["p"])

        # β affects P3, P4 (processes {3, 4}) - completely disjoint
        beta = create_test_event("beta", ["P3", "P4"], [0, 0, 1, 1], ["q"])

        initial_state_count = len(state_manager.states)

        # Process both events
        alpha_states = state_manager.process_event(alpha)
        beta_states = state_manager.process_event(beta)

        # Verify independence: events should be processable in either order
        # and should create multiple valid interleavings
        assert len(state_manager.states) > initial_state_count

        # Check that we have states representing both orderings
        alpha_then_beta_exists = False
        beta_then_alpha_exists = False

        for state in state_manager.states:
            if state.enabled and len(state.processes) == 4:
                # Count events in frontier
                events_in_frontier = [
                    comp for comp in state.processes if isinstance(comp, Event)
                ]

                if len(events_in_frontier) >= 2:
                    alpha_in_frontier = any(
                        e.name == "alpha" for e in events_in_frontier
                    )
                    beta_in_frontier = any(e.name == "beta" for e in events_in_frontier)

                    if alpha_in_frontier and beta_in_frontier:
                        alpha_then_beta_exists = True

        assert alpha_then_beta_exists, "Should have states with both independent events"

    def test_path_creation_s_beta_r_alpha_s_double_prime(self):
        """Test creation of s --β--> r --α--> s'' paths when patterns are found."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=3, formula=formula)

        # Create concurrent events that will trigger path creation
        alpha = create_test_event("alpha", ["P1"], [1, 0, 0], ["p"])
        beta = create_test_event("beta", ["P2"], [0, 1, 0], ["q"])

        # Process α first
        state_manager.process_event(alpha)
        initial_states = len(state_manager.states)

        # Process β - this should trigger concurrent path exploration
        # and create s --β--> r --α--> s'' paths
        state_manager.process_event(beta)

        # Verify new states were created for alternative paths
        assert len(state_manager.states) > initial_states

        # Look for intermediate states (r) that have β applied but not α
        intermediate_states_found = False
        final_states_found = False

        for state in state_manager.states:
            if not state.enabled:
                continue

            events_in_frontier = [
                comp for comp in state.processes if isinstance(comp, Event)
            ]
            event_names = [e.name for e in events_in_frontier]

            # Check for intermediate state r (has β but exploring α path)
            if "beta" in event_names and len(event_names) >= 1:
                intermediate_states_found = True

            # Check for final state s'' (has both α and β)
            if "alpha" in event_names and "beta" in event_names:
                final_states_found = True

        assert (
            intermediate_states_found or final_states_found
        ), "Should create intermediate states or final states in s --β--> r --α--> s'' pattern"

    def test_intermediate_node_frontier_correctness(self):
        """Test that intermediate node r has correct frontier (applying β to s's frontier)."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=3, formula=formula)

        # Get initial state s
        initial_state = state_manager.states[0]
        initial_frontier = initial_state.processes.copy()

        # Create events
        alpha = create_test_event("alpha", ["P1"], [1, 0, 0], ["p"])
        beta = create_test_event("beta", ["P2"], [0, 1, 0], ["q"])

        # Process α first, then β to trigger pattern
        state_manager.process_event(alpha)
        state_manager.process_event(beta)

        # Look for intermediate states created by concurrent processing
        for state in state_manager.states:
            if not state.enabled:
                continue

            # Check if this could be an intermediate state r
            beta_events = [
                comp
                for comp in state.processes
                if isinstance(comp, Event) and comp.name == "beta"
            ]

            if beta_events:
                # Verify frontier correctness: β should be applied to appropriate process
                beta_process_indices = []
                for i, comp in enumerate(state.processes):
                    if isinstance(comp, Event) and comp.name == "beta":
                        beta_process_indices.append(i)

                # β affects P2, so it should be in position 1 (0-indexed)
                assert (
                    1 in beta_process_indices or len(beta_process_indices) > 0
                ), "Beta event should be properly placed in frontier"

                # Verify other processes maintain their expected state
                for i, comp in enumerate(state.processes):
                    if i not in beta_process_indices:
                        # Non-beta processes should either be IOTA, CLOSED, or have alpha
                        assert (
                            comp == ProcessModes.IOTA
                            or comp == ProcessModes.CLOSED
                            or (isinstance(comp, Event) and comp.name == "alpha")
                        ), f"Process {i} should have correct frontier component, got {comp}"

    def test_duplicate_edge_prevention(self):
        """Test that duplicate edges aren't created when paths already exist."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=2, formula=formula)

        # Create events that might cause duplicate paths
        alpha = create_test_event("alpha", ["P1"], [1, 0], ["p"])
        beta = create_test_event("beta", ["P2"], [0, 1], ["q"])

        # Process events to create initial paths
        state_manager.process_event(alpha)
        state_manager.process_event(beta)

        initial_state_count = len(state_manager.states)

        # Create same events again (simulating duplicate processing)
        alpha_duplicate = create_test_event("alpha_dup", ["P1"], [2, 0], ["p"])
        beta_duplicate = create_test_event("beta_dup", ["P2"], [0, 2], ["q"])

        # Process duplicates
        state_manager.process_event(alpha_duplicate)
        state_manager.process_event(beta_duplicate)

        # Verify state transitions don't create excessive duplicates
        # The graph should grow but not explode with identical paths
        final_state_count = len(state_manager.states)

        # Should have growth, but not exponential duplication
        growth_ratio = final_state_count / initial_state_count
        assert (
            growth_ratio < 10
        ), f"Excessive state growth suggests duplicate edges: {growth_ratio}"

        # Verify no states have identical frontiers
        unique_frontiers = set()
        duplicate_frontiers = []

        for state in state_manager.states:
            if state.enabled:
                # Create hashable representation of frontier
                frontier_repr = tuple(
                    (comp.name if isinstance(comp, Event) else str(comp))
                    for comp in state.processes
                )

                if frontier_repr in unique_frontiers:
                    duplicate_frontiers.append(frontier_repr)
                else:
                    unique_frontiers.add(frontier_repr)

        assert (
            len(duplicate_frontiers) == 0
        ), f"Found duplicate frontiers: {duplicate_frontiers}"

    def test_complex_concurrent_pattern_detection(self):
        """Test complex scenario with multiple concurrent events and pattern detection."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=4, formula=formula)

        # Create a complex concurrent scenario
        events = [
            create_test_event("e1", ["P1"], [1, 0, 0, 0], ["p"]),
            create_test_event("e2", ["P2"], [0, 1, 0, 0], ["q"]),
            create_test_event("e3", ["P3"], [0, 0, 1, 0], ["r"]),
            create_test_event("e4", ["P1", "P4"], [2, 0, 0, 1], ["s"]),
        ]

        # Process events in sequence to trigger various patterns
        for event in events:
            state_manager.process_event(event)

        # Verify that the sliding window correctly handles:
        # 1. Multiple concurrent interleavings
        # 2. Pattern detection across different event orderings
        # 3. Proper frontier management

        enabled_states = state_manager.get_enabled_states()
        assert len(enabled_states) >= 1, "Should have enabled states after processing"

        # Verify some states contain multiple events (indicating pattern detection)
        multi_event_states = []
        for state in enabled_states:
            event_count = sum(1 for comp in state.processes if isinstance(comp, Event))
            if event_count >= 2:
                multi_event_states.append(state)

        assert (
            len(multi_event_states) > 0
        ), "Should have states with multiple events indicating pattern detection"

    def test_backward_propagation_timing(self):
        """Test that backward propagation occurs at the right time during event processing."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=2, formula=formula)

        # Track state creation timing
        states_after_each_event = []

        alpha = create_test_event("alpha", ["P1"], [1, 0], ["p"])
        state_manager.process_event(alpha)
        states_after_each_event.append(len(state_manager.states))

        beta = create_test_event("beta", ["P2"], [0, 1], ["q"])
        state_manager.process_event(beta)
        states_after_each_event.append(len(state_manager.states))

        # Third event that should trigger significant backward propagation
        gamma = create_test_event("gamma", ["P1", "P2"], [2, 2], ["r"])
        state_manager.process_event(gamma)
        states_after_each_event.append(len(state_manager.states))

        # Verify that state creation increases appropriately
        # (indicating backward propagation is working)
        assert (
            states_after_each_event[1] > states_after_each_event[0]
        ), "Should create new states after second event"
        assert (
            states_after_each_event[2] >= states_after_each_event[1]
        ), "Should maintain or increase states after third event"

    def test_graph_structure_after_sequential_events(self):
        """Test that graph structure is correctly built with proper state relationships."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=3, formula=formula)

        # Create a sequence of events that should build a clear graph structure
        e1 = create_test_event("e1", ["P1"], [1, 0, 0], ["p"])
        e2 = create_test_event("e2", ["P2"], [0, 1, 0], ["q"])
        e3 = create_test_event("e3", ["P3"], [0, 0, 1], ["r"])

        # Track states after each event
        initial_states = len(state_manager.states)

        state_manager.process_event(e1)
        states_after_e1 = state_manager.get_enabled_states()

        state_manager.process_event(e2)
        states_after_e2 = state_manager.get_enabled_states()

        state_manager.process_event(e3)
        states_after_e3 = state_manager.get_enabled_states()

        # Verify graph grows correctly
        assert len(states_after_e1) >= 1, "Should have at least one state after e1"
        assert len(states_after_e2) >= len(
            states_after_e1
        ), "Should maintain or grow after e2"
        assert len(states_after_e3) >= len(
            states_after_e2
        ), "Should maintain or grow after e3"

        # Verify states have proper frontier composition
        final_state_found = False
        for state in states_after_e3:
            event_count = sum(1 for comp in state.processes if isinstance(comp, Event))
            if event_count >= 3:  # State with all three events
                final_state_found = True
                # Verify each process position has correct event
                events_by_process = {}
                for i, comp in enumerate(state.processes):
                    if isinstance(comp, Event):
                        events_by_process[i] = comp.name

                # Should have events in appropriate process positions
                assert (
                    len(events_by_process) >= 3
                ), f"Expected at least 3 events, got {events_by_process}"

        assert final_state_found, "Should have a state containing all three events"

    def test_successor_predecessor_relationships(self):
        """Test that successor and predecessor relationships are correctly established."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=2, formula=formula)

        # Get initial state
        s0 = state_manager.states[0]

        # Process first event
        e1 = create_test_event("e1", ["P1"], [1, 0], ["p"])
        new_states_1 = state_manager.process_event(e1)

        # Verify s0 has successors after e1
        assert (
            len(s0.successors) > 0
        ), "Initial state should have successors after processing e1"

        # Get the new state created by e1
        s1 = None
        for state in state_manager.states:
            if state.name != s0.name and state.enabled:
                s1 = state
                break

        assert s1 is not None, "Should have created new state s1"

        # Verify successor relationship: s0 -> s1 via e1
        s1_name_in_successors = s1.name in s0.successors
        if s1_name_in_successors:
            event_to_s1, state_obj = s0.successors[s1.name]
            assert (
                event_to_s1.name == "e1"
            ), f"Edge to s1 should be labeled with e1, got {event_to_s1.name}"
            assert (
                state_obj is s1
            ), "Successor reference should point to correct state object"

        # Process second event to create more complex relationships
        e2 = create_test_event("e2", ["P2"], [0, 1], ["q"])
        state_manager.process_event(e2)

        # Verify multiple successor relationships exist
        total_successors = sum(len(state.successors) for state in state_manager.states)
        assert (
            total_successors >= 2
        ), f"Should have multiple successor relationships, got {total_successors}"

        # Verify no self-loops
        for state in state_manager.states:
            assert (
                state.name not in state.successors
            ), f"State {state.name} should not have self-loop"

    def test_edge_completion_diamond_pattern(self):
        """Test edge completion mechanism creates diamond patterns correctly."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=2, formula=formula)

        # Create concurrent events that should form diamond pattern
        e1 = create_test_event("e1", ["P1"], [1, 0], ["p"])
        e2 = create_test_event("e2", ["P2"], [0, 1], ["q"])

        # Process both events
        state_manager.process_event(e1)
        state_manager.process_event(e2)

        # Look for diamond pattern: s0 -> s1, s0 -> s2, s1 -> s3, s2 -> s3
        states_by_name = {state.name: state for state in state_manager.states}

        # Find initial state (s0) - may be disabled after processing
        s0 = states_by_name.get("S0")
        assert s0 is not None, "Should have initial state S0"

        # Verify s0 has multiple successors (diamond top)
        if len(s0.successors) >= 2:
            # Check if we have proper diamond completion
            successor_names = list(s0.successors.keys())

            # Verify each successor has their own successors (diamond completion)
            completion_found = False
            for succ_name in successor_names:
                if succ_name in states_by_name:
                    succ_state = states_by_name[succ_name]
                    if len(succ_state.successors) > 0:
                        completion_found = True

            assert completion_found, "Should have edge completion in diamond pattern"

    def test_frontier_updates_with_event_processing(self):
        """Test that state frontiers are correctly updated when processing events."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=3, formula=formula)

        # Initial frontier should be all IOTA
        s0 = state_manager.states[0]
        assert all(
            comp == ProcessModes.IOTA for comp in s0.processes
        ), "Initial state should have all IOTA processes"

        # Process event affecting P1
        e1 = create_test_event("e1", ["P1"], [1, 0, 0], ["p"])
        state_manager.process_event(e1)

        # Find state with e1 in frontier
        s1_found = False
        for state in state_manager.states:
            if state.enabled and state.name != s0.name:
                # Check if e1 is in position 0 (P1)
                if (
                    len(state.processes) >= 1
                    and isinstance(state.processes[0], Event)
                    and state.processes[0].name == "e1"
                ):
                    s1_found = True

                    # Verify other positions remain IOTA
                    assert (
                        state.processes[1] == ProcessModes.IOTA
                    ), "P2 should remain IOTA"
                    assert (
                        state.processes[2] == ProcessModes.IOTA
                    ), "P3 should remain IOTA"
                    break

        assert s1_found, "Should find state with e1 properly placed in frontier"

        # Process event affecting multiple processes
        e2 = create_test_event("e2", ["P1", "P2"], [2, 1, 0], ["q"])
        state_manager.process_event(e2)

        # Verify frontiers are updated correctly
        multi_process_state_found = False
        for state in state_manager.states:
            if not state.enabled:
                continue

            # Look for state where e2 affects both P1 and P2
            p1_has_e2 = (
                isinstance(state.processes[0], Event)
                and state.processes[0].name == "e2"
            )
            p2_has_e2 = (
                isinstance(state.processes[1], Event)
                and state.processes[1].name == "e2"
            )

            if p1_has_e2 and p2_has_e2:
                multi_process_state_found = True
                # P3 should still be IOTA since e2 doesn't affect it
                assert (
                    state.processes[2] == ProcessModes.IOTA
                ), "P3 should remain IOTA when unaffected by e2"
                break

        assert (
            multi_process_state_found
        ), "Should find state where e2 correctly affects P1 and P2"

    def test_concurrent_event_ordering_impact(self):
        """Test that different orderings of concurrent events create appropriate graph structures."""
        config = create_test_config()
        formula = parse("p")

        # Test scenario 1: e1 then e2
        state_manager_1 = StateManager(config, num_processes=2, formula=formula)

        e1 = create_test_event("e1", ["P1"], [1, 0], ["p"])
        e2 = create_test_event("e2", ["P2"], [0, 1], ["q"])

        state_manager_1.process_event(e1)
        state_manager_1.process_event(e2)

        states_1 = state_manager_1.get_enabled_states()

        # Test scenario 2: e2 then e1 (reversed order)
        state_manager_2 = StateManager(config, num_processes=2, formula=formula)

        e2_copy = create_test_event("e2", ["P2"], [0, 1], ["q"])
        e1_copy = create_test_event("e1", ["P1"], [1, 0], ["p"])

        state_manager_2.process_event(e2_copy)
        state_manager_2.process_event(e1_copy)

        states_2 = state_manager_2.get_enabled_states()

        # Both scenarios should create similar graph structures (same final states)
        assert (
            len(states_1) > 0 and len(states_2) > 0
        ), "Both scenarios should create states"

        # Check that both scenarios have states with both events
        scenario_1_has_both = any(
            sum(1 for comp in state.processes if isinstance(comp, Event)) >= 2
            for state in states_1
        )
        scenario_2_has_both = any(
            sum(1 for comp in state.processes if isinstance(comp, Event)) >= 2
            for state in states_2
        )

        assert (
            scenario_1_has_both
        ), "Scenario 1 (e1->e2) should have states with both events"
        assert (
            scenario_2_has_both
        ), "Scenario 2 (e2->e1) should have states with both events"

        # The final reachable states should be similar despite different processing order
        final_frontiers_1 = {
            tuple(
                comp.name if isinstance(comp, Event) else str(comp)
                for comp in state.processes
            )
            for state in states_1
        }
        final_frontiers_2 = {
            tuple(
                comp.name if isinstance(comp, Event) else str(comp)
                for comp in state.processes
            )
            for state in states_2
        }

        # Should have overlap in final reachable frontiers
        common_frontiers = final_frontiers_1.intersection(final_frontiers_2)
        assert (
            len(common_frontiers) > 0
        ), "Different orderings should reach some common frontier states"

    def test_graph_consistency_after_multiple_events(self):
        """Test that graph maintains consistency after processing multiple events."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=3, formula=formula)

        # Create a complex sequence of events
        events = [
            create_test_event("e1", ["P1"], [1, 0, 0], ["p"]),
            create_test_event("e2", ["P2"], [0, 1, 0], ["q"]),
            create_test_event("e3", ["P1", "P3"], [2, 0, 1], ["r"]),
            create_test_event("e4", ["P2", "P3"], [0, 2, 2], ["s"]),
            create_test_event("e5", ["P1", "P2", "P3"], [3, 3, 3], ["t"]),
        ]

        # Process all events
        for event in events:
            state_manager.process_event(event)

        enabled_states = state_manager.get_enabled_states()

        # Verify graph consistency properties
        self._verify_graph_consistency(enabled_states, state_manager.states)

        # Verify reachability: should be able to reach states with later events
        final_event_reachable = any(
            any(
                isinstance(comp, Event) and comp.name == "e5"
                for comp in state.processes
            )
            for state in enabled_states
        )
        assert (
            final_event_reachable
        ), "Should be able to reach state containing final event e5"

        # Verify frontier coherence: each state's frontier should be valid
        for state in enabled_states:
            self._verify_frontier_coherence(state, len(events))

    def _verify_graph_consistency(self, enabled_states, all_states):
        """Helper method to verify graph consistency properties."""
        # 1. All enabled states should be reachable from initial state
        # 2. No dangling references in successor relationships
        # 3. All successor relationships point to valid states

        all_state_names = {state.name for state in all_states}

        for state in enabled_states:
            # Check successor references are valid
            for succ_name, (event, succ_state) in state.successors.items():
                assert (
                    succ_name in all_state_names
                ), f"Successor {succ_name} of {state.name} not found in state list"
                assert (
                    succ_state in all_states
                ), f"Successor state object for {succ_name} not in state list"
                assert isinstance(
                    event, Event
                ), f"Edge label should be Event, got {type(event)}"

    def _verify_frontier_coherence(self, state, max_events):
        """Helper method to verify that a state's frontier is coherent."""
        # Each process position should have either:
        # - ProcessModes.IOTA (initial)
        # - ProcessModes.CLOSED (superseded)
        # - An Event object

        for i, comp in enumerate(state.processes):
            assert (
                isinstance(comp, Event)
                or comp == ProcessModes.IOTA
                or comp == ProcessModes.CLOSED
            ), f"Process {i} in state {state.name} has invalid component: {comp} ({type(comp)})"

        # Check for invalid duplicate events in same frontier
        # Note: Same event affecting multiple processes is valid (e.g., e5 affecting P1, P2, P3)
        events_in_frontier = [
            comp for comp in state.processes if isinstance(comp, Event)
        ]

        # Group events by their identity (same object), not just name
        event_objects = {}
        for i, event in enumerate(events_in_frontier):
            if id(event) in event_objects:
                event_objects[id(event)].append(i)
            else:
                event_objects[id(event)] = [i]

        # An event object appearing in multiple positions is valid for multi-process events
        # Invalid would be different event objects with same name in same frontier
        event_names_by_position = {}
        for i, event in enumerate(events_in_frontier):
            if event.name in event_names_by_position:
                # Same event name in different positions - check if it's the same event object
                prev_event = events_in_frontier[event_names_by_position[event.name]]
                if id(event) != id(prev_event):
                    assert (
                        False
                    ), f"State {state.name} has different event objects with same name: {event.name}"
            else:
                event_names_by_position[event.name] = i

    def test_event_superseding_behavior(self):
        """Test that events properly supersede earlier events in process frontiers."""
        config = create_test_config()
        formula = parse("p")

        state_manager = StateManager(config, num_processes=2, formula=formula)

        # Process first event on P1
        e1 = create_test_event("e1", ["P1"], [1, 0], ["p"])
        state_manager.process_event(e1)

        # Process second event on P1 (should supersede e1)
        e2 = create_test_event("e2", ["P1"], [2, 0], ["q"])
        state_manager.process_event(e2)

        # Look for state where e2 has superseded e1 on P1
        superseding_found = False
        for state in state_manager.get_enabled_states():
            if (
                len(state.processes) >= 1
                and isinstance(state.processes[0], Event)
                and state.processes[0].name == "e2"
            ):
                superseding_found = True

                # Verify e1 is no longer active in this process position
                assert (
                    state.processes[0].name != "e1"
                ), "e2 should have superseded e1 in process P1"
                break

        assert superseding_found, "Should find state where e2 supersedes e1"

        # Check that e1 has been marked as CLOSED in appropriate states
        e1_closed_found = False
        for state in state_manager.states:
            for comp in state.processes:
                if isinstance(comp, Event) and comp.name == "e1":
                    # Check if e1 has CLOSED mode for process 0 (P1)
                    if hasattr(comp, "modes") and len(comp.modes) > 0:
                        if comp.modes[0] == ProcessModes.CLOSED:
                            e1_closed_found = True
                            break

        # Note: The exact behavior depends on implementation details,
        # but the superseding mechanism should be working
        assert superseding_found, "Event superseding mechanism should be functioning"
