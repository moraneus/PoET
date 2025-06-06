# tests/integration_tests/test_poet_scenario.py
# This file is part of PoET - A PCTL Runtime Verification Tool
#
# Integration test scenarios for PCTL runtime verification using partial order executions.
# Tests various PCTL operators (EP, AH, EY, ES, etc.) across different distributed system scenarios.

import pytest
from typing import List, Dict, Tuple, Any

from model.event import Event
from model.state import State
from model.process import Process
from model.process_modes import ProcessModes
from parser.parser import parse
from parser.ast import Formula, Proposition, Not, EP, AP, EH, AH


def initialize_states_and_subformulas(
    num_processes: int, formula_obj: Formula
) -> List[State]:
    """Initialize the monitoring state with subformulas and create initial state."""
    all_subformulas = Formula.collect_formulas(formula_obj)
    State._State__SUBFORMULAS = all_subformulas if all_subformulas else []
    State._State__COUNTER = 0
    s0 = State(i_processes=[ProcessModes.IOTA] * num_processes)
    s0_verdict = formula_obj.eval(state=s0)
    s0.value = s0_verdict
    return [s0]


def initialize_processes(num_processes: int) -> Dict[str, Process]:
    """Create process mapping for the distributed system."""
    return {f"P{i + 1}": Process(f"P{i + 1}") for i in range(num_processes)}


def get_involved_indices(event: Event, num_system_processes: int) -> List[int]:
    """Get indices of processes involved in the event."""
    indices = []
    for i, proc_designator in enumerate(event.processes):
        if isinstance(proc_designator, str) and proc_designator.startswith("P"):
            indices.append(i)
    return indices


def is_event_in_order(
    event_vc: List[int],
    expected_vc: List[int],
    involved_indices: List[int],
    num_processes: int,
) -> bool:
    """Check if event can be processed based on vector clock ordering."""
    if not involved_indices:
        return all(c == 0 for c in event_vc)

    for i in involved_indices:
        if not (i < len(event_vc) and i < len(expected_vc)):
            print(
                f"Warning: Index {i} out of bounds for VC check. EventVC: {event_vc}, ExpectedVC: {expected_vc}"
            )
            return False
        if event_vc[i] != expected_vc[i] + 1:
            return False
    return True


def find_new_states(
    current_enabled_states: List[State], event: Event, processes_map: Dict[str, Process]
) -> Tuple[List[State], set]:
    """Find new states created by applying event to current enabled states."""
    newly_created_states = []
    all_closed_events_info = set()

    for state_obj in current_enabled_states:
        original_processes = [p for p in state_obj.processes]
        new_state_candidate, closed_event_info_set = state_obj | event

        # Restore original state to avoid side effects
        state_obj._m_processes = original_processes

        if new_state_candidate is not None:
            # Check for duplicates
            is_duplicate = False
            for existing_state in newly_created_states:
                if existing_state.processes == new_state_candidate.processes:
                    is_duplicate = True
                    State._State__COUNTER -= 1
                    break

            if not is_duplicate:
                newly_created_states.append(new_state_candidate)
                if closed_event_info_set:
                    all_closed_events_info.update(closed_event_info_set)

    return newly_created_states, all_closed_events_info


def evaluate_states(states_to_eval: List[State], formula: Formula):
    """Evaluate formula on all enabled states."""
    for state_obj in states_to_eval:
        if state_obj.enabled:
            result = formula.eval(state=state_obj)
            state_obj.value = result


def add_event_to_processes(event: Event, processes_map: Dict[str, Process]):
    """Add event to relevant processes."""
    for i, proc_designator in enumerate(event.processes):
        if isinstance(proc_designator, str) and proc_designator.startswith("P"):
            if proc_designator in processes_map:
                processes_map[proc_designator].add_event(event)


def update_closed_events(closed_event_details: set):
    """Update mode for closed events."""
    for finished_event_obj, process_idx in filter(None, closed_event_details):
        if isinstance(finished_event_obj, Event):
            finished_event_obj.update_mode(ProcessModes.CLOSED, process_idx)


def complete_state_edges(
    enabled_states: List[State],
    newly_created_states: List[State],
    processes_map: Dict[str, Process],
):
    """Complete edges between old and new states."""
    for old_state in enabled_states:
        old_state.edges_completion(newly_created_states, processes_map)

    for i, new_state in enumerate(newly_created_states):
        new_state.edges_completion(newly_created_states[i + 1 :], processes_map)


def disable_fully_closed_states(all_states: List[State], num_processes: int):
    """Disable states where all processes are closed."""
    for state_obj in all_states:
        if (
            state_obj.enabled
            and state_obj.processes
            and len(state_obj.processes) == num_processes
        ):
            all_closed = all(
                State.is_proc_closed(state_obj.processes[i], i)
                for i in range(num_processes)
            )
            if all_closed:
                state_obj.enabled = False


def process_event(
    event: Event,
    all_states: List[State],
    formula: Formula,
    processes_map: Dict[str, Process],
    num_processes: int,
) -> List[State]:
    """Process a single event and update the state space."""
    add_event_to_processes(event, processes_map)

    enabled_states = [s for s in all_states if s.enabled]
    newly_created_states, closed_event_details = find_new_states(
        enabled_states, event, processes_map
    )

    update_closed_events(closed_event_details)
    complete_state_edges(enabled_states, newly_created_states, processes_map)

    evaluate_states(newly_created_states, formula)
    all_states.extend(newly_created_states)

    disable_fully_closed_states(all_states, num_processes)
    return newly_created_states


def flush_single_pass(
    holding_queue: List[Event],
    expected_vc: List[int],
    all_states: List[State],
    formula: Formula,
    processes_map: Dict[str, Process],
    num_processes: int,
    processed_event_names: List[str],
) -> Tuple[List[Event], bool]:
    """Process one pass of queue flushing, return flushed events and progress indicator."""
    flushed_this_pass = []
    made_progress = False

    for event in holding_queue[:]:
        involved_indices = get_involved_indices(event, num_processes)
        if is_event_in_order(
            event.vector_clock, expected_vc, involved_indices, num_processes
        ):
            print(f"    Flushing from queue: {event.name}")
            process_event(event, all_states, formula, processes_map, num_processes)
            processed_event_names.append(event.name)

            for idx in involved_indices:
                if idx < len(expected_vc) and idx < len(event.vector_clock):
                    expected_vc[idx] = event.vector_clock[idx]

            flushed_this_pass.append(event)
            made_progress = True

    return flushed_this_pass, made_progress


def flush_holding_queue(
    holding_queue: List[Event],
    expected_vc: List[int],
    all_states: List[State],
    formula: Formula,
    processes_map: Dict[str, Process],
    num_processes: int,
    processed_event_names: List[str],
) -> int:
    """Process events from holding queue that are now in order."""
    total_flushed = 0
    made_progress = True

    while made_progress:
        flushed_this_pass, made_progress = flush_single_pass(
            holding_queue,
            expected_vc,
            all_states,
            formula,
            processes_map,
            num_processes,
            processed_event_names,
        )

        for flushed_event in flushed_this_pass:
            if flushed_event in holding_queue:
                holding_queue.remove(flushed_event)

        total_flushed += len(flushed_this_pass)

    return total_flushed


class PoetScenario:
    """Test scenario for PCTL runtime verification."""

    def __init__(
        self,
        scenario_id,
        description,
        num_processes,
        pctl_spec,
        event_trace,
        expected_verdicts_after_event,
        expected_final_verdict=None,
    ):
        self.id = scenario_id
        self.description = description
        self.num_processes = num_processes
        self.spec = pctl_spec
        self.trace = event_trace
        self.expected_verdicts_after_event = expected_verdicts_after_event
        self.expected_final_verdict = expected_final_verdict


SCENARIOS = [
    PoetScenario(
        scenario_id="EP_01_SIMPLE_TRUE",
        description="Tests EP(p) where p becomes true on the first event.",
        num_processes=1,
        pctl_spec="EP(p)",
        event_trace=[("e1", ["P1"], ["p"], [1])],
        expected_verdicts_after_event=[("e1", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EP_02_SIMPLE_FALSE",
        description="Tests EP(p) where p never becomes true.",
        num_processes=1,
        pctl_spec="EP(p)",
        event_trace=[("e1", ["P1"], ["q"], [1]), ("e2", ["P1"], ["r"], [2])],
        expected_verdicts_after_event=[("e1", False), ("e2", False)],
        expected_final_verdict=False,
    ),
    PoetScenario(
        scenario_id="EP_03_TRUE_LATER",
        description="Tests EP(p) where p becomes true after a few non-p events.",
        num_processes=2,
        pctl_spec="EP(p)",
        event_trace=[
            ("e1", ["P1"], ["q"], [1, 0]),
            ("e2", ["P2"], ["r"], [1, 1]),
            ("e3", ["P1"], ["s"], [2, 1]),
            ("e4", ["P2"], ["p"], [2, 2]),
        ],
        expected_verdicts_after_event=[
            ("e1", False),
            ("e2", False),
            ("e3", False),
            ("e4", True),
        ],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="AH_01_SIMPLE_TRUE",
        description="Tests AH(p) where p always holds according to trace.",
        num_processes=1,
        pctl_spec="AH(p)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["p"], [2])],
        expected_verdicts_after_event=[("e1", False), ("e2", False)],
        expected_final_verdict=False,
    ),
    PoetScenario(
        scenario_id="AH_02_BECOMES_FALSE",
        description="Tests AH(p) where p holds then stops holding.",
        num_processes=1,
        pctl_spec="AH(p)",
        event_trace=[
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["q"], [2]),
            ("e3", ["P1"], ["p"], [3]),
        ],
        expected_verdicts_after_event=[("e1", False), ("e2", False), ("e3", False)],
        expected_final_verdict=False,
    ),
    PoetScenario(
        scenario_id="EY_01_SIMPLE_TRUE",
        description="Tests EY(p) where p was true in the immediate predecessor.",
        num_processes=1,
        pctl_spec="EY(p)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["q"], [2])],
        expected_verdicts_after_event=[("e1", False), ("e2", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="ES_01_BASIC",
        description="Tests E(p S q) where p holds, then q becomes true.",
        num_processes=1,
        pctl_spec="E(p S q)",
        event_trace=[
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["p"], [2]),
            ("e3", ["P1"], ["q"], [3]),
        ],
        expected_verdicts_after_event=[("e1", False), ("e2", False), ("e3", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EP_04_CONCURRENT_RACE",
        description="EP(p). Two concurrent events. Test specific processing order.",
        num_processes=2,
        pctl_spec="EP(p)",
        event_trace=[("e_q", ["P2"], ["q"], [0, 1]), ("e_p", ["P1"], ["p"], [1, 0])],
        expected_verdicts_after_event=[("e_q", False), ("e_p", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="AH_03_TAUTOLOGY",
        description="Tests AH(p | !p), which should always be true.",
        num_processes=1,
        pctl_spec="AH(p | !p)",
        event_trace=[
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["q"], [2]),
            ("e3", ["P1"], [], [3]),
        ],
        expected_verdicts_after_event=[("e1", True), ("e2", True), ("e3", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="NESTED_COMPLEX_01",
        description="Tests AH(EP(p) -> EY(q)).",
        num_processes=2,
        pctl_spec="AH(EP(p) -> EY(q))",
        event_trace=[
            ("e_q1", ["P1"], ["q"], [1, 0]),
            ("e_p1", ["P2"], ["p"], [0, 1]),
            ("e_r", ["P1"], ["r"], [2, 0]),
            ("e_q2", ["P2"], ["q"], [0, 2]),
        ],
        expected_verdicts_after_event=[
            ("e_q1", True),
            ("e_p1", False),
            ("e_r", False),
            ("e_q2", False),
        ],
        expected_final_verdict=False,
    ),
    PoetScenario(
        scenario_id="AP_01_LIKE_AH",
        description="Tests AP(p).",
        num_processes=1,
        pctl_spec="AP(p)",
        event_trace=[
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["p"], [2]),
            ("e3", ["P1"], ["p"], [3]),
        ],
        expected_verdicts_after_event=[("e1", True), ("e2", True), ("e3", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="AP_02_BECOMES_FALSE_POET_AP",
        description="Tests AP(p) where p stops holding.",
        num_processes=1,
        pctl_spec="AP(p)",
        event_trace=[
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["q"], [2]),
            ("e3", ["P1"], ["p"], [3]),
        ],
        expected_verdicts_after_event=[("e1", True), ("e2", False), ("e3", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EH_01_BASIC_TRUE",
        description="Tests EH(p) where p holds now.",
        num_processes=1,
        pctl_spec="EH(p)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["p"], [2])],
        expected_verdicts_after_event=[("e1", True), ("e2", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EH_02_BECOMES_FALSE",
        description="Tests EH(p) where p stops holding.",
        num_processes=1,
        pctl_spec="EH(p)",
        event_trace=[
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["q"], [2]),
            ("e3", ["P1"], ["p"], [3]),
        ],
        expected_verdicts_after_event=[("e1", True), ("e2", False), ("e3", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="AS_01_SIMPLE_SUCCESS",
        description="Tests A(p S q) where p holds until q becomes true.",
        num_processes=1,
        pctl_spec="A(p S q)",
        event_trace=[
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["p"], [2]),
            ("e3", ["P1"], ["q"], [3]),
        ],
        expected_verdicts_after_event=[("e1", False), ("e2", False), ("e3", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="AS_02_P_FAILS_POET_SEMANTICS",
        description="Tests A(p S q) where p stops holding.",
        num_processes=1,
        pctl_spec="A(p S q)",
        event_trace=[
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["r"], [2]),
            ("e3", ["P1"], ["q"], [3]),
        ],
        expected_verdicts_after_event=[("e1", False), ("e2", False), ("e3", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="AY_01_MULTI_PRED_TRUE",
        description="AY(p). Harness linear: S0->S_p1->S_p1p2 (e_p2 from Q)->S_merge.",
        num_processes=2,
        pctl_spec="AY(p)",
        event_trace=[
            ("e_p1", ["P1"], ["p"], [1, 0]),
            ("e_p2", ["P2"], ["p"], [0, 1]),
            ("e_merge", ["P1", "P2"], ["m"], [2, 2]),
        ],
        expected_verdicts_after_event=[
            ("e_p1", False),
            ("e_p2", False),
            ("e_merge", False),
        ],
        expected_final_verdict=False,
    ),
    PoetScenario(
        scenario_id="AY_02_MULTI_PRED_FAIL",
        description="AY(p) where p holds in one but not all. Harness linear.",
        num_processes=2,
        pctl_spec="AY(p)",
        event_trace=[
            ("e_p1", ["P1"], ["p"], [1, 0]),
            ("e_q1", ["P2"], ["q"], [0, 1]),
            ("e_merge", ["P1", "P2"], ["m"], [2, 2]),
        ],
        expected_verdicts_after_event=[
            ("e_p1", False),
            ("e_q1", False),
            ("e_merge", False),
        ],
        expected_final_verdict=False,
    ),
    PoetScenario(
        scenario_id="AH_COMPLEX_IMPLICATION",
        description="Tests AH(!p | EY(q)).",
        num_processes=1,
        pctl_spec="AH(!p | EY(q))",
        event_trace=[
            ("e_q1", ["P1"], ["q"], [1]),
            ("e_p1", ["P1"], ["p"], [2]),
            ("e_r1", ["P1"], ["r"], [3]),
            ("e_p2", ["P1"], ["p"], [4]),
        ],
        expected_verdicts_after_event=[
            ("e_q1", True),
            ("e_p1", True),
            ("e_r1", True),
            ("e_p2", False),
        ],
        expected_final_verdict=False,
    ),
    PoetScenario(
        scenario_id="AS_EQUIV_AP_POET",
        description="Tests A(TRUE S p).",
        num_processes=1,
        pctl_spec="A(TRUE S p)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["q"], [2])],
        expected_verdicts_after_event=[("e1", True), ("e2", False)],
        expected_final_verdict=False,
    ),
    PoetScenario(
        scenario_id="INITIAL_EXAMPLE_EP_EP_A_AND_NOT_EP_D",
        description="Original example: EP(EP(a) & !EP(d)). Harness with edges_completion.",
        num_processes=2,
        pctl_spec="EP(EP(a) & !EP(d))",
        event_trace=[("int4", ["P2"], ["d"], [0, 1]), ("int5", ["P1"], ["a"], [1, 0])],
        expected_verdicts_after_event=[("int4", False), ("int5", True)],
        expected_final_verdict=True,
    ),
]


def create_event_from_trace_data(event_data: Tuple, scenario: PoetScenario) -> Event:
    """Create Event object from trace data tuple."""
    event_name, active_processes, props, vector_clock = event_data

    # Build event constructor parameters
    event_processes = ["-"] * scenario.num_processes
    for proc_id in active_processes:
        try:
            idx = int(proc_id[1:]) - 1
            if 0 <= idx < scenario.num_processes:
                event_processes[idx] = proc_id
        except (ValueError, IndexError):
            pytest.fail(
                f"Scenario {scenario.id}, Event {event_name}: Invalid process ID {proc_id}"
            )

    return Event(
        i_name=event_name,
        i_processes=event_processes,
        i_propositions=props,
        vector_clock=vector_clock,
    )


def get_verdict_state(all_states: List[State], s0: State) -> Tuple[Any, str]:
    """Get the state to check for verdict and its name."""
    candidate_states = [s for s in all_states if s.enabled and s.name != "S0"]

    if candidate_states:
        newest_state = sorted(candidate_states, key=lambda s: int(s.name[1:]))[-1]
        return newest_state.value, newest_state.name
    elif s0:
        return s0.value, s0.name
    else:
        return "ERROR_NO_STATE_FOR_VERDICT_CHECK", "None"


def check_event_verdicts(
    processed_events: List[str],
    expected_verdicts_map: Dict[str, bool],
    all_states: List[State],
    s0: State,
    scenario_id: str,
    is_final: bool = False,
):
    """Check verdicts for processed events against expected values."""
    for event_name in processed_events:
        if event_name in expected_verdicts_map:
            actual_verdict, state_name = get_verdict_state(all_states, s0)
            expected_verdict = expected_verdicts_map[event_name]

            context = "final" if is_final else "regular"
            assert (
                actual_verdict == expected_verdict
            ), f"Scenario {scenario_id}, Event {event_name} ({context}, state {state_name}): Expected {expected_verdict}, Got {actual_verdict}"


def process_single_event(
    event_data: Tuple,
    scenario: PoetScenario,
    all_states: List[State],
    formula: Formula,
    processes_map: Dict[str, Process],
    expected_vc: List[int],
    holding_queue: List[Event],
) -> List[str]:
    """Process a single event from the trace."""
    event = create_event_from_trace_data(event_data, scenario)
    print(f"\nProcessing event: {event.name} (VC: {event.vector_clock})")

    processed_events = []
    involved_indices = get_involved_indices(event, scenario.num_processes)

    if is_event_in_order(
        event.vector_clock, expected_vc, involved_indices, scenario.num_processes
    ):
        print(f"  Event {event.name} is IN ORDER. Current Expected VC: {expected_vc}")
        processed_events.append(event.name)
        process_event(event, all_states, formula, processes_map, scenario.num_processes)

        # Update expected vector clock
        for i in involved_indices:
            if i < len(expected_vc) and i < len(event.vector_clock):
                expected_vc[i] = event.vector_clock[i]
        print(f"    Updated Expected VC: {expected_vc}")

        # Flush holding queue
        flushed_count = flush_holding_queue(
            holding_queue,
            expected_vc,
            all_states,
            formula,
            processes_map,
            scenario.num_processes,
            processed_events,
        )
        print(
            f"    Flushed {flushed_count} events from queue. Events processed: {processed_events}"
        )
    else:
        print(
            f"  Event {event.name} is OUT OF ORDER. Expected VC: {expected_vc}. Adding to queue."
        )
        holding_queue.append(event)
        print(f"    Holding queue: {[e.name for e in holding_queue]}")

    return processed_events


def get_final_verdict_state(all_states: List[State], s0: State) -> Tuple[Any, str]:
    """Get the appropriate state for final verdict checking."""
    maximal_states = [
        s for s in all_states if s.enabled and not s.successors and s.name != "S0"
    ]

    if not maximal_states:
        if s0.enabled and not s0.successors and len(all_states) == 1:
            maximal_states = [s0]
        else:
            enabled_non_s0 = [s for s in all_states if s.enabled and s.name != "S0"]
            if enabled_non_s0:
                maximal_states = [
                    sorted(enabled_non_s0, key=lambda s: int(s.name[1:]))[-1]
                ]
            elif s0 and s0.enabled:
                maximal_states = [s0]
            elif all_states:
                maximal_states = [sorted(all_states, key=lambda s: int(s.name[1:]))[-1]]

    if maximal_states:
        final_state = sorted(maximal_states, key=lambda s: int(s.name[1:]))[-1]
        return final_state.value, final_state.name
    else:
        return "UNDETERMINED", "None"


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.id for s in SCENARIOS])
def test_poet_scenario(scenario: PoetScenario):
    """Test PCTL runtime verification for given scenario."""
    print(f"\n--- Running Scenario: {scenario.id} - {scenario.description} ---")
    print(f"Specification: {scenario.spec}")
    print(f"Trace: {scenario.trace}")

    # Reset global counters
    State._State__COUNTER = 0
    Event._Event__TIMELINE = 0

    # Parse specification
    formula = parse(scenario.spec)
    if formula is None:
        pytest.fail(
            f"Scenario {scenario.id}: Failed to parse PCTL specification: {scenario.spec}"
        )

    # Initialize system
    all_states = initialize_states_and_subformulas(scenario.num_processes, formula)
    s0 = all_states[0]
    processes_map = initialize_processes(scenario.num_processes)
    expected_vc = [0] * scenario.num_processes
    holding_queue = []
    expected_verdicts_map = {
        event_name: verdict
        for event_name, verdict in scenario.expected_verdicts_after_event
    }

    # Process event trace
    for event_data in scenario.trace:
        processed_events = process_single_event(
            event_data,
            scenario,
            all_states,
            formula,
            processes_map,
            expected_vc,
            holding_queue,
        )
        check_event_verdicts(
            processed_events, expected_verdicts_map, all_states, s0, scenario.id
        )

    # Final queue flush
    print("\nPerforming final queue flush.")
    final_processed = []
    flush_holding_queue(
        holding_queue,
        expected_vc,
        all_states,
        formula,
        processes_map,
        scenario.num_processes,
        final_processed,
    )

    check_event_verdicts(
        final_processed,
        expected_verdicts_map,
        all_states,
        s0,
        scenario.id,
        is_final=True,
    )
    check_final_scenario_verdict(scenario, all_states, s0)


def check_final_scenario_verdict(
    scenario: PoetScenario, all_states: List[State], s0: State
):
    """Check the final verdict for the entire scenario."""
    if scenario.expected_final_verdict is None:
        return

    final_verdict, final_state_name = get_final_verdict_state(all_states, s0)

    print(f"--- Final Verdict for Scenario: {scenario.id} ---")
    print(
        f"  State: {final_state_name}, Actual: {final_verdict}, Expected: {scenario.expected_final_verdict}"
    )

    assert final_verdict == scenario.expected_final_verdict, (
        f"Scenario {scenario.id}: Final verdict expected {scenario.expected_final_verdict}, "
        f"got {final_verdict} (state {final_state_name})"
    )
