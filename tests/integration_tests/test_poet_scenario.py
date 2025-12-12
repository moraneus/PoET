# tests/integration_tests/test_poet_scenario_unified.py
# Unified test file using only real PoET implementation (no test harness)

import pytest
import tempfile
import json
import os
from typing import List, Tuple

from core.poet_monitor import PoETMonitor
from utils.config import Config


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
            ("e2", ["P2"], ["r"], [0, 1]),
            ("e3", ["P1"], ["s"], [2, 0]),
            ("e4", ["P2"], ["p"], [0, 2]),
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
        event_trace=[
            ("INIT", ["P1"], ["p"], [0]),
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["p"], [2]),
        ],
        expected_verdicts_after_event=[("e1", True), ("e2", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="AH_02_BECOMES_FALSE_IN_MIDDLE",
        description="Tests AH(p) where p holds then stops holding.",
        num_processes=1,
        pctl_spec="AH(p)",
        event_trace=[
            ("INIT", ["P1"], ["p"], [0]),
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["q"], [2]),
            ("e3", ["P1"], ["p"], [3]),
        ],
        expected_verdicts_after_event=[("e1", True), ("e2", False), ("e3", False)],
        expected_final_verdict=False,
    ),
    PoetScenario(
        scenario_id="AH_02_BECOMES_FALSE_IN_INITIAL",
        description="Tests AH(p) where p not holds from initial event.",
        num_processes=1,
        pctl_spec="AH(p)",
        event_trace=[
            ("INIT", ["P1"], ["q"], [0]),
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["q"], [2]),
            ("e3", ["P1"], ["p"], [3]),
        ],
        expected_verdicts_after_event=[("e1", False), ("e2", False), ("e3", False)],
        expected_final_verdict=False,
    ),
    PoetScenario(
        scenario_id="EY_01_SIMPLE_TRUE_WITH_INIT_HOLD",
        description="Tests EY(p) where p was true in the immediate predecessor.",
        num_processes=1,
        pctl_spec="EY(p)",
        event_trace=[
            ("INIT", ["P1"], ["p"], [0]),
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["q"], [2]),
        ],
        expected_verdicts_after_event=[("e1", True), ("e2", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EY_01_SIMPLE_TRUE_WITH_NO_INIT_HOLD",
        description="Tests EY(p) where p was true in the immediate predecessor.",
        num_processes=1,
        pctl_spec="EY(p)",
        event_trace=[
            ("INIT", ["P1"], ["r"], [0]),
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["q"], [2]),
        ],
        expected_verdicts_after_event=[("e1", False), ("e2", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EY_01_SIMPLE_FINAL_NOT_HOLD",
        description="Tests EY(p) where p was true in the immediate predecessor.",
        num_processes=1,
        pctl_spec="EY(p)",
        event_trace=[
            ("INIT", ["P1"], ["p"], [0]),
            ("e1", ["P1"], ["r"], [1]),
            ("e2", ["P1"], ["q"], [2]),
        ],
        expected_verdicts_after_event=[("e1", True), ("e2", False)],
        expected_final_verdict=False,
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
            ("INIT", ["P1"], ["p"], [0]),
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["q"], [2]),
            ("e3", ["P1"], ["p"], [3]),
        ],
        expected_verdicts_after_event=[("e1", True), ("e2", True), ("e3", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EH_01_BASIC_TRUE",
        description="Tests EH(p) where p holds now.",
        num_processes=1,
        pctl_spec="EH(p)",
        event_trace=[
            ("INIT", ["P1"], ["p"], [0]),
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["p"], [2]),
        ],
        expected_verdicts_after_event=[("e1", True), ("e2", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EH_02_BECOMES_FALSE",
        description="Tests EH(p) where p stops holding.",
        num_processes=1,
        pctl_spec="EH(p)",
        event_trace=[
            ("INIT", ["P1"], ["p"], [0]),
            ("e1", ["P1"], ["p"], [1]),
            ("e2", ["P1"], ["q"], [2]),
            ("e3", ["P1"], ["p"], [3]),
        ],
        expected_verdicts_after_event=[("e1", True), ("e2", False), ("e3", False)],
        expected_final_verdict=False,
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
            ("e_p2", True),
            ("e_merge", True),
        ],
        expected_final_verdict=True,
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
            ("e_merge2", ["P1", "P2"], ["m"], [3, 3]),
        ],
        expected_verdicts_after_event=[
            ("e_p1", False),
            ("e_q1", False),
            ("e_merge", True),
            ("e_merge2", False),
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
        expected_verdicts_after_event=[("e1", True), ("e2", True)],
        expected_final_verdict=True,
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
    PoetScenario(
        scenario_id="EXPERIMENT_2_CAUSALITY_20_EVENTS",
        description="Experiment 2: EP(EP(a) & EP(b) & EP(c) & !EP(d)) with 20 events from 1K trace - test framework "
        "uses basic algorithm",
        num_processes=5,
        pctl_spec="EP(EP(a) & EP(b) & EP(c) & !EP(d))",
        event_trace=[
            ("pa_int1", ["P1"], [], [1, 0, 0, 0, 0]),
            ("pb_int2", ["P2"], ["b"], [0, 1, 0, 0, 0]),
            ("pc_int3", ["P3"], ["c"], [0, 0, 1, 0, 0]),
            ("pd_int4", ["P4"], [], [0, 0, 0, 1, 0]),
            ("pa_pv_comm5", ["P1", "P5"], ["comm_pa_pv"], [2, 0, 0, 0, 1]),
            ("pd_pv_comm6", ["P4", "P5"], ["comm_pd_pv"], [2, 0, 0, 2, 2]),
            (
                "pv_decide7",
                ["P5"],
                ["pv_confirms_not_d", "pv_evaluates_cycle"],
                [2, 0, 0, 2, 3],
            ),
            ("pa_int8", ["P1"], [], [3, 0, 0, 0, 1]),
            ("pb_int9", ["P2"], ["b"], [0, 2, 0, 0, 0]),
            ("pc_int10", ["P3"], ["c"], [0, 0, 2, 0, 0]),
            ("pd_int11", ["P4"], ["d"], [2, 0, 0, 3, 2]),
            ("pa_pv_comm12", ["P1", "P5"], ["comm_pa_pv"], [4, 0, 0, 2, 4]),
            ("pc_pv_comm13", ["P3", "P5"], ["comm_pc_pv"], [4, 0, 3, 2, 5]),
            (
                "pv_decide14",
                ["P5"],
                ["pv_confirms_not_d", "pv_evaluates_cycle", "pv_knows_c"],
                [4, 0, 3, 2, 6],
            ),
            ("pa_int15", ["P1"], ["a"], [5, 0, 0, 2, 4]),
            ("pb_int16", ["P2"], ["b"], [0, 3, 0, 0, 0]),
            ("pc_int17", ["P3"], [], [4, 0, 4, 2, 5]),
            ("pd_int18", ["P4"], [], [2, 0, 0, 4, 2]),
            ("pb_pv_comm19", ["P2", "P5"], ["comm_pb_pv"], [4, 4, 3, 2, 7]),
            ("pc_pv_comm20", ["P3", "P5"], ["comm_pc_pv"], [4, 4, 5, 2, 8]),
        ],
        expected_verdicts_after_event=[
            ("pb_int2", False),
            ("pc_int3", False),
            ("pd_int11", False),
            ("pa_int15", True),
            ("pb_int16", True),
            ("pc_pv_comm20", True),
        ],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EXPERIMENT_1_TRACE_1K_60_EVENTS",
        description="Experiment 1: EP(status_ok & load_lt_100 & !critical_alarm) with 60 events from trace-1k.json",
        num_processes=3,
        pctl_spec="EP(status_ok & load_lt_100 & !critical_alarm)",
        event_trace=[
            ("s_int1", ["P2"], ["load_high"], [0, 1, 0]),
            ("a_int2", ["P3"], [], [0, 0, 1]),
            ("sm_comm3", ["P1", "P2"], ["s_m_comm"], [1, 2, 0]),
            ("am_comm4", ["P1", "P3"], ["a_m_comm"], [2, 2, 2]),
            ("m_decide5", ["P1"], [], [3, 2, 2]),
            ("s_int6", ["P2"], ["load_lt_100"], [1, 3, 0]),
            ("a_int7", ["P3"], [], [2, 2, 3]),
            ("sm_comm8", ["P1", "P2"], ["s_m_comm"], [4, 4, 2]),
            ("am_comm9", ["P1", "P3"], ["a_m_comm"], [5, 4, 4]),
            ("m_decide10", ["P1"], ["load_lt_100"], [6, 4, 4]),
            ("s_int11", ["P2"], ["load_high"], [4, 5, 2]),
            ("a_int12", ["P3"], [], [5, 4, 5]),
            ("sm_comm13", ["P1", "P2"], ["s_m_comm"], [7, 6, 4]),
            ("am_comm14", ["P1", "P3"], ["a_m_comm"], [8, 6, 6]),
            ("m_decide15", ["P1"], [], [9, 6, 6]),
            ("s_int16", ["P2"], ["load_high"], [7, 7, 4]),
            ("a_int17", ["P3"], ["critical_alarm"], [8, 6, 7]),
            ("sm_comm18", ["P1", "P2"], ["s_m_comm"], [10, 8, 6]),
            ("am_comm19", ["P1", "P3"], ["a_m_comm"], [11, 8, 8]),
            ("m_decide20", ["P1"], ["critical_alarm"], [12, 8, 8]),
            ("s_int21", ["P2"], ["load_lt_100"], [10, 9, 6]),
            ("a_int22", ["P3"], [], [11, 8, 9]),
            ("sm_comm23", ["P1", "P2"], ["s_m_comm"], [13, 10, 8]),
            ("am_comm24", ["P1", "P3"], ["a_m_comm"], [14, 10, 10]),
            ("m_decide25", ["P1"], ["load_lt_100"], [15, 10, 10]),
            ("s_int26", ["P2"], ["load_high"], [13, 11, 8]),
            ("a_int27", ["P3"], ["critical_alarm"], [14, 10, 11]),
            ("sm_comm28", ["P1", "P2"], ["s_m_comm"], [16, 12, 10]),
            ("am_comm29", ["P1", "P3"], ["a_m_comm"], [17, 12, 12]),
            ("m_decide30", ["P1"], ["critical_alarm"], [18, 12, 12]),
            ("s_int31", ["P2"], ["load_lt_100"], [16, 13, 10]),
            ("a_int32", ["P3"], [], [17, 12, 13]),
            ("sm_comm33", ["P1", "P2"], ["s_m_comm"], [19, 14, 12]),
            ("am_comm34", ["P1", "P3"], ["a_m_comm"], [20, 14, 14]),
            ("m_decide35", ["P1"], ["load_lt_100"], [21, 14, 14]),
            ("s_int36", ["P2"], ["load_high"], [19, 15, 12]),
            ("a_int37", ["P3"], ["critical_alarm"], [20, 14, 15]),
            ("sm_comm38", ["P1", "P2"], ["s_m_comm"], [22, 16, 14]),
            ("am_comm39", ["P1", "P3"], ["a_m_comm"], [23, 16, 16]),
            ("m_decide40", ["P1"], ["critical_alarm"], [24, 16, 16]),
            ("s_int41", ["P2"], ["load_lt_100"], [22, 17, 14]),
            ("a_int42", ["P3"], [], [23, 16, 17]),
            ("sm_comm43", ["P1", "P2"], ["s_m_comm"], [25, 18, 16]),
            ("am_comm44", ["P1", "P3"], ["a_m_comm"], [26, 18, 18]),
            ("m_decide45", ["P1"], ["load_lt_100", "status_ok"], [27, 18, 18]),
            ("s_int46", ["P2"], ["load_lt_100"], [25, 19, 16]),
            ("a_int47", ["P3"], ["critical_alarm"], [26, 18, 19]),
            ("sm_comm48", ["P1", "P2"], ["s_m_comm"], [28, 20, 18]),
            ("am_comm49", ["P1", "P3"], ["a_m_comm"], [29, 20, 20]),
            ("m_decide50", ["P1"], ["critical_alarm", "load_lt_100"], [30, 20, 20]),
            ("s_int51", ["P2"], ["load_lt_100"], [28, 21, 18]),
            ("a_int52", ["P3"], ["critical_alarm"], [29, 20, 21]),
            ("sm_comm53", ["P1", "P2"], ["s_m_comm"], [31, 22, 20]),
            ("am_comm54", ["P1", "P3"], ["a_m_comm"], [32, 22, 22]),
            ("m_decide55", ["P1"], ["critical_alarm", "load_lt_100"], [33, 22, 22]),
            ("s_int56", ["P2"], ["load_high"], [31, 23, 20]),
            ("a_int57", ["P3"], ["critical_alarm"], [32, 22, 23]),
            ("sm_comm58", ["P1", "P2"], ["s_m_comm"], [34, 24, 22]),
            ("am_comm59", ["P1", "P3"], ["a_m_comm"], [35, 24, 24]),
            ("m_decide60", ["P1"], ["critical_alarm"], [36, 24, 24]),
        ],
        expected_verdicts_after_event=[
            ("a_int7", False),
            ("m_decide45", True),
            ("m_decide60", True),
        ],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EXPERIMENT_1_TRACE_10K_60_EVENTS",
        description="Experiment 1: EP(status_ok & load_lt_100 & !critical_alarm) with 60 events from trace-10k.json",
        num_processes=3,
        pctl_spec="EP(status_ok & load_lt_100 & !critical_alarm)",
        event_trace=[
            ("s_int1", ["P2"], ["load_lt_100"], [0, 1, 0]),
            ("a_int2", ["P3"], ["critical_alarm"], [0, 0, 1]),
            ("sm_comm3", ["P1", "P2"], ["s_m_comm"], [1, 2, 0]),
            ("am_comm4", ["P1", "P3"], ["a_m_comm"], [2, 2, 2]),
            ("m_decide5", ["P1"], ["critical_alarm", "load_lt_100"], [3, 2, 2]),
            ("s_int6", ["P2"], ["load_high"], [1, 3, 0]),
            ("a_int7", ["P3"], ["critical_alarm"], [2, 2, 3]),
            ("sm_comm8", ["P1", "P2"], ["s_m_comm"], [4, 4, 2]),
            ("am_comm9", ["P1", "P3"], ["a_m_comm"], [5, 4, 4]),
            ("m_decide10", ["P1"], ["critical_alarm"], [6, 4, 4]),
            ("s_int11", ["P2"], ["load_lt_100"], [4, 5, 2]),
            ("a_int12", ["P3"], [], [5, 4, 5]),
            ("sm_comm13", ["P1", "P2"], ["s_m_comm"], [7, 6, 4]),
            ("am_comm14", ["P1", "P3"], ["a_m_comm"], [8, 6, 6]),
            ("m_decide15", ["P1"], ["load_lt_100"], [9, 6, 6]),
            ("s_int16", ["P2"], ["load_lt_100"], [7, 7, 4]),
            ("a_int17", ["P3"], [], [8, 6, 7]),
            ("sm_comm18", ["P1", "P2"], ["s_m_comm"], [10, 8, 6]),
            ("am_comm19", ["P1", "P3"], ["a_m_comm"], [11, 8, 8]),
            ("m_decide20", ["P1"], ["load_lt_100"], [12, 8, 8]),
            ("s_int21", ["P2"], ["load_high"], [10, 9, 6]),
            ("a_int22", ["P3"], ["critical_alarm"], [11, 8, 9]),
            ("sm_comm23", ["P1", "P2"], ["s_m_comm"], [13, 10, 8]),
            ("am_comm24", ["P1", "P3"], ["a_m_comm"], [14, 10, 10]),
            ("m_decide25", ["P1"], ["critical_alarm"], [15, 10, 10]),
            ("s_int26", ["P2"], ["load_lt_100"], [13, 11, 8]),
            ("a_int27", ["P3"], ["critical_alarm"], [14, 10, 11]),
            ("sm_comm28", ["P1", "P2"], ["s_m_comm"], [16, 12, 10]),
            ("am_comm29", ["P1", "P3"], ["a_m_comm"], [17, 12, 12]),
            ("m_decide30", ["P1"], ["critical_alarm", "load_lt_100"], [18, 12, 12]),
            ("s_int31", ["P2"], ["load_high"], [16, 13, 10]),
            ("a_int32", ["P3"], [], [17, 12, 13]),
            ("sm_comm33", ["P1", "P2"], ["s_m_comm"], [19, 14, 12]),
            ("am_comm34", ["P1", "P3"], ["a_m_comm"], [20, 14, 14]),
            ("m_decide35", ["P1"], [], [21, 14, 14]),
            ("s_int36", ["P2"], ["load_high"], [19, 15, 12]),
            ("a_int37", ["P3"], [], [20, 14, 15]),
            ("sm_comm38", ["P1", "P2"], ["s_m_comm"], [22, 16, 14]),
            ("am_comm39", ["P1", "P3"], ["a_m_comm"], [23, 16, 16]),
            ("m_decide40", ["P1"], [], [24, 16, 16]),
            ("s_int41", ["P2"], ["load_high"], [22, 17, 14]),
            ("a_int42", ["P3"], ["critical_alarm"], [23, 16, 17]),
            ("sm_comm43", ["P1", "P2"], ["s_m_comm"], [25, 18, 16]),
            ("am_comm44", ["P1", "P3"], ["a_m_comm"], [26, 18, 18]),
            ("m_decide45", ["P1"], ["critical_alarm"], [27, 18, 18]),
            ("s_int46", ["P2"], ["load_lt_100"], [25, 19, 16]),
            ("a_int47", ["P3"], [], [26, 18, 19]),
            ("sm_comm48", ["P1", "P2"], ["s_m_comm"], [28, 20, 18]),
            ("am_comm49", ["P1", "P3"], ["a_m_comm"], [29, 20, 20]),
            ("m_decide50", ["P1"], ["load_lt_100", "status_ok"], [30, 20, 20]),
            ("s_int51", ["P2"], ["load_high"], [28, 21, 18]),
            ("a_int52", ["P3"], ["critical_alarm"], [29, 20, 21]),
            ("sm_comm53", ["P1", "P2"], ["s_m_comm"], [31, 22, 20]),
            ("am_comm54", ["P1", "P3"], ["a_m_comm"], [32, 22, 22]),
            ("m_decide55", ["P1"], ["critical_alarm"], [33, 22, 22]),
            ("s_int56", ["P2"], ["load_lt_100"], [31, 23, 20]),
            ("a_int57", ["P3"], ["critical_alarm"], [32, 22, 23]),
            ("sm_comm58", ["P1", "P2"], ["s_m_comm"], [34, 24, 22]),
            ("am_comm59", ["P1", "P3"], ["a_m_comm"], [35, 24, 24]),
            ("m_decide60", ["P1"], ["critical_alarm", "load_lt_100"], [36, 24, 24]),
        ],
        expected_verdicts_after_event=[
            ("m_decide10", False),
            ("am_comm49", False),
            ("m_decide50", True),
            ("m_decide60", True),
        ],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EXPERIMENT_1_TRACE_100K_10_EVENTS",
        description="Experiment 1: EP(status_ok & load_lt_100 & !critical_alarm) with 10 events from trace-100k.json",
        num_processes=3,
        pctl_spec="EP(status_ok & load_lt_100 & !critical_alarm)",
        event_trace=[
            ("s_int1", ["P2"], ["load_lt_100"], [0, 1, 0]),
            ("a_int2", ["P3"], [], [0, 0, 1]),
            ("sm_comm3", ["P1", "P2"], ["s_m_comm"], [1, 2, 0]),
            ("am_comm4", ["P1", "P3"], ["a_m_comm"], [2, 2, 2]),
            ("m_decide5", ["P1"], ["load_lt_100", "status_ok"], [3, 2, 2]),
            ("s_int6", ["P2"], ["load_high"], [1, 3, 0]),
            ("a_int7", ["P3"], [], [2, 2, 3]),
            ("sm_comm8", ["P1", "P2"], ["s_m_comm"], [4, 4, 2]),
            ("am_comm9", ["P1", "P3"], ["a_m_comm"], [5, 4, 4]),
            ("m_decide10", ["P1"], [], [6, 4, 4]),
        ],
        expected_verdicts_after_event=[
            ("am_comm4", False),
            ("sm_comm3", False),
            ("m_decide5", True),
            ("m_decide10", True),
        ],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EXPERIMENT_1_TRACE_500K_60_EVENTS",
        description="Experiment 1: EP(status_ok & load_lt_100 & !critical_alarm) with 60 events from trace-500k.json",
        num_processes=3,
        pctl_spec="EP(status_ok & load_lt_100 & !critical_alarm)",
        event_trace=[
            ("s_int1", ["P2"], ["load_lt_100"], [0, 1, 0]),
            ("a_int2", ["P3"], [], [0, 0, 1]),
            ("sm_comm3", ["P1", "P2"], ["s_m_comm"], [1, 2, 0]),
            ("am_comm4", ["P1", "P3"], ["a_m_comm"], [2, 2, 2]),
            ("m_decide5", ["P1"], ["load_lt_100"], [3, 2, 2]),
            ("s_int6", ["P2"], ["load_high"], [1, 3, 0]),
            ("a_int7", ["P3"], ["critical_alarm"], [2, 2, 3]),
            ("sm_comm8", ["P1", "P2"], ["s_m_comm"], [4, 4, 2]),
            ("am_comm9", ["P1", "P3"], ["a_m_comm"], [5, 4, 4]),
            ("m_decide10", ["P1"], ["critical_alarm"], [6, 4, 4]),
            ("s_int11", ["P2"], ["load_high"], [4, 5, 2]),
            ("a_int12", ["P3"], ["critical_alarm"], [5, 4, 5]),
            ("sm_comm13", ["P1", "P2"], ["s_m_comm"], [7, 6, 4]),
            ("am_comm14", ["P1", "P3"], ["a_m_comm"], [8, 6, 6]),
            ("m_decide15", ["P1"], ["critical_alarm"], [9, 6, 6]),
            ("s_int16", ["P2"], ["load_high"], [7, 7, 4]),
            ("a_int17", ["P3"], [], [8, 6, 7]),
            ("sm_comm18", ["P1", "P2"], ["s_m_comm"], [10, 8, 6]),
            ("am_comm19", ["P1", "P3"], ["a_m_comm"], [11, 8, 8]),
            ("m_decide20", ["P1"], [], [12, 8, 8]),
            ("s_int21", ["P2"], ["load_lt_100"], [10, 9, 6]),
            ("a_int22", ["P3"], [], [11, 8, 9]),
            ("sm_comm23", ["P1", "P2"], ["s_m_comm"], [13, 10, 8]),
            ("am_comm24", ["P1", "P3"], ["a_m_comm"], [14, 10, 10]),
            ("m_decide25", ["P1"], ["load_lt_100"], [15, 10, 10]),
            ("s_int26", ["P2"], ["load_high"], [13, 11, 8]),
            ("a_int27", ["P3"], ["critical_alarm"], [14, 10, 11]),
            ("sm_comm28", ["P1", "P2"], ["s_m_comm"], [16, 12, 10]),
            ("am_comm29", ["P1", "P3"], ["a_m_comm"], [17, 12, 12]),
            ("m_decide30", ["P1"], ["critical_alarm"], [18, 12, 12]),
            ("s_int31", ["P2"], ["load_lt_100"], [16, 13, 10]),
            ("a_int32", ["P3"], [], [17, 12, 13]),
            ("sm_comm33", ["P1", "P2"], ["s_m_comm"], [19, 14, 12]),
            ("am_comm34", ["P1", "P3"], ["a_m_comm"], [20, 14, 14]),
            ("m_decide35", ["P1"], ["load_lt_100", "status_ok"], [21, 14, 14]),
            ("s_int36", ["P2"], ["load_high"], [19, 15, 12]),
            ("a_int37", ["P3"], ["critical_alarm"], [20, 14, 15]),
            ("sm_comm38", ["P1", "P2"], ["s_m_comm"], [22, 16, 14]),
            ("am_comm39", ["P1", "P3"], ["a_m_comm"], [23, 16, 16]),
            ("m_decide40", ["P1"], ["critical_alarm"], [24, 16, 16]),
            ("s_int41", ["P2"], ["load_high"], [22, 17, 14]),
            ("a_int42", ["P3"], ["critical_alarm"], [23, 16, 17]),
            ("sm_comm43", ["P1", "P2"], ["s_m_comm"], [25, 18, 16]),
            ("am_comm44", ["P1", "P3"], ["a_m_comm"], [26, 18, 18]),
            ("m_decide45", ["P1"], ["critical_alarm"], [27, 18, 18]),
            ("s_int46", ["P2"], ["load_lt_100"], [25, 19, 16]),
            ("a_int47", ["P3"], [], [26, 18, 19]),
            ("sm_comm48", ["P1", "P2"], ["s_m_comm"], [28, 20, 18]),
            ("am_comm49", ["P1", "P3"], ["a_m_comm"], [29, 20, 20]),
            ("m_decide50", ["P1"], ["load_lt_100"], [30, 20, 20]),
            ("s_int51", ["P2"], ["load_high"], [28, 21, 18]),
            ("a_int52", ["P3"], ["critical_alarm"], [29, 20, 21]),
            ("sm_comm53", ["P1", "P2"], ["s_m_comm"], [31, 22, 20]),
            ("am_comm54", ["P1", "P3"], ["a_m_comm"], [32, 22, 22]),
            ("m_decide55", ["P1"], ["critical_alarm"], [33, 22, 22]),
            ("s_int56", ["P2"], ["load_high"], [31, 23, 20]),
            ("a_int57", ["P3"], ["critical_alarm"], [32, 22, 23]),
            ("sm_comm58", ["P1", "P2"], ["s_m_comm"], [34, 24, 22]),
            ("am_comm59", ["P1", "P3"], ["a_m_comm"], [35, 24, 24]),
            ("m_decide60", ["P1"], ["critical_alarm"], [36, 24, 24]),
        ],
        expected_verdicts_after_event=[("m_decide35", True), ("m_decide60", True)],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EXPERIMENT_3_TRACE_1K_50_EVENTS",
        description="Experiment 3: EP( (aX & EP(pX)) | (aY & EP(pY)) ) with 50 events from trace-1k.json - becomes TRUE at px_act35",
        num_processes=3,
        pctl_spec="EP( (aX & EP(pX)) | (aY & EP(pY)) )",
        event_trace=[
            ("px_pre1", ["P1"], ["dX"], [1, 0, 0]),
            ("px_act2", ["P1"], ["dX"], [2, 0, 0]),
            ("py_pre3", ["P2"], ["dY"], [0, 1, 0]),
            ("py_act4", ["P2"], ["dY"], [0, 2, 0]),
            ("pv_eval5", ["P3"], ["pve"], [0, 0, 1]),
            ("px_pre6", ["P1"], ["dX"], [3, 0, 0]),
            ("px_act7", ["P1"], ["dX"], [4, 0, 0]),
            ("py_pre8", ["P2"], [], [0, 3, 0]),
            ("py_act9", ["P2"], [], [0, 4, 0]),
            ("pxpv_comm10", ["P1", "P3"], ["cXP"], [5, 0, 2]),
            ("pv_eval11", ["P3"], ["pve"], [5, 0, 3]),
            ("px_pre12", ["P1"], [], [6, 0, 2]),
            ("px_act13", ["P1"], [], [7, 0, 2]),
            ("py_pre14", ["P2"], [], [0, 5, 0]),
            ("py_act15", ["P2"], [], [0, 6, 0]),
            ("pypv_comm16", ["P2", "P3"], ["cYP"], [5, 7, 4]),
            ("pv_eval17", ["P3"], ["pve"], [5, 7, 5]),
            ("px_pre18", ["P1"], [], [8, 0, 2]),
            ("px_act19", ["P1"], [], [9, 0, 2]),
            ("py_pre20", ["P2"], ["pY"], [5, 8, 4]),
            ("py_act21", ["P2"], ["pY"], [5, 9, 4]),
            ("pxpv_comm22", ["P1", "P3"], ["cXP"], [10, 7, 6]),
            ("pv_eval23", ["P3"], ["pve"], [10, 7, 7]),
            ("px_pre24", ["P1"], [], [11, 7, 6]),
            ("px_act25", ["P1"], [], [12, 7, 6]),
            ("py_pre26", ["P2"], [], [5, 10, 4]),
            ("py_act27", ["P2"], [], [5, 11, 4]),
            ("pv_eval28", ["P3"], ["pve"], [10, 7, 8]),
            ("px_pre29", ["P1"], [], [13, 7, 6]),
            ("px_act30", ["P1"], [], [14, 7, 6]),
            ("py_pre31", ["P2"], [], [5, 12, 4]),
            ("py_act32", ["P2"], [], [5, 13, 4]),
            ("pv_eval33", ["P3"], ["pve"], [10, 7, 9]),
            ("px_pre34", ["P1"], ["pX"], [15, 7, 6]),
            ("px_act35", ["P1"], ["aX", "pX"], [16, 7, 6]),
            ("py_pre36", ["P2"], [], [5, 14, 4]),
            ("py_act37", ["P2"], [], [5, 15, 4]),
            ("pv_eval38", ["P3"], ["pve"], [10, 7, 10]),
            ("px_pre39", ["P1"], ["pX"], [17, 7, 6]),
            ("px_act40", ["P1"], ["aX", "pX"], [18, 7, 6]),
            ("py_pre41", ["P2"], [], [5, 16, 4]),
            ("py_act42", ["P2"], [], [5, 17, 4]),
            ("pv_eval43", ["P3"], ["pve"], [10, 7, 11]),
            ("px_pre44", ["P1"], [], [19, 7, 6]),
            ("px_act45", ["P1"], [], [20, 7, 6]),
            ("py_pre46", ["P2"], [], [5, 18, 4]),
            ("py_act47", ["P2"], [], [5, 19, 4]),
            ("pv_eval48", ["P3"], ["pve"], [10, 7, 12]),
            ("px_pre49", ["P1"], ["pX"], [21, 7, 6]),
            ("px_act50", ["P1"], ["pX"], [22, 7, 6]),
        ],
        expected_verdicts_after_event=[
            ("px_pre34", False),
            ("px_act35", True),
            ("px_act40", True),
        ],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EXPERIMENT_3_TRACE_10K_50_EVENTS",
        description="Experiment 3: EP( (aX & EP(pX)) | (aY & EP(pY)) ) with 50 events from trace-10k.json - becomes TRUE at px_act18",
        num_processes=3,
        pctl_spec="EP( (aX & EP(pX)) | (aY & EP(pY)) )",
        event_trace=[
            ("px_pre1", ["P1"], ["dX"], [1, 0, 0]),
            ("px_act2", ["P1"], ["dX"], [2, 0, 0]),
            ("py_pre3", ["P2"], ["dY"], [0, 1, 0]),
            ("py_act4", ["P2"], ["dY"], [0, 2, 0]),
            ("pv_eval5", ["P3"], ["pve"], [0, 0, 1]),
            ("px_pre6", ["P1"], ["dX"], [3, 0, 0]),
            ("px_act7", ["P1"], ["dX"], [4, 0, 0]),
            ("py_pre8", ["P2"], [], [0, 3, 0]),
            ("py_act9", ["P2"], [], [0, 4, 0]),
            ("pv_eval10", ["P3"], ["pve"], [0, 0, 2]),
            ("px_pre11", ["P1"], [], [5, 0, 0]),
            ("px_act12", ["P1"], [], [6, 0, 0]),
            ("py_pre13", ["P2"], [], [0, 5, 0]),
            ("py_act14", ["P2"], [], [0, 6, 0]),
            ("pxpv_comm15", ["P1", "P3"], ["cXP"], [7, 0, 3]),
            ("pv_eval16", ["P3"], ["pve"], [7, 0, 4]),
            ("px_pre17", ["P1"], ["pX"], [8, 0, 3]),
            ("px_act18", ["P1"], ["aX", "pX"], [9, 0, 3]),
            ("py_pre19", ["P2"], [], [0, 7, 0]),
            ("py_act20", ["P2"], [], [0, 8, 0]),
            ("pv_eval21", ["P3"], ["pve"], [7, 0, 5]),
            ("px_pre22", ["P1"], ["pX"], [10, 0, 3]),
            ("px_act23", ["P1"], ["aX", "pX"], [11, 0, 3]),
            ("py_pre24", ["P2"], [], [0, 9, 0]),
            ("py_act25", ["P2"], [], [0, 10, 0]),
            ("pv_eval26", ["P3"], ["pve"], [7, 0, 6]),
            ("px_pre27", ["P1"], [], [12, 0, 3]),
            ("px_act28", ["P1"], [], [13, 0, 3]),
            ("py_pre29", ["P2"], [], [0, 11, 0]),
            ("py_act30", ["P2"], [], [0, 12, 0]),
            ("pxpv_comm31", ["P1", "P3"], ["cXP"], [14, 0, 7]),
            ("pv_eval32", ["P3"], ["pve"], [14, 0, 8]),
            ("px_pre33", ["P1"], [], [15, 0, 7]),
            ("px_act34", ["P1"], [], [16, 0, 7]),
            ("py_pre35", ["P2"], [], [0, 13, 0]),
            ("py_act36", ["P2"], [], [0, 14, 0]),
            ("pxpv_comm37", ["P1", "P3"], ["cXP"], [17, 0, 9]),
            ("pypv_comm38", ["P2", "P3"], ["cYP"], [17, 15, 10]),
            ("pv_eval39", ["P3"], ["pve"], [17, 15, 11]),
            ("px_pre40", ["P1"], ["pX"], [18, 0, 9]),
            ("px_act41", ["P1"], ["aX", "pX"], [19, 0, 9]),
            ("py_pre42", ["P2"], ["pY"], [17, 16, 10]),
            ("py_act43", ["P2"], ["pY"], [17, 17, 10]),
            ("pv_eval44", ["P3"], ["pve"], [17, 15, 12]),
            ("px_pre45", ["P1"], [], [20, 0, 9]),
            ("px_act46", ["P1"], [], [21, 0, 9]),
            ("py_pre47", ["P2"], [], [17, 18, 10]),
            ("py_act48", ["P2"], [], [17, 19, 10]),
            ("pxpv_comm49", ["P1", "P3"], ["cXP"], [22, 15, 13]),
            ("pv_eval50", ["P3"], ["pve"], [22, 15, 14]),
        ],
        expected_verdicts_after_event=[
            ("px_pre17", False),
            ("px_act18", True),
            ("px_act23", True),
        ],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EXPERIMENT_3_TRACE_100K_50_EVENTS",
        description="Experiment 3: EP( (aX & EP(pX)) | (aY & EP(pY)) ) with 50 events from trace-100k.json - becomes TRUE at py_act9",
        num_processes=3,
        pctl_spec="EP( (aX & EP(pX)) | (aY & EP(pY)) )",
        event_trace=[
            ("px_pre1", ["P1"], ["dX"], [1, 0, 0]),
            ("px_act2", ["P1"], ["dX"], [2, 0, 0]),
            ("py_pre3", ["P2"], ["dY"], [0, 1, 0]),
            ("py_act4", ["P2"], ["dY"], [0, 2, 0]),
            ("pv_eval5", ["P3"], ["pve"], [0, 0, 1]),
            ("px_pre6", ["P1"], ["dX"], [3, 0, 0]),
            ("px_act7", ["P1"], ["dX"], [4, 0, 0]),
            ("py_pre8", ["P2"], ["pY"], [0, 3, 0]),
            ("py_act9", ["P2"], ["aY", "pY"], [0, 4, 0]),
            ("pypv_comm10", ["P2", "P3"], ["cYP"], [0, 5, 2]),
            ("pv_eval11", ["P3"], ["kvaY", "kvpY", "pve"], [0, 5, 3]),
            ("px_pre12", ["P1"], ["pX"], [5, 0, 0]),
            ("px_act13", ["P1"], ["pX"], [6, 0, 0]),
            ("py_pre14", ["P2"], ["pY"], [0, 6, 2]),
            ("py_act15", ["P2"], ["aY", "pY"], [0, 7, 2]),
            ("pypv_comm16", ["P2", "P3"], ["cYP"], [0, 8, 4]),
            ("pv_eval17", ["P3"], ["kvaY", "kvpY", "pve"], [0, 8, 5]),
            ("px_pre18", ["P1"], ["pX"], [7, 0, 0]),
            ("px_act19", ["P1"], ["pX"], [8, 0, 0]),
            ("py_pre20", ["P2"], ["pY"], [0, 9, 4]),
            ("py_act21", ["P2"], ["aY", "pY"], [0, 10, 4]),
            ("pxpv_comm22", ["P1", "P3"], ["cXP"], [9, 8, 6]),
            ("pv_eval23", ["P3"], ["kvpX", "pve"], [9, 8, 7]),
            ("px_pre24", ["P1"], ["pX"], [10, 8, 6]),
            ("px_act25", ["P1"], ["aX", "pX"], [11, 8, 6]),
            ("py_pre26", ["P2"], [], [0, 11, 4]),
            ("py_act27", ["P2"], [], [0, 12, 4]),
            ("pypv_comm28", ["P2", "P3"], ["cYP"], [9, 13, 8]),
            ("pv_eval29", ["P3"], ["pve"], [9, 13, 9]),
            ("px_pre30", ["P1"], ["pX"], [12, 8, 6]),
            ("px_act31", ["P1"], ["aX", "pX"], [13, 8, 6]),
            ("py_pre32", ["P2"], [], [9, 14, 8]),
            ("py_act33", ["P2"], [], [9, 15, 8]),
            ("pv_eval34", ["P3"], ["pve"], [9, 13, 10]),
            ("px_pre35", ["P1"], ["pX"], [14, 8, 6]),
            ("px_act36", ["P1"], ["pX"], [15, 8, 6]),
            ("py_pre37", ["P2"], [], [9, 16, 8]),
            ("py_act38", ["P2"], [], [9, 17, 8]),
            ("pv_eval39", ["P3"], ["pve"], [9, 13, 11]),
            ("px_pre40", ["P1"], [], [16, 8, 6]),
            ("px_act41", ["P1"], [], [17, 8, 6]),
            ("py_pre42", ["P2"], [], [9, 18, 8]),
            ("py_act43", ["P2"], [], [9, 19, 8]),
            ("pypv_comm44", ["P2", "P3"], ["cYP"], [9, 20, 12]),
            ("pv_eval45", ["P3"], ["pve"], [9, 20, 13]),
            ("px_pre46", ["P1"], [], [18, 8, 6]),
            ("px_act47", ["P1"], [], [19, 8, 6]),
            ("py_pre48", ["P2"], [], [9, 21, 12]),
            ("py_act49", ["P2"], [], [9, 22, 12]),
            ("pxpv_comm50", ["P1", "P3"], ["cXP"], [20, 20, 14]),
        ],
        expected_verdicts_after_event=[
            ("py_pre8", False),
            ("py_act9", True),
            ("py_act15", True),
        ],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EXPERIMENT_3_TRACE_500K_50_EVENTS",
        description="Experiment 3: EP( (aX & EP(pX)) | (aY & EP(pY)) ) with 50 events from trace-500k.json - becomes TRUE at px_act45",
        num_processes=3,
        pctl_spec="EP( (aX & EP(pX)) | (aY & EP(pY)) )",
        event_trace=[
            ("px_pre1", ["P1"], ["dX"], [1, 0, 0]),
            ("px_act2", ["P1"], ["dX"], [2, 0, 0]),
            ("py_pre3", ["P2"], ["dY"], [0, 1, 0]),
            ("py_act4", ["P2"], ["dY"], [0, 2, 0]),
            ("pypv_comm5", ["P2", "P3"], ["cYP"], [0, 3, 1]),
            ("pv_eval6", ["P3"], ["pve"], [0, 3, 2]),
            ("px_pre7", ["P1"], ["dX"], [3, 0, 0]),
            ("px_act8", ["P1"], ["dX"], [4, 0, 0]),
            ("py_pre9", ["P2"], [], [0, 4, 1]),
            ("py_act10", ["P2"], [], [0, 5, 1]),
            ("pxpv_comm11", ["P1", "P3"], ["cXP"], [5, 3, 3]),
            ("pv_eval12", ["P3"], ["pve"], [5, 3, 4]),
            ("px_pre13", ["P1"], [], [6, 3, 3]),
            ("px_act14", ["P1"], [], [7, 3, 3]),
            ("py_pre15", ["P2"], [], [0, 6, 1]),
            ("py_act16", ["P2"], [], [0, 7, 1]),
            ("pypv_comm17", ["P2", "P3"], ["cYP"], [5, 8, 5]),
            ("pv_eval18", ["P3"], ["pve"], [5, 8, 6]),
            ("px_pre19", ["P1"], [], [8, 3, 3]),
            ("px_act20", ["P1"], [], [9, 3, 3]),
            ("py_pre21", ["P2"], [], [5, 9, 5]),
            ("py_act22", ["P2"], [], [5, 10, 5]),
            ("pv_eval23", ["P3"], ["pve"], [5, 8, 7]),
            ("px_pre24", ["P1"], ["pX"], [10, 3, 3]),
            ("px_act25", ["P1"], ["pX"], [11, 3, 3]),
            ("py_pre26", ["P2"], [], [5, 11, 5]),
            ("py_act27", ["P2"], [], [5, 12, 5]),
            ("pv_eval28", ["P3"], ["pve"], [5, 8, 8]),
            ("px_pre29", ["P1"], [], [12, 3, 3]),
            ("px_act30", ["P1"], [], [13, 3, 3]),
            ("py_pre31", ["P2"], [], [5, 13, 5]),
            ("py_act32", ["P2"], [], [5, 14, 5]),
            ("pv_eval33", ["P3"], ["pve"], [5, 8, 9]),
            ("px_pre34", ["P1"], [], [14, 3, 3]),
            ("px_act35", ["P1"], [], [15, 3, 3]),
            ("py_pre36", ["P2"], ["pY"], [5, 15, 5]),
            ("py_act37", ["P2"], ["pY"], [5, 16, 5]),
            ("pv_eval38", ["P3"], ["pve"], [5, 8, 10]),
            ("px_pre39", ["P1"], [], [16, 3, 3]),
            ("px_act40", ["P1"], [], [17, 3, 3]),
            ("py_pre41", ["P2"], [], [5, 17, 5]),
            ("py_act42", ["P2"], [], [5, 18, 5]),
            ("pv_eval43", ["P3"], ["pve"], [5, 8, 11]),
            ("px_pre44", ["P1"], ["pX"], [18, 3, 3]),
            ("px_act45", ["P1"], ["aX", "pX"], [19, 3, 3]),
            ("py_pre46", ["P2"], [], [5, 19, 5]),
            ("py_act47", ["P2"], [], [5, 20, 5]),
            ("pv_eval48", ["P3"], ["pve"], [5, 8, 12]),
            ("px_pre49", ["P1"], [], [20, 3, 3]),
            ("px_act50", ["P1"], [], [21, 3, 3]),
        ],
        expected_verdicts_after_event=[
            ("px_pre44", False),
            ("px_act45", True),
            ("py_act47", True),
        ],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EXPERIMENT_4_TRACE_1K_50_EVENTS",
        description="Experiment 4: EP( (EP(s1) & !EP(j1)) | (EP(j2) & ms & !EP(s2)) ) with 20 events from trace-1k.json - becomes TRUE at s1_int16",
        num_processes=6,
        pctl_spec="EP( (EP(s1) & !EP(j1)) | (EP(j2) & ms & !EP(s2)) )",
        event_trace=[
            ("s1_int1", ["P1"], ["dS1"], [1, 0, 0, 0, 0, 0]),
            ("j1_int2", ["P2"], ["dJ1"], [0, 1, 0, 0, 0, 0]),
            ("j2_int3", ["P3"], ["dJ2"], [0, 0, 1, 0, 0, 0]),
            ("ms_int4", ["P4"], ["dMS"], [0, 0, 0, 1, 0, 0]),
            ("s2_int5", ["P5"], ["dS2"], [0, 0, 0, 0, 1, 0]),
            ("j2_po_comm6", ["P3", "P6"], ["cJ2PO"], [0, 0, 2, 0, 0, 1]),
            ("s2_po_comm7", ["P5", "P6"], ["cS2PO"], [0, 0, 2, 0, 2, 2]),
            ("po_eval8", ["P6"], ["poe"], [0, 0, 2, 0, 2, 3]),
            ("s1_int9", ["P1"], ["dS1"], [2, 0, 0, 0, 0, 0]),
            ("j1_int10", ["P2"], ["dJ1"], [0, 2, 0, 0, 0, 0]),
            ("j2_int11", ["P3"], ["dJ2"], [0, 0, 3, 0, 0, 1]),
            ("ms_int12", ["P4"], [], [0, 0, 0, 2, 0, 0]),
            ("s2_int13", ["P5"], ["s2"], [0, 0, 2, 0, 3, 2]),
            ("ms_po_comm14", ["P4", "P6"], ["cMSPO"], [0, 0, 2, 3, 2, 4]),
            ("po_eval15", ["P6"], ["k_not_j1", "k_not_s2", "poe"], [0, 0, 2, 3, 2, 5]),
            ("s1_int16", ["P1"], ["s1"], [3, 0, 0, 0, 0, 0]),
            ("j1_int17", ["P2"], [], [0, 3, 0, 0, 0, 0]),
            ("j2_int18", ["P3"], [], [0, 0, 4, 0, 0, 1]),
            ("ms_int19", ["P4"], [], [0, 0, 2, 4, 2, 4]),
            ("s2_int20", ["P5"], [], [0, 0, 2, 0, 4, 2]),
        ],
        expected_verdicts_after_event=[
            ("po_eval15", False),
            ("s1_int16", True),
            ("j1_int17", True),
        ],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EXPERIMENT_4_TRACE_10K_20_EVENTS",
        description="Experiment 4: EP( (EP(s1) & !EP(j1)) | (EP(j2) & ms & !EP(s2)) ) with 50 events from trace-10k.json - becomes TRUE at s1_int15",
        num_processes=6,
        pctl_spec="EP( (EP(s1) & !EP(j1)) | (EP(j2) & ms & !EP(s2)) )",
        event_trace=[
            ("s1_int1", ["P1"], ["dS1"], [1, 0, 0, 0, 0, 0]),
            ("j1_int2", ["P2"], ["dJ1"], [0, 1, 0, 0, 0, 0]),
            ("j2_int3", ["P3"], ["dJ2"], [0, 0, 1, 0, 0, 0]),
            ("ms_int4", ["P4"], ["dMS"], [0, 0, 0, 1, 0, 0]),
            ("s2_int5", ["P5"], ["dS2"], [0, 0, 0, 0, 1, 0]),
            ("po_eval6", ["P6"], ["poe"], [0, 0, 0, 0, 0, 1]),
            ("s1_int7", ["P1"], ["dS1"], [2, 0, 0, 0, 0, 0]),
            ("j1_int8", ["P2"], ["dJ1"], [0, 2, 0, 0, 0, 0]),
            ("j2_int9", ["P3"], ["dJ2"], [0, 0, 2, 0, 0, 0]),
            ("ms_int10", ["P4"], ["dMS"], [0, 0, 0, 2, 0, 0]),
            ("s2_int11", ["P5"], ["dS2"], [0, 0, 0, 0, 2, 0]),
            ("j2_po_comm12", ["P3", "P6"], ["cJ2PO"], [0, 0, 3, 0, 0, 2]),
            ("ms_po_comm13", ["P4", "P6"], ["cMSPO"], [0, 0, 3, 3, 0, 3]),
            ("po_eval14", ["P6"], ["k_not_j1", "k_not_s2", "poe"], [0, 0, 3, 3, 0, 4]),
            ("s1_int15", ["P1"], ["s1"], [3, 0, 0, 0, 0, 0]),
            ("j1_int16", ["P2"], [], [0, 3, 0, 0, 0, 0]),
            ("j2_int17", ["P3"], ["j2"], [0, 0, 4, 0, 0, 2]),
            ("ms_int18", ["P4"], [], [0, 0, 3, 4, 0, 3]),
            ("s2_int19", ["P5"], [], [0, 0, 0, 0, 3, 0]),
            ("s1_po_comm20", ["P1", "P6"], ["cS1PO"], [4, 0, 3, 3, 0, 5]),
        ],
        expected_verdicts_after_event=[
            ("po_eval14", False),
            ("s1_int15", True),
            ("j1_int16", True),
        ],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EXPERIMENT_4_TRACE_100K_20_EVENTS",
        description="Experiment 4: EP( (EP(s1) & !EP(j1)) | (EP(j2) & ms & !EP(s2)) ) with 50 events from trace-100k.json - becomes TRUE at s1_int16",
        num_processes=6,
        pctl_spec="EP( (EP(s1) & !EP(j1)) | (EP(j2) & ms & !EP(s2)) )",
        event_trace=[
            ("s1_int1", ["P1"], ["dS1"], [1, 0, 0, 0, 0, 0]),
            ("j1_int2", ["P2"], ["dJ1"], [0, 1, 0, 0, 0, 0]),
            ("j2_int3", ["P3"], ["dJ2"], [0, 0, 1, 0, 0, 0]),
            ("ms_int4", ["P4"], ["dMS"], [0, 0, 0, 1, 0, 0]),
            ("s2_int5", ["P5"], ["dS2"], [0, 0, 0, 0, 1, 0]),
            ("po_eval6", ["P6"], ["poe"], [0, 0, 0, 0, 0, 1]),
            ("s1_int7", ["P1"], ["dS1"], [2, 0, 0, 0, 0, 0]),
            ("j1_int8", ["P2"], ["dJ1"], [0, 2, 0, 0, 0, 0]),
            ("j2_int9", ["P3"], ["dJ2"], [0, 0, 2, 0, 0, 0]),
            ("ms_int10", ["P4"], ["dMS"], [0, 0, 0, 2, 0, 0]),
            ("s2_int11", ["P5"], ["dS2"], [0, 0, 0, 0, 2, 0]),
            ("s1_po_comm12", ["P1", "P6"], ["cS1PO"], [3, 0, 0, 0, 0, 2]),
            ("j1_po_comm13", ["P2", "P6"], ["cJ1PO"], [3, 3, 0, 0, 0, 3]),
            ("ms_po_comm14", ["P4", "P6"], ["cMSPO"], [3, 3, 0, 3, 0, 4]),
            ("po_eval15", ["P6"], ["k_not_j1", "k_not_s2", "poe"], [3, 3, 0, 3, 0, 5]),
            ("s1_int16", ["P1"], ["s1"], [4, 0, 0, 0, 0, 2]),
            ("j1_int17", ["P2"], [], [3, 4, 0, 0, 0, 3]),
            ("j2_int18", ["P3"], ["j2"], [0, 0, 3, 0, 0, 0]),
            ("ms_int19", ["P4"], [], [3, 3, 0, 4, 0, 4]),
            ("s2_int20", ["P5"], ["s2"], [0, 0, 0, 0, 3, 0]),
        ],
        expected_verdicts_after_event=[
            ("po_eval15", False),
            ("s1_int16", True),
            ("j1_int17", True),
        ],
        expected_final_verdict=True,
    ),
    PoetScenario(
        scenario_id="EXPERIMENT_4_TRACE_500K_20_EVENTS",
        description="Experiment 4: EP( (EP(s1) & !EP(j1)) | (EP(j2) & ms & !EP(s2)) ) with 50 events from trace-500k.json - remains FALSE throughout",
        num_processes=6,
        pctl_spec="EP( (EP(s1) & !EP(j1)) | (EP(j2) & ms & !EP(s2)) )",
        event_trace=[
            ("s1_int1", ["P1"], ["dS1"], [1, 0, 0, 0, 0, 0]),
            ("j1_int2", ["P2"], ["dJ1"], [0, 1, 0, 0, 0, 0]),
            ("j2_int3", ["P3"], ["dJ2"], [0, 0, 1, 0, 0, 0]),
            ("ms_int4", ["P4"], ["dMS"], [0, 0, 0, 1, 0, 0]),
            ("s2_int5", ["P5"], ["dS2"], [0, 0, 0, 0, 1, 0]),
            ("po_eval6", ["P6"], ["poe"], [0, 0, 0, 0, 0, 1]),
            ("s1_int7", ["P1"], ["dS1"], [2, 0, 0, 0, 0, 0]),
            ("j1_int8", ["P2"], ["dJ1"], [0, 2, 0, 0, 0, 0]),
            ("j2_int9", ["P3"], ["dJ2"], [0, 0, 2, 0, 0, 0]),
            ("ms_int10", ["P4"], ["dMS"], [0, 0, 0, 2, 0, 0]),
            ("s2_int11", ["P5"], ["dS2"], [0, 0, 0, 0, 2, 0]),
            ("s2_po_comm12", ["P5", "P6"], ["cS2PO"], [0, 0, 0, 0, 3, 2]),
            ("po_eval13", ["P6"], ["k_not_j1", "k_not_s2", "poe"], [0, 0, 0, 0, 3, 3]),
            ("s1_int14", ["P1"], [], [3, 0, 0, 0, 0, 0]),
            ("j1_int15", ["P2"], ["j1"], [0, 3, 0, 0, 0, 0]),
            ("j2_int16", ["P3"], ["j2"], [0, 0, 3, 0, 0, 0]),
            ("ms_int17", ["P4"], [], [0, 0, 0, 3, 0, 0]),
            ("s2_int18", ["P5"], [], [0, 0, 0, 0, 4, 2]),
            ("s1_po_comm19", ["P1", "P6"], ["cS1PO"], [4, 0, 0, 0, 3, 4]),
            ("j1_po_comm20", ["P2", "P6"], ["cJ1PO"], [4, 4, 0, 0, 3, 5]),
        ],
        expected_verdicts_after_event=[
            ("po_eval13", False),
            ("j1_int15", False),
            ("j1_po_comm20", False),
        ],
        expected_final_verdict=False,
    ),
]


def run_scenario_with_real_poet_step_by_step(
    scenario: PoetScenario,
) -> Tuple[List[Tuple[str, bool]], bool]:
    """Run scenario using real PoET system and return step-by-step verdicts and final verdict."""
    step_verdicts = []

    # For each prefix of events, run PoET and get the verdict
    for i in range(1, len(scenario.trace) + 1):
        prefix_trace = scenario.trace[:i]
        current_event_name = prefix_trace[-1][0]

        # Create temporary files for this prefix
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pctl", delete=False
        ) as pctl_file:
            pctl_file.write(scenario.spec)
            pctl_path = pctl_file.name

        trace_data = {
            "processes": scenario.num_processes,
            "process_names": [f"P{i+1}" for i in range(scenario.num_processes)],
            "events": [list(event_data) for event_data in prefix_trace],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as trace_file:
            json.dump(trace_data, trace_file)
            trace_path = trace_file.name

        try:
            # Create config and run PoET
            config = Config(
                property_file=pctl_path,
                trace_file=trace_path,
                output_level="nothing",  # Very quiet mode for step-by-step
            )

            monitor = PoETMonitor(config)
            monitor.run()

            # Get the verdict from the state manager
            verdict_str = monitor.state_manager.get_final_verdict()
            verdict_bool = verdict_str == "TRUE"

            step_verdicts.append((current_event_name, verdict_bool))

            # Clean up temp files
            os.unlink(pctl_path)
            os.unlink(trace_path)

        except Exception as e:
            # Clean up on error
            try:
                os.unlink(pctl_path)
                os.unlink(trace_path)
            except:
                pass
            # For step-by-step, we store the error but continue
            step_verdicts.append((current_event_name, f"ERROR: {str(e)}"))

    # Final verdict is the last step verdict
    if step_verdicts and not isinstance(step_verdicts[-1][1], str):  # Not an error
        final_verdict = step_verdicts[-1][1]
    else:
        final_verdict = False  # Default to False on error

    return step_verdicts, final_verdict


def run_scenario_with_real_poet(scenario: PoetScenario) -> bool:
    """Run scenario using the real PoET system (full trace at once)."""
    # Create temporary files for the scenario
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pctl", delete=False
    ) as pctl_file:
        pctl_file.write(scenario.spec)
        pctl_path = pctl_file.name

    trace_data = {
        "processes": scenario.num_processes,
        "process_names": [f"P{i + 1}" for i in range(scenario.num_processes)],
        "events": [list(event_data) for event_data in scenario.trace],
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as trace_file:
        json.dump(trace_data, trace_file)
        trace_path = trace_file.name

    try:
        # Create config and run PoET
        config = Config(
            property_file=pctl_path,
            trace_file=trace_path,
            output_level="experiment",  # Quiet mode for tests
        )

        monitor = PoETMonitor(config)
        monitor.run()

        # Get the final verdict from the state manager
        final_verdict = monitor.state_manager.get_final_verdict()

        # Clean up temp files
        os.unlink(pctl_path)
        os.unlink(trace_path)

        return final_verdict == "TRUE"  # Convert string verdict to boolean

    except Exception as e:
        # Clean up on error
        try:
            os.unlink(pctl_path)
            os.unlink(trace_path)
        except:
            pass
        raise e


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.id for s in SCENARIOS])
def test_poet_scenario(scenario: PoetScenario):
    """Test PCTL runtime verification for given scenario using real PoET implementation."""
    print(
        f"\n--- Running Scenario with Real PoET: {scenario.id} - {scenario.description} ---"
    )
    print(f"Specification: {scenario.spec}")
    print(f"Trace: {scenario.trace}")
    print(f"Expected verdicts after events: {scenario.expected_verdicts_after_event}")
    print(f"Expected final verdict: {scenario.expected_final_verdict}")

    try:
        # Test step-by-step verdicts if expected_verdicts_after_event is provided
        if scenario.expected_verdicts_after_event:
            print("\n=== Testing Step-by-Step Verdicts ===")
            step_verdicts, final_verdict_from_steps = (
                run_scenario_with_real_poet_step_by_step(scenario)
            )

            print("Actual step verdicts:", step_verdicts)

            # Create a map for easier lookup
            expected_verdicts_map = {
                event_name: verdict
                for event_name, verdict in scenario.expected_verdicts_after_event
            }

            # Check each expected verdict
            for event_name, actual_verdict in step_verdicts:
                if event_name in expected_verdicts_map:
                    expected_verdict = expected_verdicts_map[event_name]

                    if isinstance(actual_verdict, str):  # Error case
                        print(f"  ❌ After {event_name}: ERROR - {actual_verdict}")
                        assert (
                            False
                        ), f"Error processing event {event_name}: {actual_verdict}"
                    else:
                        print(
                            f"  After {event_name}: Expected={expected_verdict}, Actual={actual_verdict}"
                        )

                        if actual_verdict != expected_verdict:
                            print(f"  ❌ MISMATCH after event {event_name}")
                            assert False, (
                                f"Scenario {scenario.id}: Verdict mismatch after event '{event_name}'. "
                                f"Expected {expected_verdict}, got {actual_verdict}"
                            )
                        else:
                            print(f"  ✅ MATCH after event {event_name}")

        # Test final verdict
        print("\n=== Testing Final Verdict ===")
        actual_final_verdict = run_scenario_with_real_poet(scenario)
        print(
            f"Final Verdict: Actual={actual_final_verdict}, Expected={scenario.expected_final_verdict}"
        )

        if actual_final_verdict != scenario.expected_final_verdict:
            print(f"❌ FINAL VERDICT MISMATCH")
            # Add debug information
            print(f"\nDEBUG INFO:")
            print(f"  Scenario ID: {scenario.id}")
            print(f"  Description: {scenario.description}")
            print(f"  PCTL Spec: {scenario.spec}")
            print(f"  Event Trace: {scenario.trace}")
            print(f"  Number of processes: {scenario.num_processes}")

            assert False, (
                f"Scenario {scenario.id}: Final verdict mismatch. "
                f"Expected {scenario.expected_final_verdict}, got {actual_final_verdict}"
            )
        else:
            print(f"✅ FINAL VERDICT MATCH")

        print(f"\n🎉 Scenario {scenario.id} PASSED!")

    except Exception as e:
        print(f"\n💥 Scenario {scenario.id} FAILED with exception: {str(e)}")
        print(f"\nDEBUG INFO:")
        print(f"  Scenario ID: {scenario.id}")
        print(f"  Description: {scenario.description}")
        print(f"  PCTL Spec: {scenario.spec}")
        print(f"  Event Trace: {scenario.trace}")
        print(f"  Number of processes: {scenario.num_processes}")
        print(
            f"  Expected verdicts after events: {scenario.expected_verdicts_after_event}"
        )
        print(f"  Expected final verdict: {scenario.expected_final_verdict}")
        raise
