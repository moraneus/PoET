"""
Usage:
  poet.py --property=<property> --trace.json.json=<trace.json.json> [--reduce] [--debug] [--visual] [--experiment]
  poet.py -p <property> -t <trace.json.json> [-r] [-d] [-v] [-e]

Options:
  -p <property>, --property=<property>  Property filename (mandatory)
  -t <trace.json.json>, --trace.json.json=<trace.json.json>           Trace filename (mandatory)
  -r, --reduce                          Enable reduce (optional)
  -d, --debug                           Enable debug mode (optional)
  -v, --visual                          Enable visual output (optional)
  -e, --experiment                      Disable all print due to experiment benchmarks
  -h, --help                            Show this help message and exit
"""
from typing import List, Dict, Tuple, Set
from docopt import docopt

from graphics.automaton import Automaton
from graphics.prints import Prints
from model.event import Event
from model.process import Process
from model.process_modes import ProcessModes
from model.state import State
from parser.ast import Formula
from parser.parser import parse

from utils.generic_utils import GenericUtils


def main(i_property: str, i_trace: str, i_reduce: bool, i_debug: bool, i_visual: bool, i_experiment: bool):

    if not i_experiment:
        Prints.banner()

    # Read property file
    raw_prop = GenericUtils.read_property(i_property)
    prop = parse(raw_prop)
    Prints.raw_property(''.join(raw_prop))
    Prints.compiled_property(prop)

    # Read trace.json.json file
    trace_data = GenericUtils.read_json(i_trace)
    trace = trace_data['events']
    num_of_processes = trace_data['processes']

    # Initialize processes structure
    processes = initialize_processes(num_of_processes)

    # Initialize first state
    formulas = Formula.collect_formulas(prop)
    states = initialize_states(num_of_processes, formulas)
    res = prop.eval(state=states[0])
    states[0].value = res

    if i_experiment:
        Prints.total_events(len(trace))

    for event_data in trace:
        event = initialize_event(event_data, num_of_processes)
        Prints.event(event)

        # Attach events to the processes they belong
        attach_event_to_process(event, processes)

        # The new state are the cuts
        new_states, closed_events = find_new_states(states, event)

        # Update closed events' mode
        for finish_event, index in filter(None, closed_events):
            finish_event.update_mode(ProcessModes.CLOSED, index)

        # Checking for states that couldn't yield another successors
        for state in states:
            if all(State.is_proc_closed(state.processes, i) for i in range(len(state.processes))):
                state.enabled = False

        # For the last states in the cut we check for internal edges
        for i, state in enumerate(new_states):
            state.edges_completion(new_states[i:], processes)

        # Evaluate new states
        evaluate(new_states, prop)

        if i_debug:
            Prints.display_states(new_states, i_title="NEW", i_debug=i_debug)

        if i_reduce:
            for i in range(len(states) - 1, -1, -1):
                if not states[i].enabled:
                    Prints.del_state(states[i], i_debug)
                    states[i] = None
                    del states[i]

        states.extend(new_states)
        if i_debug and i_visual:
            create_automaton(states)

    if not i_experiment:
        Prints.display_states(states, i_title="ALL", i_debug=i_debug)
    else:
        Prints.total_states(len(states))

    if i_visual:
        create_automaton(states)
        if i_debug:
            Automaton.make_gif('output')


def initialize_processes(i_num_of_processes: int) -> Dict[str, Process]:
    return {f"P{i + 1}": Process(f"P{i + 1}") for i in range(0, i_num_of_processes)}


def initialize_states(i_num_of_processes: int, i_formulas: List[str]):
    return [State(i_processes=[ProcessModes.IOTA] * i_num_of_processes, i_formulas=i_formulas)]


def initialize_event(i_event_data: List[str | List[str]], i_num_of_processes: int):
    event_name = i_event_data[0]
    event_processes = Process.distribute_processes(i_event_data[1], i_num_of_processes)
    propositions = i_event_data[2]
    return Event(i_name=event_name, i_processes=event_processes, i_propositions=propositions)


def attach_event_to_process(i_event: Event, i_processes: Dict[str, Process]):
    for p in i_event.processes:
        if p in i_processes:
            i_processes[p].add_event(i_event)


def find_new_states(i_states: List[State], i_event: Event) -> Tuple[List[State], Set[Tuple[Event, int]]]:
    # The new states are the cut slices
    new_states = []
    closed_events = set()
    for state in i_states:
        if state.enabled:
            new_state, closed_event = state | i_event
            if new_state is not None:
                new_states.append(new_state)
                closed_events.update(closed_event)

    return new_states, closed_event


def evaluate(i_new_states: List[State], i_prop: Formula):
    for new_state in i_new_states:
        res = i_prop.eval(state=new_state)
        new_state.value = res


def create_automaton(i_states: List[State]):
    # Preparing for automaton creation
    state_names, transitions = set(), []
    for state in i_states:
        state_names.add(state.name)
        for pred_name, (event, _) in state.successors.items():
            transitions.append((pred_name, state.name, getattr(event, 'name')))

    Automaton.create_automaton(i_states, transitions)


if __name__ == '__main__':
    arguments = docopt(__doc__)

    property_value = arguments['--property']
    trace_value = arguments['--trace.json.json']
    reduce_enabled = arguments['--reduce']
    debug_enabled = arguments['--debug']
    visual_enabled = arguments['--visual']
    experiment_mode = arguments['--experiment']

    main(property_value, trace_value, reduce_enabled, debug_enabled, visual_enabled, experiment_mode)
