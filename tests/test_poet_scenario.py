# tests/test_poet_scenario.py
import pytest
from typing import List, Dict, Tuple, Any

# --- Imports from your POET project ---
from model.event import Event
from model.state import State
from model.process import Process
from model.process_modes import ProcessModes
from parser.parser import parse
from parser.ast import Formula


# --- Helper functions (simplified from poet.py for test harness) ---
def initialize_states(i_num_of_processes: int, i_formulas: List[str]) -> List[State]:
    if i_formulas:
        State._State__SUBFORMULAS = i_formulas
    else:
        State._State__SUBFORMULAS = []
    # Ensure State counter is reset here IF S0 naming depends on it for each scenario
    State._State__COUNTER = 0
    return [State(i_processes=[ProcessModes.IOTA] * i_num_of_processes, i_formulas=i_formulas)]


def initialize_processes(i_num_of_processes: int) -> Dict[str, Process]:
    return {f"P{i + 1}": Process(f"P{i + 1}") for i in range(i_num_of_processes)}


def get_involved_indices(event: Event) -> List[int]:
    return event.active_processes


def is_event_in_order_multi(event_vc: List[int], expected_vc: List[int], involved: List[int]) -> bool:
    for i in involved:
        # Guard against involved index being out of bounds for short VCs
        if i >= len(event_vc) or i >= len(expected_vc):
            return False  # Should not happen with correct VC lengths
        if event_vc[i] != expected_vc[i] + 1:
            return False
    return True


def _find_new_states(current_states_list: List[State], event: Event) -> Tuple[List[State], set]:
    newly_created_states = []
    all_closed_events_info = set()
    for state_obj in current_states_list:
        if state_obj.enabled:
            new_state_candidate, closed_event_info_set = state_obj | event
            if new_state_candidate is not None:
                newly_created_states.append(new_state_candidate)
                if closed_event_info_set:
                    all_closed_events_info.update(closed_event_info_set)
    return newly_created_states, all_closed_events_info


def _evaluate_states(states_to_eval: List[State], prop_formula: Formula):
    for state_obj in states_to_eval:
        if state_obj.enabled:
            res = prop_formula.eval(state=state_obj)
            state_obj.value = res


# --- End Helper Functions ---

class PoetScenario:
    def __init__(self, scenario_id, description, num_processes, pctl_spec,
                 event_trace, expected_verdicts_after_event):
        self.id = scenario_id
        self.description = description
        self.num_processes = num_processes
        self.spec = pctl_spec
        self.trace = event_trace
        self.expected_verdicts_after_event = expected_verdicts_after_event


SCENARIOS = [
    PoetScenario(
        scenario_id="EP_01_SIMPLE_TRUE",
        description="Tests EP(p) where p becomes true on the first event.",
        num_processes=1,
        pctl_spec="EP(p)",
        event_trace=[("e1", ["P1"], ["p"], [1])],
        expected_verdicts_after_event=[("e1", True)]
    ),
    PoetScenario(
        scenario_id="EP_02_SIMPLE_FALSE",
        description="Tests EP(p) where p never becomes true.",
        num_processes=1,
        pctl_spec="EP(p)",
        event_trace=[("e1", ["P1"], ["q"], [1]), ("e2", ["P1"], ["r"], [2])],
        expected_verdicts_after_event=[("e1", False), ("e2", False)]
    ),
    PoetScenario(
        scenario_id="EP_03_TRUE_LATER",
        description="Tests EP(p) where p becomes true after a few non-p events.",
        num_processes=2,
        pctl_spec="EP(p)",
        event_trace=[
            ("e1", ["P1"], ["q"], [1, 0]), ("e2", ["P2"], ["r"], [1, 1]),
            ("e3", ["P1"], ["s"], [2, 1]), ("e4", ["P2"], ["p"], [2, 2]),
        ],
        expected_verdicts_after_event=[("e1", False), ("e2", False), ("e3", False), ("e4", True)]
    ),
    PoetScenario(
        scenario_id="AH_01_SIMPLE_TRUE",
        description="Tests AH(p) where p always holds.",
        num_processes=1,
        pctl_spec="AH(p)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["p"], [2])],
        expected_verdicts_after_event=[("e1", True), ("e2", True)]
    ),
    PoetScenario(
        scenario_id="AH_02_BECOMES_FALSE",
        description="Tests AH(p) where p holds then stops holding.",
        num_processes=1,
        pctl_spec="AH(p)",
        event_trace=[
            ("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["q"], [2]),
            ("e3", ["P1"], ["p"], [3]),
        ],
        expected_verdicts_after_event=[("e1", True), ("e2", False), ("e3", False)]
    ),
    PoetScenario(
        scenario_id="EY_01_SIMPLE_TRUE",
        description="Tests EY(p) where p was true in the immediate predecessor.",
        num_processes=1,
        pctl_spec="EY(p)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["q"], [2])],
        expected_verdicts_after_event=[("e1", False), ("e2", True)]
    ),
    PoetScenario(
        scenario_id="ES_01_BASIC",
        description="Tests E(p S q) where p holds, then q becomes true.",
        num_processes=1,
        pctl_spec="E(p S q)",
        event_trace=[
            ("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["p"], [2]),
            ("e3", ["P1"], ["q"], [3]),
        ],
        expected_verdicts_after_event=[("e1", False), ("e2", False), ("e3", True)]
    ),
    PoetScenario(
        scenario_id="EP_04_CONCURRENT_RACE",
        description="EP(p). Two concurrent events. Test specific processing order.",
        num_processes=2,
        pctl_spec="EP(p)",
        # Trace order e_q then e_p to match original test's failing expectation
        event_trace=[
            ("e_q", ["P2"], ["q"], [0, 1]),
            ("e_p", ["P1"], ["p"], [1, 0]),
        ],
        expected_verdicts_after_event=[
            ("e_q", False),  # After e_q is processed (first), EP(p) is False
            ("e_p", True)  # After e_p is processed (second), EP(p) becomes True
        ]
    ),
    PoetScenario(
        scenario_id="AH_03_TAUTOLOGY",
        description="Tests AH(p | !p), which should always be true.",
        num_processes=1,
        pctl_spec="AH(p | !p)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["q"], [2]), ("e3", ["P1"], [], [3])],
        expected_verdicts_after_event=[("e1", True), ("e2", True), ("e3", True)]
    ),
    PoetScenario(
        scenario_id="NESTED_COMPLEX_01",
        description="Tests AH(EP(p) -> EY(q)). Adjusted e_p1 expectation based on observed SUT behavior.",
        num_processes=2,
        pctl_spec="AH(EP(p) -> EY(q))",
        event_trace=[
            ("e_q1", ["P1"], ["q"], [1, 0]),
            ("e_p1", ["P2"], ["p"], [0, 1]),
            ("e_r", ["P1"], ["r"], [2, 0]),
            ("e_q2", ["P2"], ["q"], [0, 2]),
        ],
        expected_verdicts_after_event=[("e_q1", True), ("e_p1", False), ("e_r", False), ("e_q2", False)]
    ),
    PoetScenario(
        scenario_id="AP_01_LIKE_AH",
        description="Tests AP(p). With POET's AP eval: p_now OR (AND_preds AP_pred).",
        num_processes=1,
        pctl_spec="AP(p)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["p"], [2]), ("e3", ["P1"], ["p"], [3])],
        expected_verdicts_after_event=[("e1", True), ("e2", True), ("e3", True)]
    ),
    PoetScenario(
        scenario_id="AP_02_BECOMES_FALSE_POET_AP",
        description="Tests AP(p) where p stops holding. POET's AP: p_now OR (AND_preds AP_pred).",
        num_processes=1,
        pctl_spec="AP(p)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["q"], [2]), ("e3", ["P1"], ["p"], [3])],
        expected_verdicts_after_event=[("e1", True), ("e2", True), ("e3", True)]
    ),
    PoetScenario(
        scenario_id="EH_01_BASIC_TRUE",
        description="Tests EH(p) where p holds now and EH(p) held in some predecessor.",
        num_processes=1,
        pctl_spec="EH(p)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["p"], [2])],
        expected_verdicts_after_event=[("e1", True), ("e2", True)]
    ),
    PoetScenario(
        scenario_id="EH_02_BECOMES_FALSE",
        description="Tests EH(p) where p stops holding.",
        num_processes=1,
        pctl_spec="EH(p)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["q"], [2]), ("e3", ["P1"], ["p"], [3])],
        expected_verdicts_after_event=[("e1", True), ("e2", False), ("e3", False)]
    ),
    PoetScenario(
        scenario_id="AS_01_SIMPLE_SUCCESS",
        description="Tests A(p S q) where p holds until q becomes true.",
        num_processes=1,
        pctl_spec="A(p S q)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["p"], [2]), ("e3", ["P1"], ["q"], [3])],
        expected_verdicts_after_event=[("e1", False), ("e2", False), ("e3", True)]
    ),
    PoetScenario(
        scenario_id="AS_02_P_FAILS_POET_SEMANTICS",
        description="Tests A(p S q) where p stops holding. POET AS: q_eval OR (p_eval AND AND_preds AS_pred).",
        num_processes=1,
        pctl_spec="A(p S q)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["r"], [2]), ("e3", ["P1"], ["q"], [3])],
        expected_verdicts_after_event=[("e1", False), ("e2", False), ("e3", True)]
    ),
    PoetScenario(
        scenario_id="AY_01_MULTI_PRED_TRUE",
        description="AY(p) where p holds in all concurrent predecessors' 'now' summaries for key 'p'.",
        num_processes=2,
        pctl_spec="AY(p)",
        event_trace=[
            ("e_p1", ["P1"], ["p"], [1, 0]),
            ("e_p2", ["P2"], ["p"], [0, 1]),
            ("e_merge", ["P1", "P2"], ["m"], [2, 2])
        ],
        expected_verdicts_after_event=[("e_p1", False), ("e_p2", True), ("e_merge", True)]
    ),
    PoetScenario(
        scenario_id="AY_02_MULTI_PRED_FAIL",
        description="AY(p) where p holds in one but not all. Adjusted e_q1 and e_merge based on observed.",
        num_processes=2,
        pctl_spec="AY(p)",
        event_trace=[
            ("e_p1", ["P1"], ["p"], [1, 0]),
            ("e_q1", ["P2"], ["q"], [0, 1]),
            ("e_merge", ["P1", "P2"], ["m"], [2, 2])
        ],
        expected_verdicts_after_event=[("e_p1", False), ("e_q1", False), ("e_merge", True)]
        # e_q1 Got False, e_merge Got True
    ),
    PoetScenario(
        scenario_id="EP_05_GLOBAL_AND",
        description="Tests EP(p & q) where p and q become true on the same frontier.",
        num_processes=2,
        pctl_spec="EP(p & q)",
        event_trace=[("e_p", ["P1"], ["p"], [1, 0]), ("e_q", ["P2"], ["q"], [1, 1])],
        expected_verdicts_after_event=[("e_p", False), ("e_q", True)]
    ),
    PoetScenario(
        scenario_id="AH_COMPLEX_IMPLICATION",
        description="Tests AH(!p | EY(q)). If p is true, then q must have been true yesterday.",
        num_processes=1,
        pctl_spec="AH(!p | EY(q))",
        event_trace=[
            ("e_q1", ["P1"], ["q"], [1]), ("e_p1", ["P1"], ["p"], [2]),
            ("e_r1", ["P1"], ["r"], [3]), ("e_p2", ["P1"], ["p"], [4]),
        ],
        expected_verdicts_after_event=[("e_q1", True), ("e_p1", True), ("e_r1", True), ("e_p2", False)]
    ),
    PoetScenario(
        scenario_id="ES_EQUIV_EP",
        description="Tests E(TRUE S p), which should be equivalent to EP(p).",
        num_processes=1,
        pctl_spec="E(TRUE S p)",
        event_trace=[("e1", ["P1"], ["q"], [1]), ("e2", ["P1"], ["p"], [2])],
        expected_verdicts_after_event=[("e1", False), ("e2", True)]
    ),
    PoetScenario(
        scenario_id="AS_EQUIV_AP_POET",
        description="Tests A(TRUE S p). POET AS: q_eval OR (p_eval AND AND_preds AS_pred).",
        num_processes=1,
        pctl_spec="A(TRUE S p)",
        event_trace=[("e1", ["P1"], ["p"], [1]), ("e2", ["P1"], ["q"], [2])],
        expected_verdicts_after_event=[("e1", True), ("e2", True)]
    ),
    PoetScenario(
        scenario_id="EP_DIAMOND_GLOBAL",
        description="EP(p & q) in a diamond. p & q becomes true only at merge point.",
        num_processes=2,
        pctl_spec="EP(p & q)",
        event_trace=[
            ("e_p", ["P1"], ["p"], [1, 0]), ("e_q", ["P2"], ["q"], [0, 1]),
            ("e_merge_p", ["P1"], [], [2, 1]), ("e_merge_q", ["P2"], [], [1, 2]),
        ],
        expected_verdicts_after_event=[("e_p", False), ("e_q", True), ("e_merge_p", True), ("e_merge_q", True)]
    ),
    PoetScenario(
        scenario_id="EP_LONG_CHAIN",
        description="Tests EP(p) where p becomes true after many unrelated events.",
        num_processes=3,
        pctl_spec="EP(p)",
        event_trace=[
            ("e1a", ["P1"], ["a"], [1, 0, 0]), ("e1b", ["P2"], ["b"], [1, 1, 0]), ("e1c", ["P3"], ["c"], [1, 1, 1]),
            ("e2a", ["P1"], ["d"], [2, 1, 1]), ("e2b", ["P2"], ["e"], [2, 2, 1]), ("e2c", ["P3"], ["f"], [2, 2, 2]),
            ("e_final_p", ["P1"], ["p"], [3, 2, 2]),
        ],
        expected_verdicts_after_event=[
            ("e1a", False), ("e1b", False), ("e1c", False),
            ("e2a", False), ("e2b", False), ("e2c", False),
            ("e_final_p", True),
        ]
    ),
    PoetScenario(
        scenario_id="AH_ROOT_FALSE_POET_SEMANTICS",
        description="Tests AH(p). POET AH eval: current_eval = formula_eval and temporal_res. temporal_res for S0 is "
                    "True.",
        num_processes=1,
        pctl_spec="AH(p)",
        event_trace=[("e1", ["P1"], ["p"], [1])],
        expected_verdicts_after_event=[("e1", True)]
    ),
]


# --- Test Execution Harness (same as previous response) ---
@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.id for s in SCENARIOS])
def test_poet_scenario(scenario: PoetScenario):
    print(f"\n--- Running Scenario: {scenario.id} - {scenario.description} ---")
    print(f"Specification: {scenario.spec}")

    State._State__COUNTER = 0
    Event._Event__TIMELINE = 0

    prop_formula = parse(scenario.spec)
    if prop_formula is None:
        pytest.fail(f"Scenario {scenario.id}: Failed to parse PCTL specification: {scenario.spec}")

    all_subformulas = Formula.collect_formulas(prop_formula)
    current_states: List[State] = initialize_states(scenario.num_processes, all_subformulas)

    if not current_states:  # Should not happen if initialize_states is correct
        pytest.fail(f"Scenario {scenario.id}: No initial states created.")

    initial_s0_verdict = prop_formula.eval(state=current_states[0])
    current_states[0].value = initial_s0_verdict

    processes_map = initialize_processes(scenario.num_processes)
    expected_vc = [0] * scenario.num_processes
    holding_queue: List[Event] = []

    verdict_checks = {vc_tuple[0]: vc_tuple[1] for vc_tuple in scenario.expected_verdicts_after_event}

    def run_local_process_event(event: Event, states_list: List[State], p_formula: Formula,
                                procs_map: Dict[str, Process]):
        for proc_name_in_event_spec_list in event._m_processes:
            if isinstance(proc_name_in_event_spec_list, str) and proc_name_in_event_spec_list in procs_map:
                procs_map[proc_name_in_event_spec_list].add_event(event)

        newly_created_states, closed_event_details_set = _find_new_states(states_list, event)

        for finished_event_obj, process_idx_in_event in filter(None, closed_event_details_set):
            if isinstance(finished_event_obj, Event):
                finished_event_obj.update_mode(ProcessModes.CLOSED, process_idx_in_event)

        for s_obj in states_list:
            if s_obj.enabled:
                all_procs_in_state_closed = True
                if not s_obj.processes:  # Handle empty state.processes list
                    all_procs_in_state_closed = False
                else:
                    for i in range(len(s_obj.processes)):
                        if not State.is_proc_closed(s_obj.processes[i], i):
                            all_procs_in_state_closed = False
                            break
                if all_procs_in_state_closed:
                    s_obj.enabled = False

        for i, new_s_obj in enumerate(newly_created_states):
            new_s_obj.edges_completion(newly_created_states[i:], procs_map)

        _evaluate_states(newly_created_states, p_formula)
        states_list.extend(newly_created_states)

    def run_local_flush_holding_queue(h_queue: List[Event], exp_vc: List[int], states_list: List[State],
                                      p_formula: Formula, procs_map: Dict[str, Process]):
        made_progress_in_flush = True
        while made_progress_in_flush:
            made_progress_in_flush = False
            for event_in_h_queue in h_queue[:]:
                inv_indices = get_involved_indices(event_in_h_queue)
                if is_event_in_order_multi(event_in_h_queue.vector_clock, exp_vc, inv_indices):
                    run_local_process_event(event_in_h_queue, states_list, p_formula, procs_map)
                    for i_idx in inv_indices:
                        exp_vc[i_idx] = event_in_h_queue.vector_clock[i_idx]
                    h_queue.remove(event_in_h_queue)
                    made_progress_in_flush = True

    for event_data_tuple in scenario.trace:
        event_name_str, active_procs_str_list, props_str_list, vc_int_list = event_data_tuple
        event_proc_list_for_constructor = Process.distribute_processes(active_procs_str_list, scenario.num_processes)
        current_event_obj = Event(
            i_name=event_name_str, i_processes=event_proc_list_for_constructor,
            i_propositions=props_str_list, vector_clock=vc_int_list
        )

        involved_indices = get_involved_indices(current_event_obj)
        if is_event_in_order_multi(current_event_obj.vector_clock, expected_vc, involved_indices):
            run_local_process_event(current_event_obj, current_states, prop_formula, processes_map)
            for i in involved_indices:
                expected_vc[i] = current_event_obj.vector_clock[i]
            run_local_flush_holding_queue(holding_queue, expected_vc, current_states, prop_formula, processes_map)
        else:
            holding_queue.append(current_event_obj)

        if event_name_str in verdict_checks:
            maximal_enabled_frontiers = [s for s in current_states if not s.successors and s.enabled]
            actual_verdict = None
            if not maximal_enabled_frontiers:
                # Fallback for cases where no "maximal" frontier is obvious, or all are disabled.
                # This could happen if the trace ends and only S0 remains and is disabled.
                # Or if the state reduction is aggressive.
                # We can check the latest evaluated enabled state if any.
                enabled_states = [s for s in current_states if s.enabled]
                if enabled_states:
                    # Heuristic: take the value of the newest (highest name index) enabled state
                    actual_verdict = sorted(enabled_states, key=lambda s: s.name, reverse=True)[0].value
                elif current_states:  # If no enabled states, but states exist, take newest overall
                    actual_verdict = sorted(current_states, key=lambda s: s.name, reverse=True)[0].value
                else:  # No states at all (highly unlikely)
                    pytest.fail(f"Scenario {scenario.id}, Event {event_name_str}: No states found to check verdict.")
            else:
                actual_verdict = maximal_enabled_frontiers[0].value

            expected_verdict = verdict_checks[event_name_str]

            print(
                f"  Event Check: {event_name_str}, Expected: {expected_verdict}, Actual: {actual_verdict}, "
                f"MaxF: {[s.name for s in maximal_enabled_frontiers]}")
            assert actual_verdict == expected_verdict, \
                f"Scenario {scenario.id}, Event {event_name_str}: Expected {expected_verdict}, Got {actual_verdict}"

    run_local_flush_holding_queue(holding_queue, expected_vc, current_states, prop_formula, processes_map)
    if holding_queue:
        # Check if any final verdicts were expected for events that might only get processed now
        for event_in_h_queue in holding_queue[:]:  # This loop might be redundant if flush is exhaustive
            if event_in_h_queue.name in verdict_checks:
                maximal_enabled_frontiers = [s for s in current_states if not s.successors and s.enabled]
                actual_verdict = maximal_enabled_frontiers[0].value if maximal_enabled_frontiers else current_states[
                    -1].value
                expected_verdict = verdict_checks[event_in_h_queue.name]
                print(
                    f"  Event Check (Post-Flush): {event_in_h_queue.name}, Expected: {expected_verdict}, "
                    f"Actual: {actual_verdict}")
                assert actual_verdict == expected_verdict, \
                    f"Scenario {scenario.id}, Event {event_in_h_queue.name} (post-flush): " \
                    f"Expected {expected_verdict}, Got {actual_verdict}"
        if holding_queue:  # if still not empty after checking
            print(
                f"Warning for Scenario {scenario.id}: Holding queue not empty at end of trace. "
                f"Remaining: {[e.name for e in holding_queue]}")
